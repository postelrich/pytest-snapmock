# pytest-snapmock

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

### snapit

Take a function like the following that changes based on when it's called:
```python
import datetime

def two_days_from_now():
    return datetime.today() + datetime.timedelta(days=2)
```

To write a unittest, you would have to patch `datetime.today` to return a fixed date:
```python
def test_two_days_from_now(monkeypatch):
    monkeypatch.setattr(mymodule.datetime, 'today', lambda: datetime.date(2024, 10, 31))
    assert two_days_from_now() == datetime.date(2024, 11, 2)
```

Instead, it can be written as:
```python
def test_two_days_from_now(snapmock):
    snapmock.snapit(mymodule.datetime, 'today')
    assert two_days_from_now() == datetime.date(2024, 11, 2)
```

And then generate the snapshot
```bash
pytest --snapshot-mocks
```
Verify the snapshot file
```bash
cat __snapshot__/test_two_days_from_now_mymodule.datetime_today_0.snap
```

And then just run your tests like normal:

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
