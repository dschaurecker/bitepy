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
                 storage_max=10.,
                 lin_deg_cost=4.,
                 loss_in=0.95,
                 loss_out=0.95,
                 trading_fee=0.09,
                 num_stor_states=11,
                 tec_delay=0,
                 fixed_solve_time=0,
                 solve_frequency=0.,
                 withdraw_max=10.,
                 inject_max=10.):
                #  forecast_horizon_start=10*60,
                #  forecast_horizon_end=75):
        """
        Initialize a Simulation instance.

        Args:
            start_date (pd.Timestamp): The start datetime of the simulation. Must be timezone aware.
            end_date (pd.Timestamp): The end datetime of the simulation. Must be timezone aware.
            storage_max (float, optional): The maximum storage capacity of the storage unit (MWh). Default is 10.0.
            lin_deg_cost (float, optional): The linear degradation cost of the storage unit (€/MWh). Default is 4.0.
            loss_in (float, optional): The injection efficiency of the storage unit (0-1]. Default is 0.95.
            loss_out (float, optional): The withdrawal efficiency of the storage unit (0-1]. Default is 0.95.
            trading_fee (float, optional): The trading fee for the exchange (€/MWh). Default is 0.09.
            num_stor_states (int, optional): The number of storage states for dynamic programming. Default is 11.
            tec_delay (int, optional): The technical delay of the storage unit (ms, >= 0). Default is 0.
            fixed_solve_time (int, optional): The fixed solve time for dynamic programming (ms, >= 0 or -1 for realistic solve times). Default is 0.
            solve_frequency (float, optional): The frequency at which the dynamic programming solver is run (min). Default is 0.0.
            withdraw_max (float, optional): The maximum withdrawal power of the storage unit (MW). Default is 10.0.
            inject_max (float, optional): The maximum injection power of the storage unit (MW). Default is 10.0.
        """
        # forecast_horizon_start (int, optional): The start of the forecast horizon (min). Default is 600.
        # forecast_horizon_end (int, optional): The end of the forecast horizon (min). Default is 75.

        # write all the assertions
        if start_date >= end_date:
            raise ValueError("start_date must be before end_date")
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
        if end_date.tzinfo is None:
            raise ValueError("end_date must be timezone aware")
        end_date = end_date.astimezone(pytz.utc)
        self._sim_cpp.params.endMonth = end_date.month
        self._sim_cpp.params.endDay = end_date.day
        self._sim_cpp.params.endYear = end_date.year
        self._sim_cpp.params.endHour = end_date.hour

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
        start_date_utc = start_date.tz_convert('UTC')
        end_date_utc = end_date.tz_convert('UTC')

        if base_path[-1] != '/':
            base_path += '/'
        base_path += "orderbook_"

        paths = []
        current_date = start_date_utc
        while current_date < end_date_utc + timedelta(days=1):
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
        """
        start_date = pd.Timestamp(year=self._sim_cpp.params.startYear,
                                  month=self._sim_cpp.params.startMonth,
                                  day=self._sim_cpp.params.startDay,
                                  hour=self._sim_cpp.params.startHour,
                                  tz="UTC")
        end_date = pd.Timestamp(year=self._sim_cpp.params.endYear,
                                month=self._sim_cpp.params.endMonth,
                                day=self._sim_cpp.params.endDay,
                                hour=self._sim_cpp.params.endHour,
                                tz="UTC")
        lob_paths = self.get_data_bins_for_each_day(data_path, start_date, end_date)

        num_days = len(lob_paths)
        print("The simulation will iterate over", num_days, "files.")

        with tqdm(total=num_days, desc="Simulated Days", unit="%", ncols=120, disable=not verbose) as pbar:
            for i, path in enumerate(lob_paths):
                pbar.set_description(f"Currently simulating {path.split('/')[-1]} ... ")
                self.add_bin_to_orderqueue(path)
                self.run_one_day(i == len(lob_paths) - 1)
                pbar.update(1)

        print("Simulation finished.")
        
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
    
    def print_parameters(self):
        """
        Print the simulation parameters, including start/end times, storage settings, and various limits and costs.
        """
        startMonth = self._sim_cpp.params.startMonth
        startDay = self._sim_cpp.params.startDay
        startYear = self._sim_cpp.params.startYear
        startHour = self._sim_cpp.params.startHour
        endMonth = self._sim_cpp.params.endMonth
        endDay = self._sim_cpp.params.endDay
        endYear = self._sim_cpp.params.endYear
        endHour = self._sim_cpp.params.endHour

        startDate = pd.Timestamp(year=startYear, month=startMonth, day=startDay, hour=startHour, tz="UTC")
        endDate = pd.Timestamp(year=endYear, month=endMonth, day=endDay, hour=endHour, tz="UTC")
        print("Start Time (UTC):", startDate)
        print("End Time (UTC):", endDate)

        print("Storage Maximum:", self._sim_cpp.params.storageMax, "MWh")
        print("Linear Degredation Cost:", self._sim_cpp.params.linDegCost, "€/MWh")
        print("Injection Loss η+:", self._sim_cpp.params.lossIn)
        print("Withdrawal Loss η-:", self._sim_cpp.params.lossOut)
        print("Trading Fee:", self._sim_cpp.params.tradingFee, "€/MWh")
        print("Number of DP Storage States:", self._sim_cpp.params.numStorStates)
        print("Technical Delay:", self._sim_cpp.params.pingDelay, "ms")
        print("Fixed Solve Time:", self._sim_cpp.params.fixedSolveTime, "ms")
        print("Solve Frequency:", self._sim_cpp.params.dpFreq, "min")
        print("Injection Maximum:", self._sim_cpp.params.injectMax, "MW")
        print("Withdrawal Maximum:", self._sim_cpp.params.withdrawMax, "MW")
        # print("Forecast Horizon Start:", self._sim_cpp.params.foreHorizonStart, "min")
        # print("Forecast Horizon End:", self._sim_cpp.params.foreHorizonEnd, "min")
    
    def return_vol_price_pairs(self, is_last: bool, frequency: int, volumes: np.ndarray):
        """
        Retrieve volume-price pairs from the simulation.

        Args:
            is_last (bool): If True, indicates this is the last iteration of data.
            frequency (int): The frequency (in seconds) at which price data is retrieved.
            volumes (np.ndarray): A 1D numpy array of volumes for which prices are returned.

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