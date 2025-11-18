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
import os
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
                 log_transactions=False,
                 only_traverse_lob=False,
                 cycle_limit: float = None,):
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
            only_traverse_lob: Whether to only traverse the LOB and not call any DP solves. (bool, default: False)
            cycle_limit: The limit on the number of cycles per Berlin-time day. Setting it comes at a cost in terms of solve time. (float, > 0). Default is None, where no cycle limit is enforced.
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
        if cycle_limit is not None:
            if cycle_limit <= 0:
                raise ValueError("cycle_limit must be > 0 if provided")
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
        self._sim_cpp.params.onlyTraverseLOB = only_traverse_lob
        if cycle_limit is not None:
            self._sim_cpp.params.cycleLimit = float(cycle_limit)
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
        
        base_path = os.path.join(base_path, '')
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
            decision_record["cycles"] = np.round(decision_record["cycles"].astype(float), 2)
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
        cycleLimit = self._sim_cpp.params.cycleLimit

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
        print("Only Traverse LOB:", self._sim_cpp.params.onlyTraverseLOB)
        print("Cycle Limit:", cycleLimit)
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

    def has_orders_remaining(self) -> bool:
        """
        Check if there are remaining orders in the order queue.
        
        Returns
        -------
        bool
            True if there are remaining orders in the queue, False otherwise.
        """
        return self._sim_cpp.hasOrdersRemaining()

    def set_stop_time(self, stop_time: pd.Timestamp):
        """
        Set a datetime with millisecond precision to stop the simulation once.
        
        The simulation will stop only once, if the last order added has a submission time
        after the stop time. Once the simulation has stopped, the stop time is automatically
        cleared, allowing you to set a new one.
        
        Parameters
        ----------
        stop_time : pd.Timestamp
            A timezone-aware timestamp with millisecond precision when the simulation should stop.
            The simulation will stop if the last processed order's submission time is > this stop time.
        
        Raises
        ------
        ValueError
            If stop_time is not timezone aware.
        
        Notes
        -----
        - The stop time is checked after each order is processed
        - The simulation stops only once per stop time setting
        - After stopping, the stop time is automatically cleared
        - You can set a new stop time after the simulation has stopped
        - The stop time is compared against the order's submission time (transaction time)
        
        """
        # Check if timezone aware
        if stop_time.tzinfo is None:
            raise ValueError("stop_time must be timezone aware")
        
        # Convert to UTC
        stop_time_utc = stop_time.astimezone(pytz.utc)
        
        # Convert to milliseconds since epoch
        stop_time_ms = int(stop_time_utc.timestamp() * 1000)
        
        # Call C++ method
        self._sim_cpp.setStopTime(stop_time_ms)

    def solve(self) -> pd.DataFrame:
        """
        Solve the dynamic programming problem once using the time of the last placed order.

        Returns
        -------
        pd.DataFrame
            A DataFrame containing the suggested to be executed market orders from the solve.
            Columns include: dp_run, time, last_solve_time, hour, reward,
            reward_incl_deg_costs, volume, type, final_pos, final_stor.

        Notes
        -----
        This function calls the C++ solve() method once. It does not run the
        full simulation, only performs a single DP solve at the time of the
        last placed order. If no orders have been placed yet, the behavior
        depends on the initial state of _lastOrder_placementTime.

        Example
        -------
        >>> orders_df = sim.solve()
        """
        # Call C++ method (no parameters needed - uses last order placement time)
        order_list = self._sim_cpp.solve()
        
        # Convert list of dicts to pandas DataFrame
        if not order_list:
            # Return empty DataFrame with expected columns
            return pd.DataFrame(columns=[
                'dp_run', 'time', 'last_solve_time', 'hour', 'reward',
                'reward_incl_deg_costs', 'volume', 'type', 'final_pos', 'final_stor'
            ])
        
        order_df = pd.DataFrame(order_list)
        order_df['time'] = pd.to_datetime(order_df['time'], utc=True)
        order_df['last_solve_time'] = pd.to_datetime(order_df['last_solve_time'], utc=True)
        order_df['hour'] = pd.to_datetime(order_df['hour'], utc=True)
        
        return order_df

    def transform_lob_to_levels(
        self,
        lob_state_df: pd.DataFrame,
        exchange: str = "EPEX",
        product_name: str = "XBID_Hour_Power",
        delivery_area: str = "10YDE-VE-------2",
        product_duration_hours: int = 1
    ) -> pd.DataFrame:
        """
        Transforms the output of get_limit_order_book_state (individual orders)
        into an aggregated, price-level-based DataFrame.

        Parameters
        ----------
        lob_state_df : pd.DataFrame
            The DataFrame returned by get_limit_order_book_state.
            Must contain columns: 'delivery_time', 'side', 'price', 'volume'.
        exchange : str, optional
            Static value for the 'exchange' column in the output.
        product_name : str, optional
            Static value for the 'product' column in the output.
        delivery_area : str, optional
            Static value for the 'deliveryArea' column in the output.
        product_duration_hours : int, optional
            Duration of the product in hours, used to calculate
            deliveryEndUtc from delivery_time (which is used as deliveryStartUtc).
            Default is 1.

        Returns
        -------
        pd.DataFrame
            A DataFrame in the target format with aggregated price levels and columns:
            ['exchange', 'product', 'deliveryStartUtc', 'deliveryEndUtc',
            'deliveryArea', 'side', 'level', 'price', 'quantity']
        """
        
        # Define the target column order
        target_columns = [
            'exchange', 'product', 'deliveryStartUtc', 'deliveryEndUtc',
            'deliveryArea', 'side', 'level', 'price', 'quantity'
        ]
        
        # Keep only the columns we need from the start
        source_columns = ['delivery_time', 'side', 'price', 'volume']
        
        # Handle empty input DataFrame
        if lob_state_df.empty:
            return pd.DataFrame(columns=target_columns)

        all_orders_dfs = []
        product_duration = pd.Timedelta(hours=product_duration_hours)

        # Group by each product (identified by its delivery_time)
        for delivery_time, product_df in lob_state_df[source_columns].groupby('delivery_time'):
            
            delivery_start_utc = delivery_time
            delivery_end_utc = delivery_start_utc + product_duration

            # --- Process Bids (Source 'buy' side) ---
            buys_df = product_df[product_df['side'] == 'buy']
            if not buys_df.empty:
                # We assume buys_df is already sorted by price (descending)
                bids_1_to_1 = buys_df.copy().reset_index(drop=True)
                
                # Set level as the order rank
                bids_1_to_1['level'] = bids_1_to_1.index
                bids_1_to_1['side'] = 'bid'
                bids_1_to_1 = bids_1_to_1.rename(columns={'volume': 'quantity'})

                # Add common metadata
                bids_1_to_1['exchange'] = exchange
                bids_1_to_1['product'] = product_name
                bids_1_to_1['deliveryStartUtc'] = delivery_start_utc
                bids_1_to_1['deliveryEndUtc'] = delivery_end_utc
                bids_1_to_1['deliveryArea'] = delivery_area
                
                all_orders_dfs.append(bids_1_to_1[target_columns]) # Select only target cols

            # --- Process Asks (Source 'sell' side) ---
            sells_df = product_df[product_df['side'] == 'sell']
            if not sells_df.empty:
                # We assume sells_df is already sorted by price (ascending)
                asks_1_to_1 = sells_df.copy().reset_index(drop=True)

                # Set level as the order rank
                asks_1_to_1['level'] = asks_1_to_1.index
                asks_1_to_1['side'] = 'ask'
                asks_1_to_1 = asks_1_to_1.rename(columns={'volume': 'quantity'})

                # Add common metadata
                asks_1_to_1['exchange'] = exchange
                asks_1_to_1['product'] = product_name
                asks_1_to_1['deliveryStartUtc'] = delivery_start_utc
                asks_1_to_1['deliveryEndUtc'] = delivery_end_utc
                asks_1_to_1['deliveryArea'] = delivery_area
                
                all_orders_dfs.append(asks_1_to_1[target_columns]) # Select only target cols

        # Handle case where input was not empty but contained no orders
        if not all_orders_dfs:
            return pd.DataFrame(columns=target_columns)

        # Combine all products and sides into one DataFrame
        final_df = pd.concat(all_orders_dfs, ignore_index=True)

        return final_df

    def get_limit_order_book_state(self, max_action: float = None):
        """
        Get the current state of all active limit order books at the simulation's current time.
        
        This method returns, for each tradable product (delivery hour), the individual limit orders
        in the buy and sell queues with all their attributes, up to a cumulative volume of max_action.
        The query time is automatically set to the simulation's current time (last processed order).
        
        Parameters
        ----------
        max_action : float, optional
            The maximum cumulative volume to query in MW (= MWh for 1-hour products).
            If None (default), uses inject_max + withdraw_max from simulation parameters.
            Must be > 0 if specified.
        
        Returns
        -------
        pd.DataFrame
            A DataFrame containing the limit orders with the following columns:
                - delivery_time: The delivery time of the product (UTC timestamp)
                - side: 'sell' or 'buy' (sell orders are where you can buy from, buy orders are where you can sell to)
                - order_id: The unique order ID
                - initial_id: The initial order ID (for tracking order modifications)
                - start_time: When the order was placed (UTC timestamp)
                - cancel_time: When the order expires (UTC timestamp)
                - price: The limit order price in EUR/MWh
                - volume: The order volume in MWh
                - is_forecast: Whether this is a forecast order (bool)
                - cumulative_volume: The cumulative volume up to and including this order in MWh
        
        Notes
        -----
        - Uses the simulation's internal current time (_lastOrder_placementTime)
        - Sell orders are sorted by ascending price (cheapest first = best for buying)
        - Buy orders are sorted by descending price (highest first = best for selling)
        - Orders are filtered to exclude expired orders at the query time
        - Cumulative volume stops at max_action (default: inject_max + withdraw_max)
        - Each row represents one limit order in the order book
        
        Example
        -------
        >>> # Query order book state with default max_action (inject_max + withdraw_max)
        >>> lob_state = sim.get_limit_order_book_state()
        >>> # Query with custom max_action
        >>> lob_state = sim.get_limit_order_book_state(max_action=20.0)
        >>> # Filter to see sell orders for a specific product
        >>> product_sells = lob_state[(lob_state['delivery_time'] == some_time) & (lob_state['side'] == 'sell')]
        >>> # See the best (cheapest) sell price
        >>> best_sell_price = product_sells.iloc[0]['price']
        >>> # Filter to see only forecast orders
        >>> forecast_orders = lob_state[lob_state['is_forecast'] == True]
        """
        # Determine max_action value
        if max_action is None:
            # Use inject_max + withdraw_max as default
            max_action_value = self._sim_cpp.params.injectMax + self._sim_cpp.params.withdrawMax
        else:
            # Validate that max_action is positive
            if max_action <= 0:
                raise ValueError("max_action must be > 0")
            max_action_value = max_action
        
        # Call C++ function (uses simulation's current time internally)
        lob_state_dict = self._sim_cpp.getLimitOrderBookState(max_action_value)
        
        # Convert to DataFrame
        rows = []
        for delivery_time_ms, data in lob_state_dict.items():
            delivery_time = pd.Timestamp(delivery_time_ms, unit='ms', tz='UTC')
            
            # Process sell orders (where we can buy from)
            sell_ids = data['sell_ids']
            sell_initial_ids = data['sell_initial_ids']
            sell_starts = data['sell_starts']
            sell_cancels = data['sell_cancels']
            sell_prices = data['sell_prices']
            sell_volumes = data['sell_volumes']
            sell_forecasts = data['sell_forecasts']
            
            cumulative_sell_volume = 0.0
            for order_id, initial_id, start, cancel, price, volume, forecast in zip(
                sell_ids, sell_initial_ids, sell_starts, sell_cancels, sell_prices, sell_volumes, sell_forecasts
            ):
                cumulative_sell_volume += volume
                # Handle sentinel cancel time values (e.g., max int64) that overflow pandas timestamps
                cancel_ts = pd.NaT if int(cancel) > pd.Timestamp.max.value // 1_000_000 else pd.Timestamp(int(cancel), unit='ms', tz='UTC')
                rows.append({
                    'delivery_time': delivery_time,
                    'side': 'sell',
                    'order_id': int(order_id),
                    'initial_id': int(initial_id),
                    'start_time': pd.Timestamp(int(start), unit='ms', tz='UTC'),
                    'cancel_time': cancel_ts,
                    'price': price,
                    'volume': volume,
                    'is_forecast': bool(forecast),
                    'cumulative_volume': cumulative_sell_volume
                })
            
            # Process buy orders (where we can sell to)
            buy_ids = data['buy_ids']
            buy_initial_ids = data['buy_initial_ids']
            buy_starts = data['buy_starts']
            buy_cancels = data['buy_cancels']
            buy_prices = data['buy_prices']
            buy_volumes = data['buy_volumes']
            buy_forecasts = data['buy_forecasts']
            
            cumulative_buy_volume = 0.0
            for order_id, initial_id, start, cancel, price, volume, forecast in zip(
                buy_ids, buy_initial_ids, buy_starts, buy_cancels, buy_prices, buy_volumes, buy_forecasts
            ):
                cumulative_buy_volume += volume
                # Handle sentinel cancel time values (e.g., max int64) that overflow pandas timestamps
                cancel_ts = pd.NaT if int(cancel) > pd.Timestamp.max.value // 1_000_000 else pd.Timestamp(int(cancel), unit='ms', tz='UTC')
                rows.append({
                    'delivery_time': delivery_time,
                    'side': 'buy',
                    'order_id': int(order_id),
                    'initial_id': int(initial_id),
                    'start_time': pd.Timestamp(int(start), unit='ms', tz='UTC'),
                    'cancel_time': cancel_ts,
                    'price': price,
                    'volume': volume,
                    'is_forecast': bool(forecast),
                    'cumulative_volume': cumulative_buy_volume
                })
        
        df = pd.DataFrame(rows)
        return df