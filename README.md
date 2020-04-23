# blm_header
[![pypi](https://img.shields.io/pypi/v/blm_header)](https://pypi.org/project/blm-header/)

Brute force the LHC's BLM headers.

# Installation
```shell
pip install blm_header
```

# Dependencies
* `numpy`
* `pandas`
* `pytimber`

Optional:
* `tqdm` (for progress bars)


# Usage
This `blm_header` package provides the `HeaderMaker` class along with a command line tool, `blm_header`.

### `blm_header` command line tool

The `blm_header` command will generate a header for the given timestamp.
```
$ blm_header --help

usage: BLM_header [-h] [-t2 T2] [-f LOOK_FORWARD] [-b LOOK_BACK] [-n N_JOBS]
                  [-t N_THREADS] [-v] [-o OUTPUT]
                  t

Bruteforce the LHC's BLM headers.

positional arguments:
  t                     Time at which to create de header. int or float:
                        assumes utc time, converts to pd.Timestamp and to
                        Europe/Zurich timezone. str: a pd.to_datetime
                        compatible str, assumes utc, converts to pd.Timestamp.

optional arguments:
  -h, --help            show this help message and exit
  -t2 T2                Same type logic as "t", if provided will ignore any
                        "LOOK_FORWARD" or "LOOK_BACK" arguments and use the
                        provided "t" and "T2" arguments. (default: None)
  -f LOOK_FORWARD, --look_forward LOOK_FORWARD
                        Look forward amount, time format string, "1M", "4H",
                        ... (default: 30M)
  -b LOOK_BACK, --look_back LOOK_BACK
                        Look back amount, time format string, "1M", "4H", ...
                        (default: 30M)
  -n N_JOBS, --n_jobs N_JOBS
                        Number of parallel jobs. (default: -1)
  -t N_THREADS, --n_threads N_THREADS
                        Number of threads with which to fetch timber data.
                        (default: 1)
  -v, --verbose         Verbosity, -v for INFO level, -vv for DEBUG level.
                        (default: 0)
  -o OUTPUT, --output OUTPUT
                        File in which to write the header. The placeholder
                        "{t}" will be replaced with the requested time.
						(default: stdout)
```
##### Some examples:

To generate the BLM header for '2018-01-01 00:00:00' and write it in '2018_01_01_00_00_00+0100.csv':
```shell
$ blm_header '2018-01-01 00:00:00' -o {t}.csv
```

To generate the BLM header for epoch time 1457964768.0 (2016-03-14 15:12:48+0100) and write it in '2016_03_14_15_12_48+0100.csv' with verbose output:
```shell
$ blm_header 1457964768.0 -o {t}.csv -v
```

### The `HeaderMaker` class:
For use in python, this package also provides the `HeaderMaker` class.

The basic usage is:
```python
from blm_header import HeaderMaker

hm = HeaderMaker('2018-01-01 00:00:00', look_back='0S', look_forward='60M', n_threads=1)
header = hm.make()
```

# How it works
For a given a time range, `blm_header` will fetch the BLM vector numeric data along with the data of the individual BLMs in the timber database. Unfortunately, the single BLM timber entries suffer from sporatic downsampling and as such cannot be compared trivially with the vector numeric data. Leveraging the power of `pandas` for dealing with time indexed data, we can overcome this. A distance matrix is constructed between the columns of the vector numeric data and the individual BLM signals, with the distance metric being: `mean(abs(v - s))`, with `v` being a column of the vector numeric data and `s` the data of a single BLM. Each columns (BLM) of the vector numeric data is then assigned the BLM which minimizes this distance.

Note: Despite the vast majority of the BLMs being correctly assigned, when the requested time falls in a region with no beam, as the matching data is basicaly noise, the header produced can contain duplicate BLM names.
