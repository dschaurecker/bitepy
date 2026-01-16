######################################################################
# Copyright (C) 2026 ETH Zurich
# BitePy: A Python Battery Intraday Trading Engine
# Bits to Energy Lab - Chair of Information Management - ETH Zurich
#
# Author: David Schaurecker
#
# Licensed under MIT License, see https://opensource.org/license/mit
######################################################################

import datetime as dt
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.dates as mdates
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.colors import LogNorm
import types
import matplotlib
from matplotlib.ticker import AutoMinorLocator

"""
Code adapted from https://github.com/bitstoenergy/iclr-smartmeteranalytics by Markus Kreft.
"""

COLOR_AXES = "#999999"
COLOR_FACE = "#999999"

DEFAULT_FIGRATIO = 1.618
DEFAULT_FIGWIDTH = 8
DEFAULT_FIGHEIGHT = DEFAULT_FIGWIDTH / DEFAULT_FIGRATIO
DEFAULT_FIGSIZE = (DEFAULT_FIGWIDTH, DEFAULT_FIGHEIGHT)

plt.rcParams["figure.figsize"] = DEFAULT_FIGSIZE
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.size"] = 13
# plt.rcParams["savefig.dpi"] = 300
plt.rcParams["savefig.bbox"] = "tight"
plt.rcParams["savefig.pad_inches"] = 0.02


def _datetime_from_time(time):
    # Time in local timezone
    # reult is not localized
    date_yaxis = dt.datetime(year=1970, month=1, day=1).date()
    mydt = dt.datetime.combine(date_yaxis, time)
    return mydt


