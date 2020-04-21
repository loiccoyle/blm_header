import sys
import logging
import argparse

from .header_maker import HeaderMaker

def str_or_float(str_float):
    '''Tries to convert string to float.
    '''
    for typ in [float, str]:
        try:
            return typ(str_float)
        except ValueError:
            pass
    raise ValueError(f'Can\'t figure out the type of "{str_float}".')


def file_name_to_file_stream(file_str, time_str):
    if file_str == 'stdout':
        return sys.stdout
    else:
        file_str = file_str.format(t=time_str.strftime('%Y_%m_%d_%H_%M_%S%z'))
        return argparse.FileType('w')(file_str)


def main():
    '''Quick cli interface to run HeaderMaker.
    '''

    parser = argparse.ArgumentParser(prog='BLM_header',
                                     description='Bruteforce the LHC\'s BLM headers.',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('t',
                        type=str_or_float,
                        help=('Time at which to create de header. int or '
                            'float: assumes utc time, converts to '
                            'pd.Timestamp and to Europe/Zurich timezone. '
                            'str: a pd.to_datetime compatible str, assumes '
                            'utc, converts to pd.Timestamp.')
                        )
    parser.add_argument('-t2',
                        help=('Same type logic as "t", if provided will '
                            'ignore any "LOOK_FORWARD" or "LOOK_BACK" '
                            'arguments and use the provided "t" and "T2" '
                            'arguments.'),
                        type=str_or_float)
    parser.add_argument('-f', '--look_forward',
                        help=('Look forward amount, time format string, "1M", '
                              '"4H", ...'),
                        default='30M',
                        type=str)
    parser.add_argument('-b', '--look_back',
                        help=('Look back amount, time format string, "1M", '
                              '"4H", ...'),
                        default='30M',
                        type=str)
    parser.add_argument('-n', '--n_jobs',
                        help='Number of parallel jobs.',
                        default=-1,
                        type=int)
    parser.add_argument('-t', '--n_threads',
                        help='Number of threads with which to fetch timber data.',
                        default=1,
                        type=int)
    parser.add_argument('-v',
                        '--verbose',
                        help="Verbosity, -v for INFO level, -vv for DEBUG level.",
                        action='count',
                        default=0)
    parser.add_argument('-o',
                        '--output',
                        help=("File in which to write the header. The placeholder "
                              "\"{t}\" will be replaced with the requested time."),
                        default='stdout')
    args = parser.parse_args()

    logger = logging.getLogger('blm_header')
    if args.verbose == 1:
        logger.setLevel(logging.INFO)
    elif args.verbose == 2:
        logger.setLevel(logging.DEBUG)

    hm = HeaderMaker(args.t,
                     t2=args.t2,
                     look_back=args.look_back,
                     look_forward=args.look_forward,
                     n_jobs=args.n_jobs,
                     n_threads=args.n_threads)
    header = hm.make_header()

    if len(set(header)) != len(header):
        logger.warning('There are duplicates in the header !')
        for i, blm in enumerate(header):
            b_count = header.count(blm)
            if b_count > 1:
                logger.warning('\t'.join([blm, str(b_count), str(i)]))

    file_name_to_file_stream(args.output, hm.t).write('\n'.join(header))

