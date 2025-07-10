# Processed Input Data Format

  

This document provides an explanation for the included dummy dataset (`orderbook_2022-01-02.csv.zip`), which is a processed representation of raw limit order data from the EPEX Spot continuous intraday market.

  

The raw data format is specified by EPEX SPOT in their official SFTP documentation. The structure of the original exchange data is detailed in **section 2.4.3 "Intraday Continuous"** of the [EPEX SFTP Specifications Document](https://www.epexspot.com/sites/default/files/download_center_files/SFTP_specifications_2020-07.pdf) (accessed on 2025-07-10). Details on how we preprocess the exchange's data can be read in the Python source code of our [Data](../bitepy/data.py) class. Change messages are transformed into new orders with expiration times, and iceberg orders are omitted, as their depth and effect is not possible to model in backtesting.

  

## File Format

  

The data is provided in zipped comma-separated value files (`.csv.zip`) . Files are separated into days and each day contains orders that were submitted (for any product) to the exchange on this day (in UTC time).  The rows are sorted by the transaction, i.e., submission time of the orders (in UTC time). Files are named with the date trailing in the format `year-month-day`, e.g., for February 2 of 2022:

  
**Filename:**  `orderbook_2022-01-02.csv.zip`

  

## Data Dictionary

  

The following table describes the columns present in the `orderbook_2022-01-02.csv.zip` file.

  

| Column Name | Data Type | Description | Notes |

| :--- | :--- | :--- | :--- |

|  *(unnamed)*  |  `Integer`  | A unique identifier. | Corresponds to the `ID` field in the EPEX specification |

|  `initial`  |  `Integer`  | A unique identifier for the order. | Corresponds to the `initialID` field in the EPEX specification. |

|  `side`  |  `String`  | The side of the order book. | Can be `BUY` or `SELL`. |

|  `start`  |  `UTC Timestamp`  | The start of the delivery period for the order. | Formatted as `YYYY-MM-DDTHH:MM:SSZ`. |

|  `transaction`  |  `UTC Timestamp`  | The exact timestamp when the order was submitted (transacted). | Formatted as `YYYY-MM-DDTHH:MM:SS.sssZ`. |

|  `validity`  |  `UTC Timestamp`  | A timestamp indicating the expiration of the order. | In the sample data, some fields are empty, which signifies no expiry. Formatted as `YYYY-MM-DDTHH:MM:SS.sssZ`. |

|  `price`  |  `Float`  | The price of the order in EUR/MWh. | Negative prices are possible in electricity markets. |

|  `quantity`  |  `Float`  | The volume of the order in MWh, in increments of the minimum order volume of 0.1 MWh. | Represents the amount of electricity being bought or sold; the value is always positive. |

  

### Example Row

  

Here is the first row of data from the file with an explanation of each field:

  

```

647017,12059394092,SELL,2022-01-02T09:00:00Z,2022-01-02T00:00:00.002Z,2022-01-02T00:05:12.947Z,42.12,5.4

```

  

- **Unnamed Index**: `647017`

- **Order ID (`initial`)**: `12059394092`

- **Side (`side`)**: `SELL`

- **Delivery Start (`start`)**: January 2, 2022, at 09:00:00 UTC

- **Transaction/Submission Time (`transaction`)**: January 2, 2022, at 00:00:00.002 UTC

- **Order Validity (`validity`)**: January 2, 2022, at 00:05:12.947 UTC

- **Price (`price`)**: `42.12` EUR/MWh

- **Quantity (`quantity`)**: `5.4` MWh