def HeatmapFigure(
    df,
    exec_data,
    column,
    interval_minutes=None,
    timezone=None,
    title=None,
    ylabel=None,
    figsize=None,
    histy_label="Mean SoC\nProfile [MWh]",
    histx_label="Daily Traded\nEnergy [MWh]",
    cbar_label="SoC [MWh]",
    **kwargs,
):
    """
    Make a figure with a full heatmap, daily overview and annotations

    Parameter
    ---------
    df : pandas.Dataframe
        Pandas Dataframe that holds **power** measuements in `column`.
        Needs to have a timezone aware DateTimeIndex.
            Localized to local timezone unless parameter `timezone` is passed.
            Requires frequency, unless parameters `interval_minutes` is passed.

    column : str
        Name of the column with the power measurements.

    Returns
    -------
    matplotlib.figure
        Figure with the heatmap
    """

    # Norms and cmaps to try out:
    # norm = colors.TwoSlopeNorm(vcenter=0.)
    # norm = colors.CenteredNorm()
    # cmap = 'gist_rainbow_r'
    # cmap = 'guppy'
    # cmap = cmr.fusion_r,

    start_color = "#35626f"
    end_color = "#E55451"
    custom_map = LinearSegmentedColormap.from_list("custom_cmap", [start_color, end_color])

    if interval_minutes is None:
        # TODO complain if not set
        interval_minutes = df.index.freq.nanos / 60e9
        # interval_minutes = min(diff(df.index))

    if timezone is None:
        # TODO complain if not present
        # TODO localize if not localized
        timezone = df.index.tz

    # Generate the pivoted heatmap and corresponding time and date range
    data, daterange, timerange = _heatmap_data_from_pandas(df, column, interval_minutes)


    # Set up the figure and axes
    fig = plt.figure(figsize=(figsize[0], figsize[1] * 1.5))
    fig.suptitle(title)

    gs = fig.add_gridspec(2, 1, hspace=0.2,
        left=0.1,
        right=0.9,
        bottom=0.1,
        top=0.9,
        height_ratios=(6, 2)
    )

    gs0 = gs[0].subgridspec(2,
        2,
        width_ratios=(8, 1),
        height_ratios=(2, 6), #(2, 7)
        wspace=0.01,
        hspace=0.01 * DEFAULT_FIGRATIO,
    )
    
    ax = fig.add_subplot(gs0[1, 0])
    ax_histx = fig.add_subplot(gs0[0, 0])
    ax_histy = fig.add_subplot(gs0[1, 1])
    
    # SMALL COLORBAR
    #ax_cbar = ax_histx.inset_axes([1.085, 0, 0.035, 1]) #1.07

    # TODO for some reasons setting this for the ax only does not work, so we
    # modify the global defualt for now
    # -> probably have to add it explicitpy to lacators
    # ax.xaxis_date(tz=timezone)
    # ax.yaxis_date(tz=timezone)
    # ax_histx.xaxis_date(tz=timezone)
    # ax_histy.yaxis_date(tz=timezone)
    plt.rcParams["timezone"] = str(timezone)

    _plot_hists(
        daterange,
        timerange,
        data,
        exec_data,
        ax_histx,
        ax_histy,
        interval_minutes,
        histx_label=histx_label,
        histy_label=histy_label,
    )
    
    mesh = plot_pcolormesh(ax, daterange, timerange, data, custom_map, **kwargs)

    # SMALL COLORBAR
    # cbar = fig.colorbar(
    # mesh,
    # cax=ax_cbar,
    # label=cbar_label,
    # ticks=[0,2,4,6,8,10]
    # )
    
    # # Customize the colorbar outline
    # cbar.outline.set_color(COLOR_AXES)
    # cbar.outline.set_linewidth(0)
    
    # # Set colorbar ticks at 0, 2, 4, 6, 8, 10
    # cbar.set_ticks([0, 2, 4, 6, 8, 10])
    
    # Customize tick appearance
    #ax_cbar.tick_params(color=COLOR_AXES, rotation=90)

    
    # TODO fix alignment here: when doing it as below, the colorbar is not 
    ax2 = fig.add_subplot(gs[1])
    binsize=0.2
    bins = np.arange(0,10+binsize,binsize)
    num_colors = len(bins)
    colors = [custom_map(i / (num_colors - 1)) for i in range(num_colors)]
    Y,X = np.histogram(data.flatten(), bins=bins)
    ax2.bar(X[:-1],Y, color=colors, width=binsize, align="edge", log=True, rasterized=True, zorder=2)
    ax2.set_xlabel("SoC [MWh]")
    ax2.set_ylabel("SoC Occurences")
    ax2.tick_params(axis='y', which='both', left=True)  # Show both major and minor ticks on the left
    ax2.tick_params(axis='y', which='major', right=False, top=False, bottom=False)  # Hide major ticks on other sides
    ax2.tick_params(axis='y', which='minor', right=False, top=False, bottom=False)  # Hide minor ticks on other sides
    ax2.tick_params(axis='x', which='both', top=False, bottom=True, reset=True)

    ax2.spines["left"].set_color(COLOR_AXES)
    ax2.spines["bottom"].set_color(COLOR_AXES)
    ax2.spines["top"].set_color(COLOR_AXES)
    ax2.spines["right"].set_color(COLOR_AXES)
    ax2.tick_params(axis="both", which="both", color=COLOR_AXES)

    ax2.xaxis.set_minor_locator(AutoMinorLocator())

    ax2.grid(axis='y', which='major', alpha=0.5, zorder=0)


    return fig


