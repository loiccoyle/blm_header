# blm_header

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

To generate the BLM header for '2018-01-01 00:00:00' and write it in '2018-01-01 00:00:00.csv':
```shell
$ blm_header '2018-01-01 00:00:00' -o {t}.csv
```

To generate the BLM header for epoch time 1457964768.0 (2016-03-14 15:12:48+0100) and write it in '2016-03-14 15:12:48+0100.csv' with verbose output:
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
