##########################################################################
#
#   MRC FGU Computational Genomics Group
#
#   $Id$
#
#   Copyright (C) 2009 Andreas Heger
#
#   This program is free software; you can redistribute it and/or
#   modify it under the terms of the GNU General Public License
#   as published by the Free Software Foundation; either version 2
#   of the License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
##########################################################################
'''
Experiment.py - record keeping of experiments
=============================================

Module for record keeping of experiments. This module
is imported by most CGAT scripts. It provides convenience
methods for

   * argument parsing
   * record keeping (logging)
   * benchmarking

See :doc:`../scripts/script_template` on how to use this module.

API
---
'''

import re
import sys
import time
import inspect
import os
import optparse
import logging
import collections
import copy
import subprocess
import gzip
import uuid


class DefaultOptions:
    stdlog = sys.stdout
    stdout = sys.stdout
    stderr = sys.stderr

global_starting_time = time.time()
global_options = DefaultOptions()
global_args = None
global_id = uuid.uuid4()
global_benchmark = collections.defaultdict(int)


def openFile(filename, mode="r", create_dir=False):
    '''open file in *filename* with mode *mode*.

    If *create* is set, the directory containing filename
    will be created if it does not exist.

    gzip - compressed files are recognized by the
    suffix ``.gz`` and opened transparently.

    Note that there are differences in the file
    like objects returned, for example in the
    ability to seek.

    returns a file or file-like object.
    '''

    _, ext = os.path.splitext(filename)

    if create_dir:
        dirname = os.path.dirname(filename)
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname)

    if ext.lower() in (".gz", ".z"):
        return gzip.open(filename, mode)
    else:
        return open(filename, mode)


def getHeader():
    """return a header string with command line options and
    timestamp"""
    system, host, release, version, machine = os.uname()
    return "# output generated by %s\n# job started at %s on %s -- %s\n# pid: %i, system: %s %s %s %s" %\
           (" ".join(sys.argv),
            time.asctime(time.localtime(time.time())),
            host,
            global_id,
            os.getpid(),
            system, release, version, machine)


def getParams(options=None):
    """return a string containing script parameters.
    Parameters are all variables that start with "param_".
    """
    result = []
    if options:
        members = options.__dict__
        for k, v in sorted(members.items()):
            result.append("# %-40s: %s" % (k, str(v).encode("string_escape")))
    else:
        vars = inspect.currentframe().f_back.f_locals
        for var in filter(lambda x: re.match("param_", x), vars.keys()):
            result.append("# %-40s: %s" %
                          (var, str(vars[var]).encode("string_escape")))

    if result:
        return "\n".join(result)
    else:
        return "# no parameters."


def getFooter():
    """return a header string with command line options and
    timestamp."""
    return "# job finished in %i seconds at %s -- %s -- %s" %\
           (time.time() - global_starting_time,
            time.asctime(time.localtime(time.time())),
            " ".join(map(lambda x: "%5.2f" % x, os.times()[:4])),
            global_id)


class OptionGroup(optparse.OptionGroup):
    pass


def callbackShortHelp(option, opt, value, parser):
    '''output short help (only command line options).'''
    # clear usage and description
    parser.set_description(None)
    parser.set_usage(None)
    # output help
    parser.print_help()
    # exit
    parser.exit()


class MultiLineFormatter(logging.Formatter):

    '''logfile formatter: add identation for multi-line entries.'''

    def format(self, record):
        s = logging.Formatter.format(self, record)
        if s.startswith("#"):
            prefix = "#"
        else:
            prefix = ""
        if record.message:
            header, footer = s.split(record.message)
            s = prefix + s.replace('\n', '\n%s' % prefix + ' ' * len(header))
        return s


