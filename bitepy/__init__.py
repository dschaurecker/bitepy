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
import sys

from .simulation import Simulation
from .data import Data
from .results import Results


__all__ = ["Simulation", "Data", "Results", "set_tzdb_path"]

__version__ = version("bitepy")

def set_tzdb_path(path: str) -> None:
    """
    Set the path to the IANA timezone database directory (Windows only).
    
    On Windows, this package requires the IANA timezone database files.
    Download from: https://data.iana.org/time-zones/releases/
    Extract tzdata*.tar.gz and point to the extracted directory.
    
    The directory should contain files like: africa, europe, northamerica, etc.
    
    Args:
        path: Path to the directory containing tzdata files
        
    Example:
        >>> import bite
        >>> bite.set_tzdb_path(r"C:\\Users\\myuser\\tzdata")
        >>> sim = bite.Simulation(...)  # Now timezone operations will work
        
    Note:
        This function must be called BEFORE creating any Simulation objects.
        On macOS/Linux, this function does nothing (system tzdb is used).
    """
    if sys.platform == "win32":
        try:
            from . import _bite
            if hasattr(_bite, 'set_tzdb_path'):
                _bite.set_tzdb_path(path)
            else:
                raise RuntimeError(
                    "set_tzdb_path not available. The package may have been built with "
                    "USE_OS_TZDB=1 which is not supported on Windows. Please rebuild."
                )
        except ImportError as e:
            raise ImportError(f"Could not import _bite module: {e}")
    # On non-Windows platforms, this is a no-op (system tzdb is used)


__doc__ = """
bitepy: A Python Battery Intraday Trading Engine
======

A Python wrapper for the C++ battery CID arbitrage simulation.

Classes:
    Simulation: Core simulation class to run and manage simulations.
    Data: Data class to manage input data for simulations.
    Results: Results class to manage simulation results.

Functions:
    set_tzdb_path: Configure timezone database path (Windows only).
"""