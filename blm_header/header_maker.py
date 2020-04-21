import re
import time
import logging
import numpy as np
import pandas as pd
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(*args, **kwargs):
        if args:
            return args[0]
        return kwargs.get('iterable', None)


from functools import partial
from collections import OrderedDict
from multiprocessing import Pool
from multiprocessing import cpu_count
from multiprocessing.dummy import Pool as ThreadPool

from .utils import DB
from .utils import sanitize_t
from .utils import no_limit_timber_get


class HeaderMaker:
    def __init__(self,
                 t,
                 look_back='30M',
                 look_forward='30M',
                 t2=None,
                 vec_var='LHC.BLMI:LOSS_RS09',
                 n_jobs=-1,
                 n_threads=512):
        """Makes timber's vector numeric BLM header for a given timestamp. By
        brute forcely determining which column corresponds to which individual
        BLM timber variable. Building the header can be quite slow ~45 mins per
        header...

        Args:
            t (int, float, str):
                - int or float: assumes utc time, converts to pd.Timestamp and
                to Europe/Zurich timezone.

                - str: a pd.to_datetime compatible str, converts to
                pd.Timestamp and to Europe/Zurich timezone, if not already.

            look_back (str, optional): look back amount, pd.Timedelta
                compatible string.
            look_forward (str, optional): look forward amount, pd.Timedelta
                compatible string.
            t2 (int, float, str): same type logic as t, if provided will ignore
                any look_forward/look_back arguments and will use t1 = t,
                t2=t2.
            vec_var (str, optional): blm vector numeric timber variable.
            n_jobs (int, optional): number of jobs with which to do the
                distance matrix calculations.
            n_threads (int, optional): number of threads with which to fetch
                timber data.
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
        self._logger.info(f'Requested time: {self.t}')
        self._logger.info(f'Using data in range: [{self.t1} -> {self.t2}] for '
                          'matching.')

        if n_jobs == -1:
            n_jobs = cpu_count()
        self._n_jobs = n_jobs
        self._n_threads = n_threads

    def fetch_vec(self):
        """Fetches the vector numeric data from timber, and converts it to
        dataframe.

        Returns:
            pd.DataFrame: pd.DataFrame of the vector numeric data with as index
                the timestamp in Europe/Zurich timezone.
        """
        self._logger.info('Fetching vector numeric data.')

        # out = DB.get(self.vec_var, self.t1, self.t2)[self.vec_var]
        out = no_limit_timber_get(self.vec_var, self.t1, self.t2)[self.vec_var]

        timestamps = out[0][:, np.newaxis]
        data = out[1]
        if data.size == 0:
            raise ValueError('No vectornumeric data in time range '
                             f'[{self.t1} -> {self.t2}].')
        df = pd.DataFrame(np.hstack([data, timestamps]))
        df.iloc[:, -1] = pd.to_datetime(df.iloc[:, -1], unit='s', utc=True)\
            .dt.tz_convert('Europe/Zurich')
        df.set_index(df.columns[-1], inplace=True)
        df.index.name = 'timestamp'
        # rounding time to the second because there is slight offset between
        # vector numeric and single blm var.
        df.index = df.index.round('S')

        self._logger.info(f'Vector numeric shape: {df.shape}')
        return df

    def fetch_single(self, BLM_list=None, **kwargs):
        """Fetches the all the individual BLM variable data from timber, and
        stores them in a dict.

        Args:
            BLM_list (list, optional): to only fetch specific blms, provide a
                list or blm names.
            timber_filter (str, optional): filtering when fetching variable
                list from timber, "%" is the wild card.
            reg_filter (str, optional): additional regex filtering.

        Returns:
            dict: dicitonary containing as keys, the blm name and as values,
                pd.Series of the data.
        """
        self._logger.info('Fetching individual BLM data.')

        if BLM_list is None:
            BLM_list = self._fetch_blm_var_list(**kwargs)

        if self._n_threads > 1:
            self._logger.debug(f'Using {self._n_threads} threads.')
            with ThreadPool(self._n_threads) as p:
                out = list(tqdm(p.imap(lambda x: DB.get(x, self.t1, self.t2),
                                       BLM_list,
                                       # chunksize=len(BLM_list) // self._n_threads),
                                       ),
                                total=len(BLM_list),
                                desc='Fetching BLM data'))
            # Merges list of dicts
            out = {k: v for d in out for k, v in d.items()}
        else:
            out = DB.get(BLM_list, self.t1, self.t2)

        blm_data = OrderedDict()
        for blm, time_data in out.items():
            if time_data[0].size > 0:
                blm_data[blm.split(':')[0]] = self._clean_get(time_data)
            else:
                self._logger.debug(f'Timber variable {blm} has no data.')

        self._logger.info(f'Number of individual BLMs: {len(blm_data)}')
        return blm_data

    @staticmethod
    def _fetch_blm_var_list(timber_filter='BLM%:LOSS_RS09',
                            reg_filter=None):
                            # reg_filter='BLM.[IL]'):
        """Gets a list of all the BLM, respecting the filtering, from timber.

        Args:
            timber_filter (str, optional): filtering when fetching from timber,
                "%" is the wild card.
            reg_filter (str, optional): additional regex filtering.

        Returns:
            list: list of str containing the timber variables respecting the
                filtering.
        """
        out = DB.search(timber_filter)
        if reg_filter is not None:
            out = [blm for blm in out if re.search(reg_filter, blm)]

        if not out:
            raise ValueError('No timber BLM variables passed the filters.')

        return out

    def make_header(self, vec_data=None, single_data=None, **kwargs):
        """Makes the header. Note, this takes a long time... and there is not guarantee
        that the header is correct.

        Args:
            vec_data (pd.DataFrame): pd.DataFrame containing the vectornumeric
                data. If None will fetch the vectornumeric data.
            single_data (dict): dictionary containing the individual BLM data.
                If None will fetch individual BLM data.
            **kwargs: blm filtering, see self.fetch_single.

        Returns:
            list: the header, a list of blm names.
        """
        if vec_data is None:
            vec_data = self.fetch_vec()
        if single_data is None:
            single_data = self.fetch_single(**kwargs)

        d_mat = self.calc_distance_matrix(vec_data, single_data)
        return self._distance_matrix_to_header(d_mat)

    def calc_distance_matrix(self, vec_data, single_data):
        """Constructs the distance matrix between the vectonumeric data and the
        individual BLM variables.

        Args:
            vec_data (pd.DataFrame): pd.DataFrame containing the vectornumeric
                data. If None will fetch the vectornumeric data.
            single_data (dict): dictionary containing the individual BLM data.
                If None will fetch individual BLM data.

        Returns:
            pd.DataFrame: as index the columns of the vector numeric data, as
                columns the blm names and contains the "distance" between each.
        """
        self._logger.info('Constructing distance matrix. This will take a while...')
        start_t = time.time()
        # calculate the distance matrix
        col_diff = partial(self._single_column_diff, single_data=single_data)
        self._logger.debug(f"Using {self._n_jobs} jobs.")
        with Pool(self._n_jobs) as p:
            res = list(tqdm(p.imap(col_diff,
                                   (c for _, c in vec_data.iteritems()),
                                   # chunksize=vec_data.shape[1] // self._n_jobs),
                                   ),
                            total=vec_data.shape[1],
                            desc='Constructing distance matrix'))

        self._logger.info(f'Time elapsed: {time.time() - start_t}')
        return pd.DataFrame(res)

    @staticmethod
    def _clean_get(time_data):
        """Converts a tuple of (time, blm_data), typically coming from a pytimber
        db.get() call, to a pd.Series.

        Args:
            time_data (tuple): tuple of unix timestamps array and blm data
                array.

        Returns:
            pd.Series: pd.Series with the timestamp converted to pd.Timestamp,
                in Europe/Zurich timezone, with the data array as data.
        """
        series = pd.Series(data=time_data[1], index=time_data[0])
        series.index = pd.to_datetime(series.index, unit='s', utc=True)\
            .tz_convert('Europe/Zurich')
        # rounding time to the second because there is slight offset between
        # vector numeric and single blm var.
        series.index = series.index.round('S')
        series.index.name = 'timestamp'
        return series

    @staticmethod
    def _single_column_diff(series, single_data):
        '''Runs the diff of one of the vector numeric columns on each of the
        individual blm data.

        Args:
            series (pd.Series): column of the vector numeric dataframe.
            single_data (dict): dict of the individual blm data.

        Returns:
            dict: dictionary with the blm name as keys and the result of the
                diff as values.
        '''
        return {b: (series - s).abs().mean() for b, s in single_data.items()}

    @staticmethod
    def _distance_matrix_to_header(distance_matrix):
        """Converts a distance matrix to a header.

        Args:
            distance_matrix (pd.DataFrame): as index the columns of the vector
                numeric data, as columns the blm names and contains the "distance"
                between each.

        Returns:
            list: the header, a list of blm names.
        """
        return distance_matrix.idxmin(axis=1).tolist()