def Start(parser=None,
          argv=sys.argv,
          quiet=False,
          no_parsing=False,
          add_csv_options=False,
          add_mysql_options=False,
          add_psql_options=False,
          add_pipe_options=True,
          add_cluster_options=False,
          add_output_options=False,
          return_parser=False):
    """set up an experiment.

    returns a tuple containing (options, args).

    The options class is extended with a logger module.
    """

    if not parser:
        parser = OptionParser(
            version="%prog version: $Id$")

    global global_options, global_args, global_starting_time

    # save default values given by user
    user_defaults = copy.copy(parser.defaults)

    global_starting_time = time.time()

    group = OptionGroup(parser, "Script timing options")

    group.add_option("--timeit", dest='timeit_file', type="string",
                     help="store timeing information in file [%default].")
    group.add_option("--timeit-name", dest='timeit_name', type="string",
                     help="name in timing file for this class of jobs "
                     "[%default].")
    group.add_option("--timeit-header", dest='timeit_header',
                     action="store_true",
                     help="add header for timing information [%default].")
    parser.add_option_group(group)

    group = OptionGroup(parser, "Common options")

    group.add_option("-v", "--verbose", dest="loglevel", type="int",
                     help="loglevel [%default]. The higher, the more output.")

    group.add_option("-?", dest="short_help", action="callback",
                     callback=callbackShortHelp,
                     help="output short help (command line options only.")

    parser.add_option_group(group)

    if quiet:
        parser.set_defaults(loglevel=0)
    else:
        parser.set_defaults(loglevel=1)

    parser.set_defaults(
        timeit_file=None,
        timeit_name='all',
        timeit_header=None,
    )

    if add_csv_options:
        parser.add_option("--csv-dialect", dest="csv_dialect", type="string",
                          help="csv dialect to use [%default].")

        parser.set_defaults(
            csv_dialect="excel-tab",
            csv_lineterminator="\n",
        )

    if add_psql_options:
        group = OptionGroup(parser, "postgres options")
        group.add_option("-C", "--connection", dest="psql_connection",
                         type="string",
                         help="psql connection string [%default].")
        group.add_option("-U", "--user", dest="user", type="string",
                         help="database user name [%default].")
        parser.set_defaults(psql_connection="fgu202:postgres")
        parser.set_defaults(user="")
        parser.add_option_group(group)

    if add_cluster_options:
        group = OptionGroup(parser, "cluster options")
        group.add_option("--no-cluster", "--local", dest="without_cluster",
                         action="store_true",
                         help="do no use cluster - run locally [%default].")
        group.add_option("--cluster-priority", dest="cluster_priority",
                         type="int",
                         help="set job priority on cluster [%default].")
        group.add_option("--cluster-queue", dest="cluster_queue",
                         type="string",
                         help="set cluster queue [%default].")
        group.add_option("--cluster-num-jobs", dest="cluster_num_jobs",
                         type="int",
                         help="number of jobs to submit to the queue execute "
                         "in parallel [%default].")
        group.add_option("--cluster-parallel",
                         dest="cluster_parallel_environment",
                         type="string",
                         help="name of the parallel environment to use "
                         "[%default].")
        group.add_option("--cluster-options", dest="cluster_options",
                         type="string",
                         help="additional options for cluster jobs, passed "
                         "on to queuing system [%default].")

        parser.set_defaults(without_cluster=False,
                            cluster_queue=None,
                            cluster_priority=None,
                            cluster_num_jobs=None,
                            cluster_parallel_environment=None,
                            cluster_options=None)
        parser.add_option_group(group)

    if add_output_options or add_pipe_options:
        group = OptionGroup(parser, "Input/output options")

        if add_output_options:
            group.add_option(
                "-P", "--output-filename-pattern",
                dest="output_filename_pattern", type="string",
                help="OUTPUT filename pattern for various methods "
                "[%default].")

            group.add_option("-F", "--force-output", dest="output_force",
                             action="store_true",
                             help="force over-writing of existing files.")

            parser.set_defaults(output_filename_pattern="%s",
                                output_force=False)

        if add_pipe_options:

            group.add_option("-I", "--stdin", dest="stdin", type="string",
                             help="file to read stdin from [default = stdin].",
                             metavar="FILE")
            group.add_option("-L", "--log", dest="stdlog", type="string",
                             help="file with logging information "
                             "[default = stdout].",
                             metavar="FILE")
            group.add_option("-E", "--error", dest="stderr", type="string",
                             help="file with error information "
                             "[default = stderr].",
                             metavar="FILE")
            group.add_option("-S", "--stdout", dest="stdout", type="string",
                             help="file where output is to go "
                             "[default = stdout].",
                             metavar="FILE")

            parser.set_defaults(stderr=sys.stderr)
            parser.set_defaults(stdout=sys.stdout)
            parser.set_defaults(stdlog=sys.stdout)
            parser.set_defaults(stdin=sys.stdin)

        parser.add_option_group(group)

    if add_mysql_options:
        group = OptionGroup(parser, "MYSQL connection options")
        group.add_option("-H", "--host", dest="host", type="string",
                         help="mysql host [%default].")
        group.add_option("-D", "--database", dest="database", type="string",
                         help="mysql database [%default].")
        group.add_option("-U", "--user", dest="user", type="string",
                         help="mysql username [%default].")
        group.add_option("-P", "--password", dest="password", type="string",
                         help="mysql password [%default].")
        group.add_option("-O", "--port", dest="port", type="int",
                         help="mysql port [%default].")

        parser.set_defaults(host="db",
                            port=3306,
                            user="",
                            password="",
                            database="")
        parser.add_option_group(group)

    # restore user defaults
    parser.defaults.update(user_defaults)

    if return_parser:
        return parser

    if not no_parsing:
        (global_options, global_args) = parser.parse_args(argv[1:])

    if add_pipe_options:
        if global_options.stdout != sys.stdout:
            global_options.stdout = openFile(global_options.stdout, "w")
        if global_options.stderr != sys.stderr:
            if global_options.stderr == "stderr":
                global_options.stderr = global_options.stderr
            else:
                global_options.stderr = openFile(global_options.stderr, "w")
        if global_options.stdlog != sys.stdout:
            global_options.stdlog = openFile(global_options.stdlog, "a")
        if global_options.stdin != sys.stdin:
            global_options.stdin = openFile(global_options.stdin, "r")
    else:
        global_options.stderr = sys.stderr
        global_options.stdout = sys.stdout
        global_options.stdlog = sys.stdout
        global_options.stdin = sys.stdin

    if global_options.loglevel >= 1:
        global_options.stdlog.write(getHeader() + "\n")
        global_options.stdlog.write(getParams(global_options) + "\n")
        global_options.stdlog.flush()

    # configure logging
    # map from 0-10 to logging scale
    # 0: quiet
    # 1: little verbositiy
    # >1: increased verbosity
    if global_options.loglevel == 0:
        lvl = logging.ERROR
    elif global_options.loglevel == 1:
        lvl = logging.INFO
    else:
        lvl = logging.DEBUG

    if global_options.stdout == global_options.stdlog:
        format = '# %(asctime)s %(levelname)s %(message)s'
    else:
        format = '%(asctime)s %(levelname)s %(message)s'

    logging.basicConfig(
        level=lvl,
        format=format,
        stream=global_options.stdlog)

    # set up multi-line logging
    # Note that .handlers is not part of the API, might change
    # Solution is to configure handlers explicitely.
    for handler in logging.getLogger().handlers:
        handler.setFormatter(MultiLineFormatter(format))

    return global_options, global_args