def _heatmap_data_from_pandas(df, column, interval_minutes):
    """
    Get day/hour matrix from DataFrame
    """

    data_df = df.copy()
    timezone = data_df.index.tz
    # TODO why does this not make it work with pivot without aggfunc?
    # df.drop_duplicates(subset='Timestamp', keep='first', inplace=True)
    data_df["date_new"] = df.index.date
    data_df["time_new"] = df.index.time #df["time"].dt.time
    # data = df.pivot(index="to_time", columns="to_date", values='A+')
    # mysum = lambda x: x.sum(skipna=False)
    mysum = lambda x: x.iloc[0]
    data = data_df.pivot_table(
        index="time_new", columns="date_new", values=column, aggfunc=mysum, dropna=False
    )

    #display("data_df.pivot_table:", data)
    #invalid_entries = data[data.isna()]

    # Print these entries along with their indices and columns
    #print("Entries not between 0 and 10.0:")
    #display(invalid_entries)
    #print(data.keys())
    #display(data[data["date_new"] == "2021-10-31"])

    

    daterange = data.columns.astype("datetime64[ns]").tz_localize(timezone)
    # # daterange.freq = daterange.inferred_freq
    # daterange = daterange.union(pd.date_range(daterange[-1] + daterange.freq, periods=1, freq=daterange.freq))
    # daterange = pd.date_range(start=daterange.min(), end=daterange.max() + dt.timedelta(days=1), tz=config.tz_local)

    # timerange = data.index
    # timerange = timerange.union(pd.Index([dt.datetime.time(23, 59, 59)]))
    # timerange = pd.to_datetime(timerange)  # .astype('datetime64[ns]')
    # timerange = pd.Series(timerange)
    # timerange = timerange.apply(lambda t: dt.datetime.combine(dt.datetime(year=1970, month=1, day=1), t))
    timerange = pd.date_range(
        start="1970-01-01T00:00:00",
        end="1970-01-02T00:00:00",
        freq=f"{interval_minutes}min",
        tz=timezone,
    )

    data = data.to_numpy()
    # Discard the last day, since daterange needs to extend one day later
    data = data[:, :-1]

    return data, daterange, timerange


def plot_pcolormesh(ax, daterange, timerange, data, cmap, **kwargs):
    """
    Plot the 2D demand profile
    Take a numpy matrix and indices and make a figure with heatmap and sum/avg
    """
    datacopy = data.copy()
    #interpolate nan entries
    #data = data.interpolate(method="time", limit=1)
    data = np.apply_along_axis(
        lambda col: np.interp(
            np.arange(len(col)), 
            np.where(~np.isnan(col))[0],  # Indices of valid values
            col[~np.isnan(col)]          # Valid values
        ) if np.any(~np.isnan(col)) else col,  # Avoid empty slice
        axis=0, 
        arr=data
    )

    # differences = np.argwhere(datacopy != data)
    # for index in differences:
    #     i, j = index
    #     print(f"Index: ({i}, {j}), Original: {datacopy[i, j]}, Interpolated: {data[i, j]}")
        
    def _forward(x):
        return np.sqrt(x)
    def _inverse(x):
        return x**2
    norm = matplotlib.colors.FuncNorm((_forward, _inverse), vmin=0, vmax=10)
    mesh = ax.pcolormesh(daterange, timerange, data, cmap=cmap, rasterized=True, norm=None, **kwargs)
    ax.set_xlim(daterange[0], daterange[-1])
    ax.invert_yaxis()

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_minor_locator(mdates.MonthLocator())

    # Use '%-H' for linux, '%#H' for windows to remove leading zero
    ax.yaxis.set_major_formatter(mdates.DateFormatter("%H"))
    ax.yaxis.set_major_locator(mdates.AutoDateLocator())
    ax.yaxis.set_minor_locator(mdates.HourLocator())

    SHIFT = -0.00875 # Data coordinates
    for label in ax.yaxis.get_majorticklabels():
        label.customShiftValue = SHIFT
        label.set_y = types.MethodType( lambda self, y: matplotlib.text.Text.set_y(self, y-self.customShiftValue ), 
                                        label )
        break


    # Remove last x tick label, to avoid overlapp with histogram
    # TODO does not work in older matplotlib
    # ax_xticks = ax.get_xticks()
    # ax_xticklabels = ax.get_xticklabels()
    # ax_xticklabels[-1] = ""
    # ax.set_xticks(ax_xticks)
    # ax.set_xticklabels(ax_xticklabels)

    ax.set_xlabel("Date")
    ax.set_ylabel("Hour")

    ax.spines["left"].set_color(COLOR_AXES)
    ax.spines["bottom"].set_color(COLOR_AXES)
    ax.tick_params(axis="both", which="both", color=COLOR_AXES)
    for pos in ["top", "right"]:
        ax.spines[pos].set_visible(False)

    return mesh


