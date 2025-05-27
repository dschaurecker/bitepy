######################################################################
# Copyright (C) 2025 ETH Zurich
# BitePy: A Python Battery Intraday Trading Engine
# Bits to Energy Lab - Chair of Information Management - ETH Zurich
#
# Author: David Schaurecker
#
# Licensed under MIT License, see https://opensource.org/license/mit
######################################################################

from importlib.metadata import version

from .simulation import Simulation
from .data import Data
from .results import Results


__all__ = ["Simulation", "Data", "Results"]

__version__ = version("bitepy")

__doc__ = """
bitepy: A Python Battery Intraday Trading Engine
======

A Python wrapper for the C++ battery CID arbitrage simulation.

Classes:
    Simulation: Core simulation class to run and manage simulations.
    Data: Data class to manage input data for simulations.
    Results: Results class to manage simulation results.
"""