def Stop():
    """stop the experiment."""

    if global_options.loglevel >= 1 and global_benchmark:
        t = time.time() - global_starting_time
        global_options.stdlog.write(
            "######### Time spent in benchmarked functions ###################\n")
        global_options.stdlog.write("# function\tseconds\tpercent\n")
        for key, value in global_benchmark.items():
            global_options.stdlog.write(
                "# %s\t%6i\t%5.2f%%\n" % (key, value, (100.0 * float(value) / t)))
        global_options.stdlog.write(
            "#################################################################\n")

    if global_options.loglevel >= 1:
        global_options.stdlog.write(getFooter() + "\n")

    # close files
    if global_options.stdout != sys.stdout:
        global_options.stdout.close()
    # do not close log, otherwise the following error occurs:
    # Error in sys.exitfunc:
    # Traceback (most recent call last):
    #   File "/net/cpp-group/server/lib/python2.6/atexit.py", line 24, in _run_exitfuncs
    #     func(*targs, **kargs)
    #   File "/net/cpp-group/server/lib/python2.6/logging/__init__.py", line 1472, in shutdown
    #     h.flush()
    #   File "/net/cpp-group/server/lib/python2.6/logging/__init__.py", line 740, in flush
    #     self.stream.flush()
    # ValueError: I/O operation on closed file
    # if global_options.stdlog != sys.stdout: global_options.stdlog.close()
    if global_options.stderr != sys.stderr:
        global_options.stderr.close()

    if global_options.timeit_file:

        outfile = open(global_options.timeit_file, "a")

        if global_options.timeit_header:
            outfile.write("\t".join(("name", "wall", "user", "sys", "cuser", "csys",
                                     "host", "system", "release", "machine",
                                     "start", "end", "path", "cmd")) + "\n")

        csystem, host, release, version, machine = map(str, os.uname())
        uusr, usys, c_usr, c_sys = map(lambda x: "%5.2f" % x, os.times()[:4])
        t_end = time.time()
        c_wall = "%5.2f" % (t_end - global_starting_time)

        if sys.argv[0] == "run.py":
            cmd = global_args[0]
            if len(global_args) > 1:
                cmd += " '" + "' '".join(global_args[1:]) + "'"
        else:
            cmd = sys.argv[0]

        result = "\t".join((global_options.timeit_name,
                            c_wall, uusr, usys, c_usr, c_sys,
                            host, csystem, release, machine,
                            time.asctime(time.localtime(global_starting_time)),
                            time.asctime(time.localtime(t_end)),
                            os.path.abspath(os.getcwd()),
                            cmd)) + "\n"

        outfile.write(result)
        outfile.close()


