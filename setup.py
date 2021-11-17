# -*- coding: utf-8 -*-
from setuptools import setup

packages = ["blm_header"]

package_data = {"": ["*"]}

install_requires = [
    "numpy>=1.21.2,<2.0.0",
    "pandas>=1.0.3,<2.0.0",
    "pytimber>=3.0.0,<4.0.0",
]

extras_require = {"progress": ["tqdm>=4.45.0,<5.0.0"]}

entry_points = {"console_scripts": ["blm_header = blm_header.cli:main"]}

setup_kwargs = {
    "name": "blm-header",
    "version": "1.1.2",
    "description": "Brute force the LHC's BLM headers.",
    "long_description": '# blm_header\n\nBrute force the LHC\'s BLM headers.\n\n# Installation\n```shell\ngit clone https://github.com/loiccoyle/blm_header\ncd blm_header\npip install .\n```\n\n# Dependencies\n* `numpy`\n* `pandas`\n* `pytimber`\n\nOptional:\n* `tqdm` (for progress bars)\n\n\n# Usage\nThis `blm_header` package provides the `HeaderMaker` class along with a command line tool, `blm_header`.\n\n### `blm_header` command line tool\n\nThe `blm_header` command will generate a header for the given timestamp.\n```\n$ blm_header --help\n\nusage: BLM_header [-h] [-t2 T2] [-f LOOK_FORWARD] [-b LOOK_BACK] [-n N_JOBS]\n                  [-t N_THREADS] [-v] [-o OUTPUT]\n                  t\n\nBruteforce the LHC\'s BLM headers.\n\npositional arguments:\n  t                     Time at which to create de header. int or float:\n                        assumes utc time, converts to pd.Timestamp and to\n                        Europe/Zurich timezone. str: a pd.to_datetime\n                        compatible str, assumes utc, converts to pd.Timestamp.\n\noptional arguments:\n  -h, --help            show this help message and exit\n  -t2 T2                Same type logic as "t", if provided will ignore any\n                        "LOOK_FORWARD" or "LOOK_BACK" arguments and use the\n                        provided "t" and "T2" arguments. (default: None)\n  -f LOOK_FORWARD, --look_forward LOOK_FORWARD\n                        Look forward amount, time format string, "1M", "4H",\n                        ... (default: 30M)\n  -b LOOK_BACK, --look_back LOOK_BACK\n                        Look back amount, time format string, "1M", "4H", ...\n                        (default: 30M)\n  -n N_JOBS, --n_jobs N_JOBS\n                        Number of parallel jobs. (default: -1)\n  -t N_THREADS, --n_threads N_THREADS\n                        Number of threads with which to fetch timber data.\n                        (default: 1)\n  -v, --verbose         Verbosity, -v for INFO level, -vv for DEBUG level.\n                        (default: 0)\n  -o OUTPUT, --output OUTPUT\n                        File in which to write the header. The placeholder\n                        "{t}" will be replaced with the requested time.\n\t\t\t\t\t\t(default: stdout)\n```\n##### Some examples:\n\nTo generate the BLM header for \'2018-01-01 00:00:00\' and write it in \'2018_01_01_00_00_00+0100.csv\':\n```shell\n$ blm_header \'2018-01-01 00:00:00\' -o {t}.csv\n```\n\nTo generate the BLM header for epoch time 1457964768.0 (2016-03-14 15:12:48+0100) and write it in \'2016_03_14_15_12_48+0100.csv\' with verbose output:\n```shell\n$ blm_header 1457964768.0 -o {t}.csv -v\n```\n\n### The `HeaderMaker` class:\nFor use in python, this package also provides the `HeaderMaker` class.\n\nThe basic usage is:\n```python\nfrom blm_header import HeaderMaker\n\nhm = HeaderMaker(\'2018-01-01 00:00:00\', look_back=\'0S\', look_forward=\'60M\', n_threads=1)\nheader = hm.make()\n```\n\n# How it works\nFor a given a time range, `blm_header` will fetch the BLM vector numeric data along with the data of the individual BLMs in the timber database. Unfortunately, the single BLM timber entries suffer from sporatic downsampling and as such cannot be compared trivially with the vector numeric data. Leveraging the power of `pandas` for dealing with time indexed data, we can overcome this. A distance matrix is constructed between the columns of the vector numeric data and the individual BLM signals, with the distance metric being: `mean(abs(v - s))`, with `v` being a column of the vector numeric data and `s` the data of a single BLM. Each columns (BLM) of the vector numeric data is then assigned the BLM which minimizes this distance.\n\nNote: Despite the vast majority of the BLMs being correctly assigned, when the requested time falls in a region with no beam, as the matching data is basicaly noise, the header produced can contain duplicate BLM names.\n',
    "author": "Loic Coyle",
    "author_email": "loic.coyle@hotmail.fr",
    "maintainer": None,
    "maintainer_email": None,
    "url": "https://github.com/loiccoyle/blm_header",
    "packages": packages,
    "package_data": package_data,
    "install_requires": install_requires,
    "extras_require": extras_require,
    "entry_points": entry_points,
    "python_requires": ">=3.7,<3.11",
}


setup(**setup_kwargs)