def _plot_hists(
    daterange,
    timerange,
    data,
    exec_data,
    ax_histx,
    ax_histy,
    interval_minutes,
    histx_label=None,
    histy_label=None,
    minimal=False,
):
    # Daily sum
    daily_demand = exec_data["summed_vol"].values[:]
    daily_max_draw = exec_data["max_vol"].values[:]

    
    twinx = ax_histx.twinx()
    twinx.set_ylabel("Daily Peak Traded\nVolume [MWh]", labelpad=5)
    twinx.scatter(
        daterange,#[-1] + dt.timedelta(hours=12),
        daily_max_draw,
        color="black",
        s=1,
        linewidths=0,
    )
    twinx.set_ylim(0, None)

    for pos in ["top", "left", "bottom"]:
        twinx.spines[pos].set_visible(False)
    twinx.spines["right"].set_color(COLOR_AXES)
    # Rotate in case they are long
    twinx.tick_params(color=COLOR_AXES, rotation=90)
    skip=True
    for tick in twinx.get_yticklabels():
        if skip:
            skip=False
            continue
        tick.set_verticalalignment('center')
    # TODO this is deprecated but currently the only way to set alignment
    # TODO does not work in older mpl
    # twinx.set_yticks(twinx.get_yticks())
    # twinx.set_yticklabels(twinx.get_yticklabels(), rotation=90, va='center')

    ax_histx.fill_between(
        daterange,#[:-1] + dt.timedelta(hours=12),
        daily_demand,
        facecolor=COLOR_FACE,
        alpha=0.5,
    )
    ax_histx.set_xlim(daterange[0], daterange[-1])
    # Need to set the max here as welll, else when removing the lower tick (below) the limits get extended, since the ticks have not been renderd yet.
    ax_histx.set_ylim(min(0, daily_demand.min()), daily_demand.max())

    ax_histx.set_ylabel(histx_label)

    SHIFT = -45 # Data coordinates
    for label in ax_histx.yaxis.get_majorticklabels():
        label.customShiftValue = SHIFT
        label.set_y = types.MethodType( lambda self, y: matplotlib.text.Text.set_y(self, y-self.customShiftValue ), 
                                        label )
        break


    # yticks = ax_histy.yaxis.get_major_ticks()
    # yticks[0].set_visible(False)
    # Remove fist label because it may overlapp with heat map
    # TODO does not work in older mpl
    # ax_yticks = ax_histx.get_yticks()
    # ax_yticklabels = ax_histx.get_yticklabels()
    # ax_yticklabels[0] = ""
    # ax_histx.set_yticks(ax_yticks)
    # ax_histx.set_yticklabels(ax_yticklabels)

    # Mean profile
    histy_values = np.nanmean(data, axis=1)
    histy_values = np.append(histy_values, histy_values[0])
    ax_histy.fill_betweenx(
        timerange[:],# + dt.timedelta(minutes=interval_minutes) / 2,
        histy_values,
        facecolor=COLOR_FACE,
        alpha=0.5,
    )

    ax_histy.axes.yaxis.set_ticklabels([])
    # If demand is larger than zero, alsways show from zero, else show from negative demand on
    ax_histy.set_xlim(min(0, np.nanmean(data, axis=1).min()), None)
    ax_histy.set_ylim(timerange[0], timerange[-1])
    ax_histy.set_xlabel(histy_label)
    ax_histy.set_xticks([0,5,10])
    ax_histy.set_xticklabels(["0","5","10"])
    ax_histy.invert_yaxis()  # This has to be after setting lims

    # Hide the ticks and labels
    ax_histx.get_xaxis().set_visible(False)
    ax_histy.get_yaxis().set_visible(False)
    # Hide axes frame lines
    for pos in ["top", "right", "bottom"]:
        ax_histx.spines[pos].set_visible(False)
    for pos in ["top", "right", "left"]:
        ax_histy.spines[pos].set_visible(False)
    ax_histx.spines["left"].set_color(COLOR_AXES)
    ax_histx.tick_params(color=COLOR_AXES)
    ax_histy.spines["bottom"].set_color(COLOR_AXES)
    ax_histy.tick_params(color=COLOR_AXES)