def benchmark(func):
    """decorator collecting wall clock time spent in decorated method."""

    def wrapper(*arg):
        t1 = time.time()
        res = func(*arg)
        t2 = time.time()
        key = "%s:%i" % (func.func_name, func.func_code.co_firstlineno)
        global_benchmark[key] += t2 - t1
        global_options.stdlog.write(
            '## benchmark: %s completed in %6.4f s\n' % (key, (t2 - t1)))
        global_options.stdlog.flush()
        return res
    return wrapper

# there are differences whether you cache a function or
# an objects method


def cachedmethod(function):
    '''decorator for caching a method.'''
    return Memoize(function)


class Memoize(object):

    def __init__(self, fn):
        self.cache = {}
        self.fn = fn

    def __get__(self, instance, cls=None):
        self.instance = instance
        return self

    def __call__(self, *args):
        if args in self.cache:
            return self.cache[args]
        else:
            object = self.cache[args] = self.fn(self.instance, *args)
            return object


def log(loglevel, message):
    """log message at loglevel."""
    logging.log(loglevel, message)


def info(message):
    '''log information message, see the :mod:`logging` module'''
    logging.info(message)


def warning(message):
    '''log warning message, see the :mod:`logging` module'''
    logging.warning(message)


def warn(message):
    '''log warning message, see the :mod:`logging` module'''
    logging.warning(message)


def debug(message):
    '''log debugging message, see the :mod:`logging` module'''
    logging.debug(message)


def error(message):
    '''log error message, see the :mod:`logging` module'''
    logging.error(message)


def critical(message):
    '''log critical message, see the :mod:`logging` module'''
    logging.critical(message)


def getOutputFile(section):
    '''return filename to write to.'''
    return re.sub("%s", section, global_options.output_filename_pattern)


def openOutputFile(section, mode="w"):
    """open file for writing substituting section in the
    output_pattern (if defined).

    If the filename ends with ".gz", the output is opened
    as a gzip'ed file.
    """

    fn = getOutputFile(section)
    try:
        if fn == "-":
            return global_options.stdout
        else:
            if not global_options.output_force and os.path.exists(fn):
                raise OSError(
                    "file %s already exists, use --force to overwrite existing files." % fn)
            if fn.endswith(".gz"):
                return gzip.open(fn, mode)
            else:
                return open(fn, mode)
    except AttributeError:
        return global_options.stdout


class Counter(object):

    '''a counter class.

    The counter acts both as a dictionary and
    a object permitting attribute access.

    Counts are automatically initialized to 0.

    Instantiate and use like this::

       c = Counter()
       c.input += 1
       c.output += 2
       c["skipped"] += 1

       print str(c)
    '''

    __slots__ = ["_counts"]

    def __init__(self):
        """Store data returned by function."""
        object.__setattr__(self, "_counts", collections.defaultdict(int))

    def __setitem__(self, key, value):
        self._counts[key] = value

    def __getitem__(self, key):
        return self._counts[key]

    def __getattr__(self, name):
        return self._counts[name]

    def __setattr__(self, name, value):
        self._counts[name] = value

    def __str__(self):
        return ", ".join("%s=%i" % x for x in self._counts.iteritems())

    def __iadd__(self, other):
        try:
            for key, val in other.iteritems():
                self._counts[key] += val
        except:
            raise TypeError("unknown type")
        return self

    def iteritems(self):
        return self._counts.iteritems()


def run(cmd):
    '''executed a command line cmd.

    raises OSError if process failed or was terminated.
    '''

    retcode = subprocess.call(cmd, shell=True)
    if retcode < 0:
        raise OSError("process was terminated by signal %i" % -retcode)
    return retcode
