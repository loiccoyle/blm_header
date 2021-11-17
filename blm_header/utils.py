from collections import defaultdict
from datetime import datetime
from typing import Union

import numpy as np
import pandas as pd
import pytimber


def get_timber_db(*args, **kwargs):
    """Fetches a pytimber DB insstance."""
    try:
        return pytimber.LoggingDB(*args, **kwargs)
    except (AttributeError, TypeError) as e:
        print(e)


DB = get_timber_db()


def sanitize_t(t: Union[float, str]) -> pd.Timestamp:
    """Sanitizes input epoch or datetime string to pd.Timestamp in 'Europe/Zurich' timezone.

    Args:
        t:
            - int or float: assumes utc time, converts to pd.Timestamp and to
            Europe/Zurich timezone.

            - str: a pd.to_datetime compatible str, converts to pd.Timestamp
            and to 'Europe/Zurich' timezone if not already.

    Returns:
        Timestamp object for the given time.
    """

    if isinstance(t, (float, int)):
        t = pd.to_datetime(t, unit="s", utc=True).tz_convert("Europe/Zurich")
    elif isinstance(t, str):
        t = pd.to_datetime(t)
    elif isinstance(t, datetime):
        t = pd.to_datetime(t, utc=True)
    else:
        raise TypeError(f'Can\'t figure out how to convert "{t}".')
    if t.tz is None:
        t = t.tz_localize("Europe/Zurich")
    elif t.tz.zone != "Europe/Zurich":
        t = t.tz_convert("Europe/Zurich")
    return t


def no_limit_timber_get(variables, t1, t2, **kwargs):
    """Hacky bypass of the timber single query limit."""
    t1 = sanitize_t(t1)
    t2 = sanitize_t(t2)

    if not isinstance(variables, list):
        variables = [variables]

    try:
        out = DB.get(variables, t1, t2, **kwargs)
    except Exception:
        t12 = t1 + (t2 - t1) / 2
        out1 = no_limit_timber_get(variables, t1, t12, **kwargs)
        out2 = no_limit_timber_get(variables, t12, t2, **kwargs)
        out = {}
        for k in variables:
            out[k] = (
                np.hstack([out1[k][0], out2[k][0]]),
                np.vstack([out1[k][1], out2[k][1]]),
            )
    return out


def list_duplicates(seq):
    tally = defaultdict(list)
    for i, item in enumerate(seq):
        tally[item].append(i)
    return ((key, locs) for key, locs in tally.items() if len(locs) > 1)


def chunkify(a, n):
    k, m = divmod(len(a), n)
    return [a[i * k + min(i, m) : (i + 1) * k + min(i + 1, m)] for i in range(n)]
