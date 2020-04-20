# blm_header

Brute force the LHC's BLM header.

# Installation
```shell
pip install blm_header
```

# Usage
```
$ blm_header --help

usage: BLM_header [-h] [-t2 T2] [-f LOOK_FORWARD] [-b LOOK_BACK] [-n N_JOBS]
                  [-t N_THREADS] [-v] [-o OUTPUT]
                  t

Bruteforce the LHC's BLM headers.

positional arguments:
  t                     Time at which to create de header. int or float:
                        assumes utc time, converts to pd.Timestamp and to
                        Europe/Zurich timezone.str: a pd.to_datetime
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
                        File in which to write the header. The placeholder the
                        "{t}" placeholder will be replaced with the requested
                        time. (default: stdout)
```
