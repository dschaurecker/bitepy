<p align="center" width="100%">
<img src="https://raw.githubusercontent.com/dschaurecker/bitepy/main/docs/assets/bitepy_logo_text.png" width="300">
</p>

## _A Battery Intraday Trading Engine_

[![Version](https://img.shields.io/github/v/tag/dschaurecker/bitepy?label=version&style=flat)](https://github.com/dschaurecker/bitepy/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-red.svg)](https://opensource.org/licenses/MIT)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/bitepy)](https://pypi.org/project/bitepy/)
<!-- [![Tests](https://github.com/dschaurecker/bitepy/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/dschaurecker/bitepy/actions/workflows/release.yml) -->
<!-- [![Docs](https://github.com/dschaurecker/bitepy/actions/workflows/gh-pages.yml/badge.svg?branch=main)](https://github.com/dschaurecker/bitepy/actions/workflows/gh-pages.yml) -->



A Python high-frequency intraday trading engine for simulating the rolling intrinsic strategy on the European market, solved as a dynamic program. See our paper ([Schaurecker et al. (2026)](
https://doi.org/10.1016/j.apenergy.2026.128550)) for details on the method and visualizations of the results.


## Features

- Process your own raw EPEX Spot Market Data to a suitable format
- Define battery and simulation settings
- Adapt the parameters of the dynamic programming optimization
- React to every single LOB update on the exchange
- Run yearly high-frequency trading simulations in minutes/hours
- Return and visualize results and statistics

## Installation

BitePy requires Python 3.9+ to run.
The package is hosted on [PyPI](https://pypi.org/project/bitepy/) and can be easily installed via

```sh
pip install bitepy
```

## Documentation and Tutorial

Our [Documentation](https://dschaurecker.github.io/bitepy/) gives a detailed overview on our package's features and will be updated continuously. We also provide a simple [Tutorial](https://github.com/dschaurecker/bitepy/blob/main/notebooks/package_tutorial.ipynb) in form of a Jupyter Notebook, guiding users through our simulation process.

## Contribution

We are happy about all forms of feedback and would like to hear from you, if you would like to contribute as well, or are interested in the underlying C++ source code of your simulation engine.
If you want to clone and contribute to the repository, first `pip install bitepy` and then clone the repository to have access to the compiled binaries while being able to edit the Python source code.

## License

Licensed under MIT License.
See [License](https://github.com/dschaurecker/bitepy/blob/main/LICENSE) for the full license text.

## Author

[@dschaurecker](https://github.com/dschaurecker)

with pythonic support by [@simon-hirsch](https://github.com/simon-hirsch)
