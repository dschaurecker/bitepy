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
import matplotlib.pyplot as plt
from . import heatmap as hm

class Results:
    def __init__(self, logs: dict):
        """
        Initialize a Simulation instance.

        Args:
            logs (dict): A dictionary containing the get_logs() output of the simulation class.
        """
        
        self.logs = logs

    def get_total_reward(self):
        return np.round(self.logs["decision_record"]['full_reward'].sum(),2)
    
    def plot_decision_chart(self,lleft: int = 0,lright: int = -1):
        """
        Plot the storage, market-position, and reward of the agent over the selected simulation period.

        Args:
            lleft (int): The left index of the simulation period.
            lright (int): The right index of the simulation period.
        """
        df = self.logs["decision_record"]

        # plot storage, position, and reward where reward is in a seperate axis below
        fig1, ax1 = plt.subplots(figsize=(18, 10))
        ax2 = ax1.twinx()
        ax1.plot(df["hour"][lleft:lright], df['storage'][lleft:lright], color='blue')
        #plot position as points not line
        ax1.plot(df["hour"][lleft:lright], df['position'][lleft:lright], 'o', color='red')


        ax2.plot(df["hour"][lleft:lright], df['full_reward'][lleft:lright], color='green')
        ax1.set_xlabel('Time ')
        ax1.set_ylabel('Storage (MWh)')
        ax2.set_ylabel('Reward (€)')
        # plot a horizontal line at 0
        ax2.axhline(y=0, color='green', linestyle='--', linewidth=1.5, alpha=0.5)
        ax1.legend(['storage', 'position'], loc='upper left')
        ax2.legend(['reward'], loc='upper right')
        #set gridlines
        # plot vertical grid line for each hour

        # # array for each hour between lleft and lright
        # hours = pd.date_range(start=df["hour"].iloc[lleft], end=df["hour"].iloc[lright], freq='D')
        # for hour in hours:
        #     ax1.axvline(x=hour, color='gray', linestyle='--', linewidth=0.5)

        ax1.grid(True, alpha=0.5)
        plt.show()

        fig1, ax1 = plt.subplots(figsize=(18, 10))
        #plot cumulative reward
        ax1.plot(df["hour"][lleft:lright], df['full_reward'].cumsum()[lleft:lright], color='blue')
        ax1.set_xlabel('Time ')
        ax1.set_ylabel('Cumulative Reward (€)')
        ax1.grid(True, alpha=0.5)
        plt.show()

    def plot_heatmap(self):
        """
        Plot a heatmap of the final storage positions and visualize the executed orders over the simulation period.
        Heatmap plots adapted from: https://github.com/bitstoenergy/iclr-smartmeteranalytics by Markus Kreft.
        """

        df = self.logs["decision_record"]
        df.index = df["hour"]
        df = df.drop(columns=["hour"])

        exec_df = self.logs["executed_orders"].drop(columns=["dp_run", "last_solve_time", "final_pos", "final_stor"])
        exec_df.set_index('hour', inplace=True)
    
        # Create an empty list to store results
        daily_volumes = []

        # Iterate through unique dates in df
        for day in np.unique(df.index.date):
            # Filter the data for the current day
            daily_data = exec_df.loc[exec_df.index.date == day]
            
            # Calculate the largest daily volume and the summed daily volume
            largest_daily_vol = daily_data["volume"].max()
            summed_daily_vol = daily_data["volume"].sum()
            
            # Append the results as a dictionary
            daily_volumes.append({
                "date": day,
                "max_vol": largest_daily_vol,
                "summed_vol": summed_daily_vol
            })

        # Create a DataFrame from the list of dictionaries
        daily_volumes_df = pd.DataFrame(daily_volumes)

        # Set the 'date' column as the index
        daily_volumes_df.set_index("date", inplace=True)
        daily_volumes_df.index = pd.to_datetime(daily_volumes_df.index).tz_localize("UTC")


        fig = hm.HeatmapFigure(df, daily_volumes_df, 'storage', interval_minutes=60, figsize=(14, 8))
        plt.show()

