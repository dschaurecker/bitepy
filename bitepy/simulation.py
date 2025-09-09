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
import pytz
from datetime import timedelta
from tqdm import tqdm

try:
    from ._bitepy import Simulation_cpp
except ImportError as e:
    raise ImportError(
        "Failed to import _bitepy module. Ensure that the C++ extension is correctly built and installed."
    ) from e

class Simulation:
    def __init__(self, start_date: pd.Timestamp, end_date: pd.Timestamp,
                 trading_start_date: pd.Timestamp=None,
                 storage_max=10.,
                 lin_deg_cost=4.,
                 loss_in=0.95,
                 loss_out=0.95,
                 trading_fee=0.09,
                 num_stor_states=11,
                 trading_delay=0,
                 tec_delay=0,
                 fixed_solve_time=0,
                 solve_frequency=0.,
                 withdraw_max=5.,
                 inject_max=5.,
                 log_transactions=False,):
                #  forecast_horizon_start=10*60,
                #  forecast_horizon_end=75):
        """
        Initialize a Simulation instance.

        Args:
            start_date (pd.Timestamp): The start datetime of the simulation, i.e. which products are loaded into the simulation. Must be timezone aware.
            end_date (pd.Timestamp): The end datetime of the simulation, i.e. which products are loaded into the simulation. Must be timezone aware.
            trading_start_date (pd.Timestamp, optional): The start datetime of the trading, i.e. when the trading starts. Must be timezone aware. If None, the trading starts at the same time as the start_date.
            storage_max (float, optional): The maximum storage capacity of the storage unit (MWh). Default is 10.0.
            lin_deg_cost (float, optional): The linear degradation cost of the storage unit (€/MWh). Default is 4.0.
            loss_in (float, optional): The injection efficiency of the storage unit (0-1]. Default is 0.95.
            loss_out (float, optional): The withdrawal efficiency of the storage unit (0-1]. Default is 0.95.
            trading_fee (float, optional): The trading fee for the exchange (€/MWh). Default is 0.09.
            num_stor_states (int, optional): The number of storage states for dynamic programming. Default is 11.
            trading_delay (int, optional): The trading delay of the storage unit, i.e., when to start trading all new products after gate opening. (min, >= 0 and < 480 mins (8 hours)). Default is 0.
            tec_delay (int, optional): The technical delay of the storage unit (ms, >= 0). Default is 0.
            fixed_solve_time (int, optional): The fixed solve time for dynamic programming (ms, >= 0 or -1 for realistic solve times). Default is 0.
            solve_frequency (float, optional): The frequency at which the dynamic programming solver is run (min). Default is 0.0.
            withdraw_max (float, optional): The maximum withdrawal power of the storage unit (MW). Default is 5.0.
            inject_max (float, optional): The maximum injection power of the storage unit (MW). Default is 5.0.
            log_transactions (bool, optional): If True, we run the simulation only to log transactions data of the market, no optimization is performed. Default is False.
        """
        # forecast_horizon_start (int, optional): The start of the forecast horizon (min). Default is 600.
        # forecast_horizon_end (int, optional): The end of the forecast horizon (min). Default is 75.

        # write all the assertions
        if start_date >= end_date:
            raise ValueError("start_date must be before end_date")
        if trading_start_date is None:
            trading_start_date = start_date
        if trading_start_date >= end_date:
            raise ValueError("trading_start_date must be before end_date")
        if storage_max < 0:
            raise ValueError("storage_max must be >= 0")
        if lin_deg_cost < 0:
            raise ValueError("lin_deg_cost must be >= 0")
        if loss_in < 0 or loss_in > 1:
            raise ValueError("loss_in must be in [0, 1]")
        if loss_out < 0 or loss_out > 1:
            raise ValueError("loss_out must be in [0,1]")
        if trading_fee < 0:
            raise ValueError("trading_fee must be >= 0")
        if num_stor_states <= 0:
            raise ValueError("num_stor_states must be > 0")
        if tec_delay < 0:
            raise ValueError("tec_delay must be >= 0")
        if fixed_solve_time < 0:
            if fixed_solve_time != -1:
                raise ValueError("fixed_solve_time must be >= 0 (or -1 for realistic solve times)")
        if solve_frequency < 0:
            raise ValueError("solve_frequency must be >= 0")
        if withdraw_max <= 0:
            raise ValueError("withdraw_max must be > 0")
        if inject_max <= 0:
            raise ValueError("inject_max must be > 0")
        if trading_delay < 0 or trading_delay >= 8*60:
            raise ValueError("trading_delay must be >= 0 and < 480 mins (8 hours)")
        # if forecast_horizon_start < 0:
        #     raise ValueError("forecast_horizon_start must be >= 0")
        # if forecast_horizon_end < 0:
        #     raise ValueError("forecast_horizon_end must be >= 0")
        # if forecast_horizon_start <= forecast_horizon_end:
        #     raise ValueError("forecast_horizon_start must larger than forecast_horizon_end")
        
        self._sim_cpp = Simulation_cpp()

        self._sim_cpp.params.storageMax = storage_max
        self._sim_cpp.params.linDegCost = lin_deg_cost
        self._sim_cpp.params.lossIn = loss_in
        self._sim_cpp.params.lossOut = loss_out
        self._sim_cpp.params.tradingFee = trading_fee
        self._sim_cpp.params.numStorStates = num_stor_states
        self._sim_cpp.params.pingDelay = tec_delay
        self._sim_cpp.params.fixedSolveTime = fixed_solve_time
        self._sim_cpp.params.dpFreq = solve_frequency
        self._sim_cpp.params.withdrawMax = withdraw_max
        self._sim_cpp.params.injectMax = inject_max
        self._sim_cpp.params.minuteDelay = trading_delay
        self._sim_cpp.params.logTransactions = log_transactions
        # self._sim_cpp.params.foreHorizonStart = forecast_horizon_start
        # self._sim_cpp.params.foreHorizonEnd = forecast_horizon_end

        # Set start and end date
        if start_date >= end_date:
            raise ValueError("start_date must be before end_date")
        if start_date.tzinfo is None:
            raise ValueError("start_date must be timezone aware")
        start_date = start_date.astimezone(pytz.utc)
        self._sim_cpp.params.startMonth = start_date.month
        self._sim_cpp.params.startDay = start_date.day
        self._sim_cpp.params.startYear = start_date.year
        self._sim_cpp.params.startHour = start_date.hour
        self._sim_cpp.params.startMinute = start_date.minute
        if end_date.tzinfo is None:
            raise ValueError("end_date must be timezone aware")
        end_date = end_date.astimezone(pytz.utc)
        self._sim_cpp.params.endMonth = end_date.month
        self._sim_cpp.params.endDay = end_date.day
        self._sim_cpp.params.endYear = end_date.year
        self._sim_cpp.params.endHour = end_date.hour
        self._sim_cpp.params.endMinute = end_date.minute

        # Set trading start date
        if trading_start_date.tzinfo is None:
            raise ValueError("trading_start_date must be timezone aware")
        trading_start_date = trading_start_date.astimezone(pytz.utc)
        self._sim_cpp.params.tradingStartMonth = trading_start_date.month
        self._sim_cpp.params.tradingStartDay = trading_start_date.day
        self._sim_cpp.params.tradingStartYear = trading_start_date.year
        self._sim_cpp.params.tradingStartHour = trading_start_date.hour
        self._sim_cpp.params.tradingStartMinute = trading_start_date.minute

    def add_bin_to_orderqueue(self, bin_data: str):
        """
        Add an order binary file to the simulation's order queue.

        Args:
            bin_data (str): The path to the order binary file.
        """
        self._sim_cpp.addOrderQueueFromBin(bin_data)
    
    def add_df_to_orderqueue(self, df: pd.DataFrame):
        """
        Add a DataFrame of orders to the simulation's order queue.

        The DataFrame must have the same columns as the saved CSV files, with timestamps in UTC
        (seconds and milliseconds).

        Args:
            df (pd.DataFrame): A DataFrame containing the orders to be added.

        Processing Steps:
            - Validate that the timestamp columns ('start', 'transaction', 'validity') are timezone aware.
            - Ensure that all timestamps are in the same timezone.
            - Convert all timestamps to UTC and format them in ISO 8601.
        """
        if (df["start"].dt.tz is None and df["transaction"].dt.tz is None and df["validity"].dt.tz is None):
            raise ValueError("All timestamps of input df must be timezone aware")
        if not (df["start"].dt.tz == df["transaction"].dt.tz and df["start"].dt.tz == df["validity"].dt.tz):
            raise ValueError("All timestamps of input df must be in the same timezone")
        
        df["start"] = df["start"].dt.tz_convert("UTC")
        df["transaction"] = df["transaction"].dt.tz_convert("UTC")
        df["validity"] = df["validity"].dt.tz_convert("UTC")
        df["start"] = df["start"].dt.tz_localize(None).dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        df["transaction"] = df["transaction"].dt.tz_localize(None).dt.strftime('%Y-%m-%dT%H:%M:%S.%f').str[:-3] + 'Z'
        df["validity"] = df["validity"].dt.tz_localize(None).dt.strftime('%Y-%m-%dT%H:%M:%S.%f').str[:-3] + 'Z'

        ids = df['id'].to_numpy(dtype=np.int64).tolist()
        initials = df['initial'].to_numpy(dtype=np.int64).tolist()
        sides = df['side'].to_numpy(dtype='str').tolist()
        starts = df['start'].to_numpy(dtype='str').tolist()
        transactions = df['transaction'].to_numpy(dtype='str').tolist()
        validities = df['validity'].to_numpy(dtype='str').tolist()
        prices = df['price'].to_numpy(dtype=np.float64).tolist()
        quantities = df['quantity'].to_numpy(dtype=np.float64).tolist()

        self._sim_cpp.addOrderQueueFromPandas(ids, initials, sides, starts, transactions, validities, prices, quantities)

    # def add_forecast_from_df(self, df: pd.DataFrame):
    #     """
    #     Add forecast data from a DataFrame to the simulation.

    #     The DataFrame must contain the following columns:
    #         - creation_time: The time when the forecast was created (timezone aware, up to millisecond precision).
    #         - delivery_start: The start time of the delivery period (timezone aware).
    #         - sell_price: The price at which the optimization will try to sell (€/MWh).
    #         - buy_price: The price at which the optimization will try to buy (€/MWh).

    #     Args:
    #         df (pd.DataFrame): A DataFrame containing the forecast data.

    #     Processing Steps:
    #         - Validate that the 'creation_time' and 'delivery_start' columns are timezone aware and identical.
    #         - Convert the timestamps to UTC and format them in ISO 8601.
    #         - Pass the data to the simulation.
    #     """
    #     if (df["creation_time"].dt.tz is None and df["delivery_start"].dt.tz is None):
    #         raise ValueError("All timestamps of input df must be timezone aware")
    #     if not (df["creation_time"].dt.tz == df["delivery_start"].dt.tz):
    #         raise ValueError("All timestamps of input df must be in the same timezone")
        
    #     df["creation_time"] = df["creation_time"].dt.tz_convert("UTC")
    #     df["delivery_start"] = df["delivery_start"].dt.tz_convert("UTC")

    #     df["creation_time"] = df["creation_time"].dt.tz_localize(None).dt.strftime('%Y-%m-%dT%H:%M:%S.%f').str[:-3] + 'Z'
    #     df["delivery_start"] = df["delivery_start"].dt.tz_localize(None).dt.strftime('%Y-%m-%dT%H:%M:%SZ')

    #     creation_time = df["creation_time"].to_numpy(dtype='str').tolist()
    #     delivery_start = df["delivery_start"].to_numpy(dtype='str').tolist()
    #     buy_price = df["buy_price"].to_numpy(dtype=np.float64).tolist()
    #     sell_price = df["sell_price"].to_numpy(dtype=np.float64).tolist()

    #     self._sim_cpp.loadForecastMapFromPandas(creation_time, delivery_start, buy_price, sell_price)

    def get_data_bins_for_each_day(self, base_path: str, start_date: pd.Timestamp, end_date: pd.Timestamp):
        """
        Generate a list of file paths for binary order book data for each day within a date range.

        Args:
            base_path (str): The base directory path where the binary files are stored.
            start_date (pd.Timestamp): The start date of the range.
            end_date (pd.Timestamp): The end date of the range.

        Returns:
            list: A list of file paths for each day's binary order book file.
        """
        # convert dates to utc time
        start_date_berlin = start_date.tz_convert('Europe/Berlin') # convert to tz in which the lob files are segemented
        end_date_berlin = end_date.tz_convert('Europe/Berlin') # convert to tz in which the lob files are segemented

        # round up to midnight
        end_date_berlin_round_up = end_date_berlin.replace(hour=23, minute=59, second=59)
        
        if base_path[-1] != '/':
            base_path += '/'
        base_path += "orderbook_"

        # Generate paths for each day within the date range
        paths = []
        
        current_date = start_date_berlin - timedelta(days=1) # include the day before the start date to ensure that all orders submitted with delivery on first day are included
        while current_date < end_date_berlin_round_up:
            path = f"{base_path}{current_date.strftime('%Y-%m-%d')}.bin"
            paths.append(path)
            current_date += timedelta(days=1)
        
        return paths
    
    def run(self, data_path: str, verbose: bool = True):
        """
        Execute the simulation using binary data files.

        The files must be named as: orderbook_YYYY-MM-DD.bin.

        Args:
            data_path (str): The directory containing the binary data files.
            verbose (bool, optional): If True, display progress logs. Default is True.

        Processing Steps:
            - Retrieve the list of binary file paths for the simulation period.
            - Iterate through each day's data, add the file to the order queue, and run the simulation for that day.

        Returns:
            pd.DataFrame: A DataFrame containing the transactions if log_transactions is True, otherwise None.

        """
        start_date = pd.Timestamp(year=self._sim_cpp.params.startYear,
                                  month=self._sim_cpp.params.startMonth,
                                  day=self._sim_cpp.params.startDay,
                                  hour=self._sim_cpp.params.startHour,
                                  minute=self._sim_cpp.params.startMinute,
                                  tz="UTC")
        end_date = pd.Timestamp(year=self._sim_cpp.params.endYear,
                                month=self._sim_cpp.params.endMonth,
                                day=self._sim_cpp.params.endDay,
                                hour=self._sim_cpp.params.endHour,
                                minute=self._sim_cpp.params.endMinute,
                                tz="UTC")
        lob_paths = self.get_data_bins_for_each_day(data_path, start_date, end_date)

        transactions = pd.DataFrame()

        num_days = len(lob_paths)
        if verbose: print("The simulation will iterate over", num_days, "files.")

        with tqdm(total=num_days, desc="Simulated Days", unit="%", ncols=120, disable=not verbose) as pbar:
            for i, path in enumerate(lob_paths):
                pbar.set_description(f"Currently simulating {path.split('/')[-1]} ... ")
                self.add_bin_to_orderqueue(path)
                self.run_one_day(i == len(lob_paths) - 1)
                if self._sim_cpp.params.logTransactions:
                    transactions = pd.concat([transactions, self.group_transactions(self.get_transactions())])
                pbar.update(1)

        if verbose: print("Simulation finished.")

        if self._sim_cpp.params.logTransactions and not transactions.empty:
            return transactions

    def group_transactions(self, transactions: pd.DataFrame):
        """
        Group transactions by timestamp and delivery hour, calculating volume-weighted average prices.

        Args:
            transactions (pd.DataFrame): A DataFrame containing the transactions to be grouped.

        Processing Steps:
            - Group the transactions by timestamp and delivery_hour.
            - Calculate the volume weighted average price for each group.
            - Return a DataFrame with aggregated transaction data.

        Returns:
            pd.DataFrame: A DataFrame with the following columns:
                - timestamp: The UTC timestamp when the transaction occurred.
                - delivery_hour: The UTC timestamp of the delivery hour for the traded product.
                - vwap: The volume weighted average price of the transaction.
                - total_volume: The total volume of the transaction.
                - num_transactions: The number of transactions in the group.
        """

        vwap_results = []

        # Group by timestamp and delivery_hour
        grouped = transactions.groupby(['timestamp', 'delivery_hour'])

        for (timestamp, delivery_hour), group in grouped:
            if len(group) == 1:
                # Single transaction - use price and volume directly
                row = group.iloc[0]
                vwap = row['price']
                total_volume = row['volume']
            else:
                # Multiple transactions - calculate volume weighted average price
                total_volume = group['volume'].sum()
                weighted_price_sum = (group['price'] * group['volume']).sum()
                vwap = weighted_price_sum / total_volume if total_volume > 0 else 0
            
            vwap_results.append({
                'timestamp': timestamp,
                'delivery_hour': delivery_hour,
                'vwap': vwap,
                'total_volume': total_volume,
                'num_transactions': len(group)
            })

        if vwap_results:
            vwap_df = pd.DataFrame(vwap_results)
        else:
            vwap_df = pd.DataFrame()
        
        return vwap_df
        
    def run_one_day(self, is_last: bool):
        """
        Run the simulation for a single day.

        Args:
            is_last (bool): If True, indicates that this is the last iteration of data.

        Processing Steps:
            - Execute the simulation for the provided day's data.
        """
        self._sim_cpp.run(is_last)

    def get_logs(self):
        """
        Retrieve the logs generated by the simulation.

        Returns:
            dict: A dictionary containing simulation logs with the following keys:
                - decision_record: Final simulation schedule.
                - price_record: CID price data over the simulation duration.
                - accepted_orders: Limit orders accepted by the RI.
                - executed_orders: Orders sent to the exchange by the RI.
                - killed_orders: Orders that were missed at the exchange.
        """
        # - forecast_orders: Orders virtually traded against the forecast.
        # - balancing_orders: Orders that would have incurred payments to the TSO.
        decision_record, price_record, accepted_orders, executed_orders, forecast_orders, killed_orders, balancing_orders = self._sim_cpp.getLogs()
        decision_record = pd.DataFrame(decision_record)
        price_record = pd.DataFrame(price_record)
        accepted_orders = pd.DataFrame(accepted_orders)
        executed_orders = pd.DataFrame(executed_orders)
        forecast_orders = pd.DataFrame(forecast_orders)
        killed_orders = pd.DataFrame(killed_orders)
        balancing_orders = pd.DataFrame(balancing_orders)

        if not decision_record.empty:
            decision_record["hour"] = pd.to_datetime(decision_record["hour"], utc=True)
        if not price_record.empty:
            price_record["hour"] = pd.to_datetime(price_record["hour"], utc=True)
        if not accepted_orders.empty:
            accepted_orders["time"] = pd.to_datetime(accepted_orders["time"], utc=True)
            accepted_orders["start"] = pd.to_datetime(accepted_orders["start"], utc=True)
            accepted_orders["cancel"] = pd.to_datetime(accepted_orders["cancel"], utc=True)
            accepted_orders["delivery"] = pd.to_datetime(accepted_orders["delivery"], utc=True)
        if not executed_orders.empty:
            executed_orders["time"] = pd.to_datetime(executed_orders["time"], utc=True)
            executed_orders["last_solve_time"] = pd.to_datetime(executed_orders["last_solve_time"], utc=True)
            executed_orders["hour"] = pd.to_datetime(executed_orders["hour"], utc=True)
        if not forecast_orders.empty:
            forecast_orders["time"] = pd.to_datetime(forecast_orders["time"], utc=True)
            forecast_orders["last_solve_time"] = pd.to_datetime(forecast_orders["last_solve_time"], utc=True)
            forecast_orders["hour"] = pd.to_datetime(forecast_orders["hour"], utc=True)
        if not killed_orders.empty:
            killed_orders["time"] = pd.to_datetime(killed_orders["time"], utc=True)
            killed_orders["last_solve_time"] = pd.to_datetime(killed_orders["last_solve_time"], utc=True)
            killed_orders["hour"] = pd.to_datetime(killed_orders["hour"], utc=True)
        if not balancing_orders.empty:
            balancing_orders["time"] = pd.to_datetime(balancing_orders["time"], utc=True)
            balancing_orders["hour"] = pd.to_datetime(balancing_orders["hour"], utc=True)

        logs = {
            "decision_record": pd.DataFrame(decision_record, index=None),
            "price_record": pd.DataFrame(price_record, index=None),
            "accepted_orders": pd.DataFrame(accepted_orders, index=None),
            "executed_orders": pd.DataFrame(executed_orders, index=None),
            # "forecast_orders": pd.DataFrame(forecast_orders, index=None), # removed for later versions of the code
            "killed_orders": pd.DataFrame(killed_orders, index=None),
            # "balancing_orders": pd.DataFrame(balancing_orders, index=None), # removed for later versions of the code
        }
        return logs

    def get_transactions(self):
        """
        Retrieve all transactions that have occurred since the last call and clear the internal transaction log.

        Returns:
            pd.DataFrame: A DataFrame containing all transactions that occurred, with the following columns:
                - timestamp: The UTC timestamp when the transaction occurred.
                - delivery_hour: The UTC timestamp of the delivery hour for the traded product.
                - price: The execution price of the transaction (EUR/MWh).
                - volume: The volume of the transaction (MW).
                - buy_order_type: The type of the buy order ('Market' or 'Limit').
                - sell_order_type: The type of the sell order ('Market' or 'Limit').
                - buy_order_id: The ID of the buy order.
                - sell_order_id: The ID of the sell order.
        """
        transactions = self._sim_cpp.getTransactions()
        transactions = pd.DataFrame(transactions)
        if not transactions.empty:
            transactions["timestamp"] = pd.to_datetime(transactions["timestamp"], utc=True)
            transactions["delivery_hour"] = pd.to_datetime(transactions["delivery_hour"], utc=True)
        return transactions
    
    def print_parameters(self):
        """
        Print the simulation parameters, including start/end times, storage settings, and various limits and costs.

        Processing Steps:
            - Extract simulation start, end, and trading start times from internal parameters.
            - Display all relevant storage configuration parameters.
            - Show trading and technical constraints.
        """
        startMonth = self._sim_cpp.params.startMonth
        startDay = self._sim_cpp.params.startDay
        startYear = self._sim_cpp.params.startYear
        startHour = self._sim_cpp.params.startHour
        startMinute = self._sim_cpp.params.startMinute
        endMonth = self._sim_cpp.params.endMonth
        endDay = self._sim_cpp.params.endDay
        endYear = self._sim_cpp.params.endYear
        endHour = self._sim_cpp.params.endHour
        endMinute = self._sim_cpp.params.endMinute
        tradingStartMonth = self._sim_cpp.params.tradingStartMonth
        tradingStartDay = self._sim_cpp.params.tradingStartDay
        tradingStartYear = self._sim_cpp.params.tradingStartYear
        tradingStartHour = self._sim_cpp.params.tradingStartHour
        tradingStartMinute = self._sim_cpp.params.tradingStartMinute

        startDate = pd.Timestamp(year=startYear, month=startMonth, day=startDay, hour=startHour, minute=startMinute, tz="UTC")
        endDate = pd.Timestamp(year=endYear, month=endMonth, day=endDay, hour=endHour, minute=endMinute, tz="UTC")
        tradingStartDate = pd.Timestamp(year=tradingStartYear, month=tradingStartMonth, day=tradingStartDay, hour=tradingStartHour, minute=tradingStartMinute, tz="UTC")

        print("Start Time (UTC):", startDate)
        print("End Time (UTC):", endDate)
        print("Trading Start Time (UTC):", tradingStartDate)

        print("Storage Maximum:", self._sim_cpp.params.storageMax, "MWh")
        print("Linear Degredation Cost:", self._sim_cpp.params.linDegCost, "€/MWh")
        print("Injection Loss η+:", self._sim_cpp.params.lossIn)
        print("Withdrawal Loss η-:", self._sim_cpp.params.lossOut)
        print("Trading Fee:", self._sim_cpp.params.tradingFee, "€/MWh")
        print("Number of DP Storage States:", self._sim_cpp.params.numStorStates)
        print("Technical Delay:", self._sim_cpp.params.pingDelay, "ms")
        print("Trading Delay:", self._sim_cpp.params.minuteDelay, "min")
        print("Fixed Solve Time:", self._sim_cpp.params.fixedSolveTime, "ms")
        print("Solve Frequency:", self._sim_cpp.params.dpFreq, "min")
        print("Injection Maximum:", self._sim_cpp.params.injectMax, "MW")
        print("Withdrawal Maximum:", self._sim_cpp.params.withdrawMax, "MW")
        print("Log Transactions:", self._sim_cpp.params.logTransactions)
        # print("Forecast Horizon Start:", self._sim_cpp.params.foreHorizonStart, "min")
        # print("Forecast Horizon End:", self._sim_cpp.params.foreHorizonEnd, "min")
    
    def return_vol_price_pairs(self, is_last: bool, frequency: int, volumes: np.ndarray):
        """
        Retrieve volume-price pairs from the simulation.

        Args:
            is_last (bool): If True, indicates this is the last iteration of data.
            frequency (int): The frequency (in seconds) at which price data is retrieved.
            volumes (np.ndarray): A 1D numpy array of volumes for which prices are returned.

        Processing Steps:
            - Validate input parameters for correct format and values.
            - Extract volume-price data from the simulation at specified frequency.
            - Convert timestamps to UTC format for consistency.

        Returns:
            pd.DataFrame: A DataFrame with columns:
                - current_time: Time of the export (UTC).
                - delivery_hour: Delivery period time (UTC).
                - volume: The volume for which the price is exported (MWh).
                - price_full: The full price (cashflow) for the volume (€).
                - worst_accepted_price: Market price of the worst matched order (€/MWh).
        """
        if len(volumes.shape) != 1:
            raise ValueError("volumes must be a 1D numpy array")
        if frequency <= 0:
            raise ValueError("frequency must be > 0")
        
        vol_price_list = self._sim_cpp.return_vol_price_pairs(is_last, frequency, volumes)
        vol_price_list = pd.DataFrame(vol_price_list)

        if not vol_price_list.empty:
            vol_price_list["current_time"] = pd.to_datetime(vol_price_list["current_time"], utc=True)
            vol_price_list["delivery_hour"] = pd.to_datetime(vol_price_list["delivery_hour"], utc=True)
            
        return vol_price_list

    def submit_limit_orders(self, df: pd.DataFrame):
        """
        Submit a list of limit orders and track their matches without battery optimization.

        This method validates input data and queues the limit orders for submission at specified times.
        The orders will be submitted during the normal simulation run without triggering battery optimization.

        Args:
            df (pd.DataFrame): A DataFrame containing the limit orders to be submitted.
                The DataFrame must have the following columns:
                    - transaction_time: The time when the order should be submitted (timezone aware, up to millisecond precision).
                    - price: The price of the limit order (€/MWh).
                    - volume: The volume of the limit order (MWh, positive for buy, negative for sell).
                    - side: The side of the order ('buy' or 'sell').
                    - delivery_time: The delivery time for the order (timezone aware, required).

        Processing Steps:
            - Validates input data format and required columns.
            - Ensures timezone awareness and proper formatting of timestamps.
            - Queues the limit orders for submission during simulation execution.
            - Orders are processed without triggering battery optimization.

        Returns:
            None: This method queues orders but does not return match information.
                After running the simulation, use get_limit_order_matches() to retrieve match details.

        Note:
            Call this method to queue own limit orders, then run the simulation to process them and collect matches.
            Use get_limit_order_matches() after simulation to retrieve final match results.
        """
        
        # Validate input DataFrame
        required_columns = ['transaction_time', 'price', 'volume', 'side', 'delivery_time']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Check if transaction_time is timezone aware
        if df["transaction_time"].dt.tz is None:
            raise ValueError("transaction_time must be timezone aware")
        if df["transaction_time"].isna().any():
            raise ValueError("transaction_time cannot contain NaT values - all transaction times are required")
            
        # Check if delivery_time is timezone aware and has no NaT values
        if df["delivery_time"].dt.tz is None:
            raise ValueError("delivery_time must be timezone aware")
        if df["delivery_time"].isna().any():
            raise ValueError("delivery_time cannot contain NaT values - all delivery times are required")

        # check that the delivery time is a full hour exactly
        if (df["delivery_time"].dt.minute != 0).any():
            raise ValueError("delivery_time must be a full hour exactly for hourly products")

        # volume must be > 0
        if df["volume"].le(0).any():
            raise ValueError("volume must be > 0")
        
        # Convert to UTC
        df = df.copy()
        df["transaction_time"] = df["transaction_time"].dt.tz_convert("UTC")
        df["delivery_time"] = df["delivery_time"].dt.tz_convert("UTC")
        
        # Validate side column
        valid_sides = {'buy', 'sell', 'Buy', 'Sell', 'BUY', 'SELL'}
        invalid_sides = df["side"].unique()
        invalid_sides = [side for side in invalid_sides if side not in valid_sides]
        if invalid_sides:
            raise ValueError(f"Invalid side values: {invalid_sides}. Must be one of: {valid_sides}")
        
        # Normalize side values to 'Buy'/'Sell'
        df["side"] = df["side"].str.capitalize()
        
        # Convert timestamps to ISO format
        df["transaction_time"] = df["transaction_time"].dt.tz_localize(None).dt.strftime('%Y-%m-%dT%H:%M:%S.%f').str[:-3] + 'Z'
        df["delivery_time"] = df["delivery_time"].dt.tz_localize(None).dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        # Prepare data for C++ function
        transaction_times = df["transaction_time"].to_numpy(dtype='str').tolist()
        prices = df["price"].to_numpy(dtype=np.float64).tolist()
        volumes = df["volume"].to_numpy(dtype=np.float64).tolist()
        sides = df["side"].to_numpy(dtype='str').tolist()
        delivery_times = df["delivery_time"].to_numpy(dtype='str').tolist()
        
        # Call C++ function to submit limit orders (no return value)
        self._sim_cpp.submitLimitOrdersAndGetMatches(transaction_times, prices, volumes, sides, delivery_times)
    
    def get_limit_order_matches(self):
        """
        Get the limit order matches collected during simulation using the forecast tracking mechanism.

        This method retrieves match information for submitted limit orders that were processed
        during the simulation run. The orders are tracked using the forecast flag system.

        Processing Steps:
            - Retrieves match data from the C++ simulation backend.
            - Converts timestamps to timezone-aware datetime objects.
            - Clears the internal match storage after retrieval.

        Returns:
            pd.DataFrame: A DataFrame containing information about which limit orders were matched against which existing orders.
                The DataFrame contains the following columns:
                    - submitted_order_id: The ID of the submitted limit order.
                    - matched_order_id: The ID of the existing order that was matched.
                    - match_timestamp: The timestamp when the match occurred.
                    - delivery_hour: The delivery hour for the matched order.
                    - match_price: The price at which the orders were matched, i.e., the price of the existing (partially) matched order (€/MWh).
                    - match_volume: The volume that was matched (MWh).
                    - submitted_order_side: The side of the submitted order ('buy' or 'sell').
                    - existing_order_side: The side of the existing order ('buy' or 'sell').
        """
        matches = self._sim_cpp.getLimitOrderMatches()
        matches_df = pd.DataFrame(matches)
        
        # Convert timestamps to datetime if not empty
        if not matches_df.empty:
            matches_df["match_timestamp"] = pd.to_datetime(matches_df["match_timestamp"], utc=True)
            matches_df["delivery_hour"] = pd.to_datetime(matches_df["delivery_hour"], utc=True)
        else:
            print("No limit order matches to return.")

        self._sim_cpp.clearLimitOrderMatches() # clear existing matches
        
        return matches_df