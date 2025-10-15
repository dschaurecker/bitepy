######################################################################
# Copyright (C) 2025 ETH Zurich
# BitePy: A Python Battery Intraday Trading Engine
# Bits to Energy Lab - Chair of Information Management - ETH Zurich
#
# Author: David Schaurecker
#
# Licensed under MIT License, see https://opensource.org/license/mit
######################################################################

import pandas as pd
import numpy as np
from zipfile import ZipFile
import os
from tqdm import tqdm
from pathlib import Path
from datetime import datetime

try:
    from ._bitepy import Simulation_cpp
except ImportError as e:
    raise ImportError(
        "Failed to import _bitepy module. Ensure that the C++ extension is correctly built and installed."
    ) from e


class Data:
    def __init__(self):
        """Initialize a Data instance."""
        pass

    def _load_csv(self, file_path):
        """
        Load a single zipped CSV file with specified dtypes.
        """
        df = pd.read_csv(
            file_path,
            compression="zip",
            dtype={
                "id": np.int64,
                "initial": np.int64,
                "side": "string",
                "start": "string",
                "transaction": "string",
                "validity": "string",
                "price": np.float64,
                "quantity": np.float64,
            },
        )
        df.rename(columns={"Unnamed: 0": "id"}, inplace=True)
        ids = df["id"].to_numpy(dtype=np.int64).tolist()
        initials = df["initial"].to_numpy(dtype=np.int64).tolist()
        sides = df["side"].to_numpy(dtype="str").tolist()
        starts = df["start"].to_numpy(dtype="str").tolist()
        transactions = df["transaction"].to_numpy(dtype="str").tolist()
        validities = df["validity"].to_numpy(dtype="str").tolist()
        prices = df["price"].to_numpy(dtype=np.float64).tolist()
        quantities = df["quantity"].to_numpy(dtype=np.float64).tolist()
        return ids, initials, sides, starts, transactions, validities, prices, quantities

    def _read_id_table_2020(self, timestamp, datapath):
        year = timestamp.strftime("%Y")
        month = timestamp.strftime("%m")
        datestr = "Continuous_Orders_DE_" + timestamp.strftime("%Y%m%d")
        
        # Get file name of zip-file and CSV file within the zip file
        file_list = os.listdir(f"{datapath}/{year}/{month}")
        zip_file_name = [i for i in file_list if datestr in i][0]
        csv_file_name = zip_file_name[:-4]

        # Read data from the CSV inside the zip file
        zip_file = ZipFile(f"{datapath}/{year}/{month}/" + zip_file_name)
        df = (pd.read_csv(zip_file.open(csv_file_name), sep=";", decimal=".")
              .drop_duplicates(subset=["Order ID", "Initial ID", "Action code", "Validity time", "Price", "Quantity"])
              .loc[lambda x: x["Is User Defined Block"] == 0]
              .loc[lambda x: (x["Product"] == "Intraday_Hour_Power") | (x["Product"] == "XBID_Hour_Power")]
              .loc[lambda x: (x["Action code"] == "A") | (x["Action code"] == "D") | (x["Action code"] == "C") | (x["Action code"] == "I")]
              .drop(["Delivery area", "Execution restriction", "Market area", "Parent ID", "Delivery End",
                     "Currency", "Product", "isOTC", "Is User Defined Block", "Unnamed: 20", "RevisionNo", "Entry time"],
                    axis=1)
              .rename({"Order ID": "order",
                       "Initial ID": "initial",
                       "Delivery Start": "start",
                       "Side": "side",
                       "Price": "price",
                       "Volume": "volume",
                       "Validity time": "validity",
                       "Action code": "action",
                       "Transaction Time": "transaction",
                       "Quantity": "quantity"}, axis=1)
              .assign(start=lambda x: pd.to_datetime(x.start, format="%Y-%m-%dT%H:%M:%SZ"))
              .assign(validity=lambda x: pd.to_datetime(x.validity, format="%Y-%m-%dT%H:%M:%SZ"))
              .assign(transaction=lambda x: pd.to_datetime(x.transaction, format="%Y-%m-%dT%H:%M:%S.%fZ"))
              )

        # Remove iceberg orders
        iceberg_IDs = df.loc[df["action"] == "I", "initial"].unique()
        df = df.loc[~df["initial"].isin(iceberg_IDs)]

        # Process change messages (action code 'C')
        change_messages = df[df["action"] == "C"].drop_duplicates(subset=["order"], keep="first")
        not_added = change_messages[~(change_messages["order"].isin(df.loc[df["action"] == "A", "order"]))]
        change_messages = change_messages[~(change_messages["order"].isin(not_added["order"]))]
        
        change_exists = change_messages.shape[0] > 0
        change_counter = 0
        while change_exists:
            indexer_messA_with_change = df[(df["order"].isin(change_messages["order"])) & (df["action"] == "A")] \
                .sort_values("transaction").groupby("order").tail(1).index

            df["df_index_copy"] = df.index
            merged = pd.merge(change_messages, df.loc[indexer_messA_with_change], on='order')
            df.loc[merged["df_index_copy"].to_numpy(), "validity"] = merged["transaction_x"].to_numpy()

            # Change the action code from "C" to "A" for processed messages
            df.loc[df.index.isin(change_messages.index), "action"] = "A"
            df.drop("df_index_copy", axis=1, inplace=True)

            # Redo the procedure for remaining change messages
            change_messages = df[df["action"] == "C"].drop_duplicates(subset=["order"], keep="first")
            not_added = change_messages[~(change_messages["order"].isin(df.loc[df["action"] == "A", "order"]))]
            change_messages = change_messages[~(change_messages["order"].isin(not_added["order"]))]
            change_exists = change_messages.shape[0] > 0
            change_counter += 1

        # Process cancel messages (action code 'D')
        cancel_messages = df[df["action"] == "D"]
        not_added = cancel_messages[~(cancel_messages["order"].isin(df.loc[df["action"] == "A", "order"]))]
        cancel_messages = cancel_messages[~(cancel_messages["order"].isin(not_added["order"]))]
        
        indexer_messA_with_cancel = df[(df["order"].isin(cancel_messages["order"])) & (df["action"] == "A")] \
            .sort_values("transaction").groupby("order").tail(1).index
        df["df_index_copy"] = df.index
        merged = pd.merge(cancel_messages, df.loc[indexer_messA_with_cancel], on='order')
        df.loc[merged["df_index_copy"].to_numpy(), "validity"] = merged["transaction_x"].to_numpy()

        df = df.loc[lambda x: ~(x["action"] == "D")]
        df = df.drop(["order", "action", "df_index_copy"], axis=1)

        # Reorder and format columns
        newOrder = ["initial", "side", "start", "transaction", "validity", "price", "quantity"]
        df = df[newOrder]
        df['side'] = df['side'].str.upper()

        df["start"] = df["start"].dt.tz_localize('UTC').dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        df["transaction"] = df["transaction"].dt.tz_localize('UTC').dt.strftime('%Y-%m-%dT%H:%M:%S.%f').str[:-3] + 'Z'
        df["validity"] = df["validity"].dt.tz_localize('UTC').dt.strftime('%Y-%m-%dT%H:%M:%S.%f').str[:-3] + 'Z'
        
        return df

    def _read_id_table_2021(self, timestamp, datapath):
        year = timestamp.strftime("%Y")
        month = timestamp.strftime("%m")
        datestr = "Continuous_Orders-DE-" + timestamp.strftime("%Y%m%d")
        
        # Get file name of zip-file and CSV file within the zip file
        file_list = os.listdir(f"{datapath}/{year}/{month}")
        zip_file_name = [i for i in file_list if datestr in i][0]
        csv_file_name = zip_file_name[:-4]

        # Read data from the CSV inside the zip file
        zip_file = ZipFile(f"{datapath}/{year}/{month}/" + zip_file_name)
        df = (pd.read_csv(zip_file.open(csv_file_name), sep=",", decimal=".", skiprows=1)
              .drop_duplicates(subset=["OrderId", "InitialId", "ActionCode", "ValidityTime", "Price", "Quantity"])
              .loc[lambda x: x["UserDefinedBlock"] == "N"]
              .loc[lambda x: (x["Product"] == "Intraday_Hour_Power") | (x["Product"] == "XBID_Hour_Power")]
              .loc[lambda x: (x["ActionCode"] == "A") | (x["ActionCode"] == "D") | (x["ActionCode"] == "C") | (x["ActionCode"] == "I")]
              .drop(["LinkedBasketId", "DeliveryArea", "ParentId", "DeliveryEnd", "Currency", "Product",
                     "UserDefinedBlock", "RevisionNo", "ExecutionRestriction", "CreationTime", "QuantityUnit",
                     "Volume", "VolumeUnit"], axis=1)
              .rename({"OrderId": "order",
                       "InitialId": "initial",
                       "DeliveryStart": "start",
                       "Side": "side",
                       "Price": "price",
                       "Volume": "volume",
                       "ValidityTime": "validity",
                       "ActionCode": "action",
                       "TransactionTime": "transaction",
                       "Quantity": "quantity"}, axis=1)
              .assign(start=lambda x: pd.to_datetime(x.start, format="%Y-%m-%dT%H:%M:%SZ"))
              .assign(validity=lambda x: pd.to_datetime(x.validity, format="%Y-%m-%dT%H:%M:%SZ"))
              .assign(transaction=lambda x: pd.to_datetime(x.transaction, format="%Y-%m-%dT%H:%M:%S.%fZ"))
              )
        # Remove iceberg orders
        iceberg_IDs = df.loc[df["action"] == "I", "initial"].unique()
        df = df.loc[~df["initial"].isin(iceberg_IDs)]

        # Process change messages (action code 'C')
        change_messages = df[df["action"] == "C"].drop_duplicates(subset=["order"], keep="first")
        not_added = change_messages[~(change_messages["order"].isin(df.loc[df["action"] == "A", "order"]))]
        change_messages = change_messages[~(change_messages["order"].isin(not_added["order"]))]
        
        change_exists = change_messages.shape[0] > 0
        change_counter = 0
        while change_exists:
            indexer_messA_with_change = df[(df["order"].isin(change_messages["order"])) & (df["action"] == "A")] \
                .sort_values("transaction").groupby("order").tail(1).index

            df["df_index_copy"] = df.index
            merged = pd.merge(change_messages, df.loc[indexer_messA_with_change], on='order')
            df.loc[merged["df_index_copy"].to_numpy(), "validity"] = merged["transaction_x"].to_numpy()

            # Change the action code from "C" to "A" so it can be processed in the next iteration
            df.loc[df.index.isin(change_messages.index), "action"] = "A"
            df.drop("df_index_copy", axis=1, inplace=True)

            # Redo procedure for remaining change messages
            change_messages = df[df["action"] == "C"].drop_duplicates(subset=["order"], keep="first")
            not_added = change_messages[~(change_messages["order"].isin(df.loc[df["action"] == "A", "order"]))]
            change_messages = change_messages[~(change_messages["order"].isin(not_added["order"]))]
            change_exists = change_messages.shape[0] > 0
            change_counter += 1

        # Process cancel messages (action code 'D')
        cancel_messages = df[df["action"] == "D"]
        not_added = cancel_messages[~(cancel_messages["order"].isin(df.loc[df["action"] == "A", "order"]))]
        cancel_messages = cancel_messages[~(cancel_messages["order"].isin(not_added["order"]))]
        
        indexer_messA_with_cancel = df[(df["order"].isin(cancel_messages["order"])) & (df["action"] == "A")] \
            .sort_values("transaction").groupby("order").tail(1).index
        df["df_index_copy"] = df.index
        merged = pd.merge(cancel_messages, df.loc[indexer_messA_with_cancel], on='order')
        df.loc[merged["df_index_copy"].to_numpy(), "validity"] = merged["transaction_x"].to_numpy()

        df = df.loc[lambda x: ~(x["action"] == "D")]
        df = df.drop(["order", "action", "df_index_copy"], axis=1)

        df["start"] = df["start"].dt.tz_localize('UTC').dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        df["transaction"] = df["transaction"].dt.tz_localize('UTC').dt.strftime('%Y-%m-%dT%H:%M:%S.%f').str[:-3] + 'Z'
        df["validity"] = df["validity"].dt.tz_localize('UTC').dt.strftime('%Y-%m-%dT%H:%M:%S.%f').str[:-3] + 'Z'
        
        return df
    
    
    def _read_nordpool_table(self, date, marketdatapath):
        """Read and process NordPool parquet files for a specific date.
           Nordpool contains flags for full and partial execution of orders. We disregard this, as it will become apparent in our backtesting LOB traversal. After partial execution, orders are sometimes modified, deleted etc., this all stays relevant and is handled.
           We also currently still disregard FoK and IoC orders (treat them as 0 validity duration). They have all the same updateTime in their message-chain.
        """
        date_folder = date.strftime("%Y%m%d")
        folder_path = Path(marketdatapath) / date_folder
        
        if not folder_path.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        
        parquet_files = sorted(folder_path.glob("NordPool_*.parquet"))
        
        if not parquet_files:
            raise FileNotFoundError(f"No parquet files found in folder: {folder_path}")
        
        # Read and concatenate all hourly parquet files
        dfs = []
        for file in parquet_files:
            df_temp = pd.read_parquet(file)
            dfs.append(df_temp)
        
        df = pd.concat(dfs, ignore_index=True)
        
        # Convert timestamps (needed for subsequent filtering and processing)
        df = (df
            .assign(createdTime=lambda x: pd.to_datetime(x['createdTime'], format='ISO8601'))
            .assign(updatedTime=lambda x: pd.to_datetime(x['updatedTime'], format='ISO8601'))
            .assign(expirationTime=lambda x: pd.to_datetime(x['expirationTime'], format='ISO8601'))
            .assign(deliveryStart=lambda x: pd.to_datetime(x['deliveryStart'], format='ISO8601'))
            .assign(deliveryEnd=lambda x: pd.to_datetime(x['deliveryEnd'], format='ISO8601'))
            )
        
        # Filter and prepare data
        df = (df
            .drop_duplicates(subset=['orderId', 'originalOrderId', 'action', 'expirationTime', 'price', 'volume'])
            .loc[lambda x: x['contractName'].str.startswith('PH')]
            .loc[lambda x: x['action'].isin(['UserAdded', 'UserModified', 'UserDeleted', 'SystemDeleted', 'UserHibernated'])]
            )
        
        # Remove iceberg orders
        iceberg_IDs = df.loc[df['orderType'] == 'Iceberg', 'originalOrderId'].unique()
        df = df.loc[~df['originalOrderId'].isin(iceberg_IDs)]

        # Replace letters with numbers in originalOrderId and orderId
        unique_letters = sorted(df['originalOrderId'].astype(str).str.findall(r'[A-Za-z]').str.join('').unique())
        # Create mapping of unique letters to numbers starting from 11
        letter_to_num = {letter: str(i+11) for i, letter in enumerate(unique_letters)}
        # Function to replace letters with numbers
        def replace_letters(order_id):
            order_id = str(order_id)
            for letter, num in letter_to_num.items():
                order_id = order_id.replace(letter, num)
            return order_id

        # Apply replacement to originalOrderId column
        df['originalOrderId'] = df['originalOrderId'].apply(replace_letters)
        df['orderId'] = df['orderId'].apply(replace_letters)
        
        # Rename columns to standardized format
        df = df.rename(columns={
            'orderId': 'order',
            'originalOrderId': 'initial',
            'deliveryStart': 'start',
            'updatedTime': 'transaction',
            'expirationTime': 'validity',
            'volume': 'quantity',
            'action': 'action_original'
        })
        
        # Map NordPool actions to standardized codes
        df['action'] = df['action_original'].map({
            'UserAdded': 'A',
            'UserModified': 'C',
            'UserDeleted': 'D',
            'SystemDeleted': 'D',
            'UserHibernated': 'H'
        })
        
        # Process change messages (modifications)
        change_messages = df[df["action"] == "C"].drop_duplicates(subset=["order"], keep="first")
        not_added = change_messages[~(change_messages["order"].isin(df.loc[df["action"] == "A", "order"]))]
        change_messages = change_messages[~(change_messages["order"].isin(not_added["order"]))]
        
        change_exists = change_messages.shape[0] > 0
        while change_exists:
            indexer_messA_with_change = df[(df["order"].isin(change_messages["order"])) & (df["action"] == "A")] \
                .sort_values("transaction").groupby("order").tail(1).index
            df["df_index_copy"] = df.index
            merged = pd.merge(change_messages, df.loc[indexer_messA_with_change], on='order')
            df.loc[merged["df_index_copy"].to_numpy(), "validity"] = merged["transaction_x"].to_numpy()
            df.loc[df.index.isin(change_messages.index), "action"] = "A"
            df.drop("df_index_copy", axis=1, inplace=True)
            
            change_messages = df[df["action"] == "C"].drop_duplicates(subset=["order"], keep="first")
            not_added = change_messages[~(change_messages["order"].isin(df.loc[df["action"] == "A", "order"]))]
            change_messages = change_messages[~(change_messages["order"].isin(not_added["order"]))]
            change_exists = change_messages.shape[0] > 0
        
        # Process cancel messages (deletions)
        cancel_messages = df[df["action"] == "D"]
        not_added = cancel_messages[~(cancel_messages["order"].isin(df.loc[df["action"] == "A", "order"]))]
        cancel_messages = cancel_messages[~(cancel_messages["order"].isin(not_added["order"]))]
        
        indexer_messA_with_cancel = df[(df["order"].isin(cancel_messages["order"])) & (df["action"] == "A")] \
            .sort_values("transaction").groupby("order").tail(1).index
        df["df_index_copy"] = df.index
        merged = pd.merge(cancel_messages, df.loc[indexer_messA_with_cancel], on='order')
        df.loc[merged["df_index_copy"].to_numpy(), "validity"] = merged["transaction_x"].to_numpy()
        df.drop("df_index_copy", axis=1, inplace=True)
        
        df = df.loc[lambda x: ~(x["action"] == "D")]
        
        # Process hibernation messages
        hibernated_messages = df[df["action"] == "H"]
        not_added = hibernated_messages[~(hibernated_messages["order"].isin(df.loc[df["action"] == "A", "order"]))]
        hibernated_messages = hibernated_messages[~(hibernated_messages["order"].isin(not_added["order"]))]
        
        if not hibernated_messages.empty:
            indexer_messA_with_hibernated = df[(df["order"].isin(hibernated_messages["order"])) & (df["action"] == "A")] \
                .sort_values("transaction").groupby("order").tail(1).index
            df["df_index_copy"] = df.index
            merged = pd.merge(hibernated_messages, df.loc[indexer_messA_with_hibernated], on='order')
            df.loc[merged["df_index_copy"].to_numpy(), "validity"] = merged["transaction_x"].to_numpy()
            df.drop("df_index_copy", axis=1, inplace=True)
        
        df = df.loc[lambda x: ~(x["action"] == "H")]
        df = df.drop(["order", "action", "action_original"], axis=1, errors='ignore')

        # Filter out orders where validity time is not after transaction time; Sometimes orders are added and deleted at the same time.
        df = df[df['validity'] > df['transaction']]
        
        # Convert timestamps to string format
        df["start"] = df["start"].dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        df["transaction"] = df["transaction"].dt.strftime('%Y-%m-%dT%H:%M:%S.%f').str[:-3] + 'Z'
        df["validity"] = df["validity"].dt.strftime('%Y-%m-%dT%H:%M:%S.%f').str[:-3] + 'Z'

        # rename side to all uppercase
        df['side'] = df['side'].str.upper()
        
        # Select and order final columns
        df = df[['initial', 'side', 'start', 'transaction', 'validity', 'price', 'quantity']]
        
        return df


    def parse_market_data(self, start_date_str: str, end_date_str: str, marketdatapath: str, 
                        savepath: str, market_type: str, verbose: bool = True):
        """
        Parse market data between two dates and save processed zipped CSV files.
        
        Processes raw order book data from EPEX or NordPool markets and converts them into 
        standardized sorted CSV files for each day in UTC time format. Handles order lifecycle 
        events (additions, modifications, cancellations) and reconstructs order validity periods.
        
        Args:
            start_date_str (str): Start date in format "YYYY-MM-DD"
            end_date_str (str): End date in format "YYYY-MM-DD"
            marketdatapath (str): Path to market data folder with yearly/monthly subfolders
            savepath (str): Directory where processed CSV files will be saved
            market_type (str): "EPEX" or "NordPool"
            verbose (bool, optional): Print progress messages. Defaults to True.
        """
        
        if not os.path.exists(savepath):
            os.makedirs(savepath)
        
        start_date = pd.Timestamp(start_date_str)
        end_date = pd.Timestamp(end_date_str)
        
        if start_date > end_date:
            raise ValueError("Error: Start date is after end date.")
        if market_type == "EPEX" and start_date.year < 2020:
            raise ValueError("Error: Years before 2020 are not supported.")
        
        dates = pd.date_range(start_date, end_date, freq="D")
        df1 = pd.DataFrame()
        df2 = pd.DataFrame()
        
        with tqdm(total=len(dates), desc="Loading and saving CSV data", ncols=100, disable=not verbose) as pbar:
            for dt1 in dates:
                pbar.set_description(f"Currently loading and saving date {str(dt1.date())} ... ")
                df1 = df2
                df2 = pd.DataFrame()
                dt2 = dt1 + pd.Timedelta(days=1)
                
                # Read current day data
                if df1.empty:
                    if market_type == "EPEX":
                        if dt1.year == 2020:
                            df1 = self._read_id_table_2020(dt1, marketdatapath)
                        elif dt1.year >= 2021:
                            df1 = self._read_id_table_2021(dt1, marketdatapath)
                        else:
                            raise ValueError("Error: Year not >= 2020")
                    elif market_type == "NordPool":
                        df1 = self._read_nordpool_table(dt1, marketdatapath)
                    else:
                        raise ValueError(f"Unknown market_type: {market_type}")
                
                # Read next day data (captures orders with transaction today, delivery tomorrow)
                if dt2 <= end_date:
                    if market_type == "EPEX":
                        if dt2.year == 2020:
                            df2 = self._read_id_table_2020(dt2, marketdatapath)
                        elif dt2.year >= 2021:
                            df2 = self._read_id_table_2021(dt2, marketdatapath)
                        else:
                            raise ValueError("Error: Year not >= 2020")
                    elif market_type == "NordPool":
                        df2 = self._read_nordpool_table(dt2, marketdatapath)
                    else:
                        raise ValueError(f"Unknown market_type: {market_type}")
                
                # Combine and filter by transaction date
                df = pd.concat([df1, df2])
                df = df.sort_values(by='transaction')
                df['transaction_date'] = pd.to_datetime(df['transaction']).dt.date
                grouped = df.groupby('transaction_date')

                # round price to 2 decimals and quantity to 1 decimal
                df['price'] = df['price'].round(2)
                df['quantity'] = df['quantity'].round(1)
                
                save_date = dt1.date()
                group = grouped.get_group(save_date)
                daily_filename = f"{savepath}orderbook_{save_date}.csv"
                compression_options = dict(method='zip', archive_name=Path(daily_filename).name)
                group.drop(columns='transaction_date').sort_values(by='transaction').fillna("").to_csv(
                    f'{daily_filename}.zip', compression=compression_options)
                pbar.update(1)
        
        print("\nWriting CSV data completed.")

    def create_bins_from_csv(self, csv_list: list, save_path: str, verbose: bool = True):
        """
        Convert zipped CSV files of pre-processed order book data into binary files.

        This method sequentially loads each previously generated zipped CSV file, converts it to a binary format using the C++ simulation
        extension, and saves the binary file in the specified directory. Binary files allow for much (10x) quicker loading
        of the data at runtime.

        Args:
            csv_list (list): List of file paths to the zipped CSV files containing pre-processed order book data.
            save_path (str): Directory path where the binary files should be saved. The binary files will use the same base name as the CSV files.
            verbose (bool, optional): If True, print progress messages. Defaults to True.
        """
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        _sim = Simulation_cpp()
        with tqdm(total=len(csv_list), desc="Writing Binaries", ncols=100, disable=not verbose) as pbar:
            for csv_file_path in csv_list:
                filename = os.path.basename(csv_file_path)
                bin_file_path = os.path.join(save_path, filename.replace(".csv.zip", ".bin"))
                pbar.set_description(f"Currently saving binary {bin_file_path.split('/')[-1]} ... ")
                ids, initials, sides, starts, transactions, validities, prices, quantities = self._load_csv(csv_file_path)
                _sim.writeOrderBinFromPandas(
                    bin_file_path,
                    ids,
                    initials,
                    sides,
                    starts,
                    transactions,
                    validities,
                    prices,
                    quantities,
                )
                pbar.update(1)

        print("\nWriting Binaries completed.")