import logging
import re
import time
from typing import List, Optional, Tuple, Union

import numpy as np
import pandas as pd

try:
    from tqdm import tqdm
except ImportError:

    def tqdm(*args, **kwargs):
        if args:
            return args[0]
        return kwargs.get("iterable", None)


from collections import OrderedDict
from functools import partial
from itertools import chain
from multiprocessing import Pool, cpu_count
from multiprocessing.dummy import Pool as ThreadPool

from .utils import DB, chunkify, no_limit_timber_get, sanitize_t


class HeaderMaker:
    def __init__(
        self,
        t: Union[float, str],
        look_back: str = "30M",
        look_forward: str = "30M",
        t2: Optional[Union[float, str]] = None,
        vec_var: str = "LHC.BLMI:LOSS_RS09",
        n_jobs: int = -1,
        n_threads: int = 32,
    ):
        """Makes timber's vector numeric BLM header for a given timestamp. By
        brute forcely determining which column corresponds to which individual
        BLM timber variable. Building the header can be quite slow.

        Args:
            t:
                - int or float: assumes utc time, converts to pd.Timestamp and
                to Europe/Zurich timezone.

                - str: a pd.to_datetime compatible str, converts to
                pd.Timestamp and to Europe/Zurich timezone, if not already.

            look_back: look back amount, pd.Timedelta compatible string.
            look_forward: look forward amount, pd.Timedelta compatible string.
            t2: same type logic as t, if provided will ignore any look_forward/look_back
                arguments and will use t1 = t, t2=t2.
            vec_var: blm vector numeric timber variable.
            n_jobs: number of jobs with which to do the distance matrix calculations.
            n_threads: number of threads with which to fetch timber data.
        """
        self._logger = logging.getLogger(__name__)

        self.vec_var = vec_var
        self.t = sanitize_t(t)
        if t2 is not None:
            self.t1 = self.t
            self.t2 = sanitize_t(t2)
        else:
            self._look_back = pd.Timedelta(look_back)
            self._look_forward = pd.Timedelta(look_forward)
            self.t1 = self.t - self._look_back
            self.t2 = self.t + self._look_forward
        self._logger.info("Requested time: %s", self.t)
        self._logger.info(
            "Using data in range: [%s -> %s] for matching.", self.t1, self.t2
        )

        if n_jobs == -1:
            n_jobs = cpu_count()
        self._n_jobs = n_jobs
        self._n_threads = n_threads

    def fetch_vec(self) -> pd.DataFrame:
        """Fetches the vector numeric data from timber, and converts it to dataframe.

        Returns:
            `pd.DataFrame` of the vector numeric data with as index the timestamp
                in Europe/Zurich timezone.
        """
        self._logger.info("Fetching vector numeric data.")

        # out = DB.get(self.vec_var, self.t1, self.t2)[self.vec_var]
        out = no_limit_timber_get(self.vec_var, self.t1, self.t2)[self.vec_var]

        timestamps = out[0][:, np.newaxis]
        data = out[1]
        if data.size == 0:
            raise ValueError(
                "No vectornumeric data in time range [%s -> %s].", self.t1, self.t2
            )
        df = pd.DataFrame(np.hstack([data, timestamps]))
        df.iloc[:, -1] = pd.to_datetime(
            df.iloc[:, -1], unit="s", utc=True
        ).dt.tz_convert("Europe/Zurich")
        df.set_index(df.columns[-1], inplace=True)
        df.index.name = "timestamp"
        # rounding time to the second because there is slight offset between
        # vector numeric and single blm var.
        df.index = df.index.round("S")

        self._logger.info("Vector numeric shape: %s", df.shape)
        return df

    def fetch_single(
        self,
        BLM_list: Optional[List[str]] = None,
        timber_filter: str = "BLM%:LOSS_RS09",
        reg_filter: Optional[str] = None,
    ) -> dict:
        """Fetches the all the individual BLM variable data from timber, and
        stores them in a dict.

        Args:
            BLM_list: to only fetch specific blms, provide a list or blm names.
            timber_filter: filtering when fetching variable list from timber,
                "%" is the wild card.
            reg_filter: additional regex filtering.

        Returns:
            dicitonary containing as keys, the blm name and as values, `pd.Series`
                of the data.
        """
        self._logger.info("Fetching individual BLM data.")

        if BLM_list is None:
            BLM_list = self._fetch_blm_var_list(
                timber_filter=timber_filter, reg_filter=reg_filter
            )

        if self._n_threads > 1:
            self._logger.debug("Using %i threads.", self._n_threads)
            with ThreadPool(self._n_threads) as p:
                out = list(
                    tqdm(
                        p.imap(
                            lambda x: DB.get(x, self.t1, self.t2),
                            BLM_list,
                            # chunksize=len(BLM_list) // self._n_threads),
                        ),
                        total=len(BLM_list),
                        desc="Fetching BLM data",
                    )
                )
            # Merges list of dicts
            out = {k: v for d in out for k, v in d.items()}
        else:
            out = DB.get(BLM_list, self.t1, self.t2)

        blm_data = OrderedDict()
        for blm, time_data in out.items():
            if time_data[0].size > 0:
                blm_data[blm.split(":")[0]] = self._clean_get(time_data)
            else:
                self._logger.debug("Timber variable %s has no data.", blm)

        self._logger.info("Number of individual BLMs: %i", len(blm_data))
        return blm_data

    @staticmethod
    def _fetch_blm_var_list(
        timber_filter: str = "BLM%:LOSS_RS09", reg_filter: Optional[str] = None
    ):
        """Gets a list of all the BLM, respecting the filtering, from timber.

        Args:
            timber_filter: filtering when fetching from timber, "%" is the wild card.
            reg_filter: additional regex filtering.

        Returns:
            List of str containing the timber variables respecting the filtering.
        """
        # reg_filter='BLM.[IL]'):
        out = DB.search(timber_filter)
        if reg_filter is not None:
            out = [blm for blm in out if re.search(reg_filter, blm)]

        if not out:
            raise ValueError("No timber BLM variables passed the filters.")

        return out

    def make_header(
        self,
        vec_data: Optional[pd.DataFrame] = None,
        single_data: Optional[dict] = None,
        **kwargs,
    ) -> List[str]:
        """Makes the header.

        Note: this takes a long time... and there is not guarantee that the header
            is correct.

        Args:
            vec_data: pd.DataFrame containing the vectornumeric data. If None will
                fetch the vectornumeric data.
            single_data: dictionary containing the individual BLM data. If None
                will fetch individual BLM data.
            **kwargs: blm filtering, see self.fetch_single.

        Returns:
            The header, a list of blm names.
        """
        if vec_data is None:
            vec_data = self.fetch_vec()
        if single_data is None:
            single_data = self.fetch_single(**kwargs)

        d_mat = self.calc_distance_matrix(vec_data, single_data)
        return self._distance_matrix_to_header(d_mat)

    def calc_distance_matrix(
        self, vec_data: pd.DataFrame, single_data: dict
    ) -> pd.DataFrame:
        """Constructs the distance matrix between the vectonumeric data and the
        individual BLM variables.

        Args:
            vec_data: pd.DataFrame containing the vectornumeric data. If None will
                fetch the vectornumeric data.
            single_data: dictionary containing the individual BLM data. If None
                will fetch individual BLM data.

        Returns:
            `pd.DataFrame` with as index the columns of the vector numeric data, as
                columns the blm names and contains the "distance" between each.
        """
        self._logger.info("Constructing distance matrix. This will take a while...")
        start_t = time.time()
        # calculate the distance matrix
        col_diff = partial(self._multi_column_diff, single_data=single_data)
        self._logger.debug("Using %i jobs.", self._n_jobs)
        # Split the vec_data into chunks for more efficient multiprocessing
        with Pool(self._n_jobs) as p:
            res = p.imap(
                col_diff,
                enumerate(chunkify([c for _, c in vec_data.iteritems()], self._n_jobs)),
            )
            res = list(chain(*res))

        self._logger.info("Time elapsed: %s s", round(time.time() - start_t))
        return pd.DataFrame(res)

    @staticmethod
    def _clean_get(time_data: tuple) -> pd.Series:
        """Converts a tuple of (time, blm_data), typically coming from a pytimber
        `db.get()` call, to a `pd.Series`.

        Args:
            time_data (tuple): tuple of unix timestamps array and blm data
                array.

        Returns:
            `pd.Series` with the timestamp converted to pd.Timestamp, in Europe/Zurich
                timezone, with the data array as data.
        """
        series = pd.Series(data=time_data[1], index=time_data[0])
        series.index = pd.to_datetime(series.index, unit="s", utc=True).tz_convert(
            "Europe/Zurich"
        )
        # rounding time to the second because there is slight offset between
        # vector numeric and single blm var.
        series.index = series.index.round("S")
        series.index.name = "timestamp"
        return series

    @staticmethod
    def _multi_column_diff(
        index_list_of_series: Tuple[int, list], single_data: dict
    ) -> List[dict]:
        """Run the distance calculation on a chunk of the vec_data. This is run
        in one multiprocessing job.

        Args:
            index_list_of_series: tuple of (progress bar position, list of vec_data columns).
            single_data: dict of the individual blm data.

        Returns:
            A list of dicts.
        """

        def _single_column_diff(series: pd.Series):
            """Runs the diff of one of the vector numeric columns on each of the
            individual blm data.

            Args:
                series: Column of the vector numeric dataframe.

            Returns:
                Dictionary with the blm name as keys and the result of the diff as values.
            """
            return {b: (series - s).abs().mean() for b, s in single_data.items()}

        # i is the position of the progress bar
        # list_of_series if the chunk of vector numeric columns on which ot run
        # the computation
        i, list_of_series = index_list_of_series[0], index_list_of_series[1]
        return [
            _single_column_diff(series)
            for series in tqdm(
                list_of_series,
                position=i,
                desc=f"Computing matrix chunk {i:02}",
                leave=False,
            )
        ]

    @staticmethod
    def _distance_matrix_to_header(distance_matrix: pd.DataFrame) -> pd.DataFrame:
        """Converts a distance matrix to a header.

        Args:
            distance_matrix: as index the columns of the vector numeric data, as
                columns the blm names and contains the "distance" between each.

        Returns:
            The header, a list of blm names.
        """
        return distance_matrix.idxmin(axis=1).tolist()
