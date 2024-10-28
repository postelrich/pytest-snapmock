# pytest Snapshot Library for Monkeypatched Objects

![Pytest Snapshot](https://img.shields.io/badge/python-3.7%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## Overview

This library provides a convenient way to generate snapshots for monkeypatched objects in your tests using `pytest`. Longgone are the days trying to come up with mock lambdas and data.

## Features

- **Snapshot Generation**: Automatically create snapshots of monkeypatched objects.
- **Easy Integration**: Seamlessly integrates with existing `pytest` workflows.
- **Diff Reporting**: Clear reporting on differences between current and expected snapshots.

## Installation

You can install the library via pip (soon):

```bash
pip install pytest-snapmock
```

## Usage

### Basic Example

Let's say you have a function that reads some data from a database and does a transformation.
```python
# sales.py
import pandas as pd

def sales_by_month():
    df = pd.read_sql('select date, total from sales', engine=someengine)
    return df.groupby(df['date'].dt.month)['total'].sum()
```
For a unittest we might not want to be making queries to a database, so we could monkeypatch the call like:
```python
test_sales.py
import pandas as pd

import sales


def test_sales_by_month(monkeypatch):
    monkeypatch.setattr('sales.pd', 'read_sql', lambda *args, **kwargs: pd.DataFrame({'date': [pd.Timestamp('2024-10-01'), ..., pd.Timestamp('2024-12-31')], 'total': [500.0, ..., 100.8]})
    assert sales.sales_by_month() == pd.DataFrame(...)
```
But what if we could just do:
```python
import pandas as pd

import sales


def test_sales_by_month(snapmock):
    snapmock.snapit('sales.pd', 'read_sql')
    assert sales.sales_by_month() == pd.DataFrame(...)
```
and run 
```bash
pytest --snapshot-mocks
________________________________________ ERROR at teardown of test_double_foo _________________________________________
  - Generated snapshot for call #0 to read_sql
=============================================== short test summary info ===============================================
ERROR tests/test_sales.py::test_sales_by_month - Failed:   - Generated snapshot for call #0 to read_sql
============================================= 1 errors in 0.16s =======================================================
```

### Running Tests

To update snapshots after making changes, use the `--snapshot-update` flag:

```bash
pytest --snapshot-mocks
```

To run your tests and generate snapshots, simply execute:

```bash
pytest
```

## Snapshot Management

Snapshots are stored in a `__snapshot__` directory in the same directory as the test and are named based on the test and the name of mocked object. You can easily manage them by deleting or modifying snapshot files directly.

## Contribution

Contributions are welcome! Please fork the repository and submit a pull request. For large changes, please open an issue first to discuss your proposed changes.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

Thanks to the contributors of `pytest`, `pytest-snapshot` and `syrupy` for the inspiration!

