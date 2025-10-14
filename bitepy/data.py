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

        year = str(date.year)
        month = f"{date.month:02d}"
        day = f"{date.day:02d}"
        folder_path = Path(marketdatapath) / year / month / day
        
        if not folder_path.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        
        parquet_files = sorted(folder_path.glob("NordPool_*.parquet"))
        
        if not parquet_files:
            raise FileNotFoundError(f"No parquet files found in folder: {folder_path}")
        
        dfs = []
        tot_rows = 0
        for file in parquet_files:
            df_temp = pd.read_parquet(file)
            tot_rows += len(df_temp)
            dfs.append(df_temp)
        
        df = pd.concat(dfs, ignore_index=True)

        df = (df
            .assign(createdTime=lambda x: pd.to_datetime(x['createdTime'], format='ISO8601'))
            .assign(expirationTime=lambda x: pd.to_datetime(x['expirationTime'], format='ISO8601'))
            .assign(deliveryStart=lambda x: pd.to_datetime(x['deliveryStart'], format='ISO8601'))
            .assign(deliveryEnd=lambda x: pd.to_datetime(x['deliveryEnd'], format='ISO8601'))
            )
        
        df = (df
            .drop_duplicates(subset=['orderId', 'originalOrderId', 'action', 'expirationTime', 'price', 'volume'])
            .loc[lambda x: x['contractName'].str.startswith('PH')]
            .assign(delivery_duration=lambda x: x['deliveryEnd'] - x['deliveryStart'])
            .loc[lambda x: x['delivery_duration'] == pd.Timedelta(hours=1)]
            .drop('delivery_duration', axis=1)
            .loc[lambda x: x['action'].isin(['UserAdded', 'UserModified', 'UserDeleted', 'SystemDeleted'])]
            )
        
        iceberg_IDs = df.loc[df['orderType'] == 'Iceberg', 'originalOrderId'].unique()
        df = df.loc[~df['originalOrderId'].isin(iceberg_IDs)]
        
        df = df.rename(columns={
            'orderId': 'order',
            'originalOrderId': 'initial',
            'deliveryStart': 'start',
            'createdTime': 'transaction',
            'expirationTime': 'validity',
            'volume': 'quantity',
            'action': 'action_original'
        })
        
        df['action'] = df['action_original'].map({
            'UserAdded': 'A',
            'UserModified': 'C',
            'UserDeleted': 'D',
            'SystemDeleted': 'D'
        })
        
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
        
        cancel_messages = df[df["action"] == "D"]
        not_added = cancel_messages[~(cancel_messages["order"].isin(df.loc[df["action"] == "A", "order"]))]
        cancel_messages = cancel_messages[~(cancel_messages["order"].isin(not_added["order"]))]
        
        indexer_messA_with_cancel = df[(df["order"].isin(cancel_messages["order"])) & (df["action"] == "A")] \
            .sort_values("transaction").groupby("order").tail(1).index
        df["df_index_copy"] = df.index
        merged = pd.merge(cancel_messages, df.loc[indexer_messA_with_cancel], on='order')
        df.loc[merged["df_index_copy"].to_numpy(), "validity"] = merged["transaction_x"].to_numpy()
        
        df = df.loc[lambda x: ~(x["action"] == "D")]
        df = df.drop(["order", "action", "action_original", "df_index_copy"], axis=1, errors='ignore')
        
        df = df[df['quantity'] > 0]
        
        df["start"] = df["start"].dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        df["transaction"] = df["transaction"].dt.strftime('%Y-%m-%dT%H:%M:%S.%f').str[:-3] + 'Z'
        df["validity"] = df["validity"].dt.strftime('%Y-%m-%dT%H:%M:%S.%f').str[:-3] + 'Z'
        
        df = df[['initial', 'side', 'start', 'transaction', 'validity', 'price', 'quantity']]

        return df

    def parse_market_data(self, start_date_str: str, end_date_str: str, marketdatapath: str, 
                     savepath: str, market_type: str, verbose: bool = True):
        """
        Parse market data between two dates and save processed zipped CSV files.

        This method sequentially loads and processes the raw market data files (zipped order book data)
        provided by EPEX. It converts the raw data into a sorted CSV file for each day in UTC time format.

        The processing constructs the file name based on the timestamp,
        reads the zipped CSV file (using a different CSV format and separator compared to 2020),
        processes the data by removing duplicates, filtering rows, renaming columns,
        and converting timestamp columns to UTC ISO 8601 format.
        Additional processing is done to handle change and cancel messages.

        Args:
            start_date_str (str): Start date string in the format "YYYY-MM-DD" (no time zone).
            end_date_str (str): End date string in the format "YYYY-MM-DD" (no time zone).
            marketdatapath (str): Path to the market data folder containing yearly/monthly subfolders with zipped files.
            savepath (str): Directory path where the parsed CSV files should be saved.
            market_type: "EPEX" or "NordPool"
            verbose (bool, optional): If True, print progress messages. Defaults to True.
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
                
                df = pd.concat([df1, df2])
                df = df.sort_values(by='transaction')
                df['transaction_date'] = pd.to_datetime(df['transaction']).dt.date
                grouped = df.groupby('transaction_date')
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