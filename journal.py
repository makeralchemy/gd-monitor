#!/usr/bin/python

from __future__ import print_function

import logging
from logging.handlers import RotatingFileHandler
from logging import handlers

import argparse
import os
import sys

PREFIX_FORMAT = "%(asctime)s %(levelname)s %(message)s"
DATE_FORMAT = "%a %m/%d/%Y %I:%M:%S %p"
MESSAGE_FORMAT = "{}: {}"


class Journal(object):

    def __init__(self,
                 logger_name,
                 log_file_name,
                 program_name,
                 log_debug=True,
                 log_information=True,
                 log_warning=True,
                 log_error=True,
                 log_critical=True,
                 max_bytes=10000,
                 backup_count=1,
                 ):

        # Save internal variables
        self._logger_name = logger_name
        self._log_file_name = log_file_name
        self._program_name = program_name
        self._max_bytes = max_bytes
        self._backup_count = backup_count

        # Save which types of messages to be sent to the console
        # and logged. These can be changed during execution.
        # Default is everything is printed and logged.

        self.log_debug = log_debug
        self.log_information = log_information
        self.log_warning = log_warning
        self.log_error = log_error
        self.log_critical = log_critical

        # Setup the logging service.

        self._log = logging.getLogger(self._logger_name)
        self._log.setLevel(logging.DEBUG)
        self._format = logging.Formatter(PREFIX_FORMAT, DATE_FORMAT)

        self._ch = logging.StreamHandler(sys.stdout)
        self._ch.setFormatter(self._format)
        self._log.addHandler(self._ch)

        self._fh = handlers.RotatingFileHandler(self._log_file_name,
                                                maxBytes=self._max_bytes,
                                                backupCount=self._backup_count,
                                                )
        self._fh.setFormatter(self._format)
        self._log.addHandler(self._fh)

    def debug(self, message):
        """
        Log a debug message.
        """
        if self.log_debug:
            msg = MESSAGE_FORMAT.format(self._program_name, message)
            self._log.debug(msg)

    def information(self, message):
        """
        Log a information message.
        """
        if self.log_information:
            msg = MESSAGE_FORMAT.format(self._program_name, message)
            self._log.info(msg)

    def warning(self, message):
        """
        Log a warning message.
        """
        if self.log_warning:
            msg = MESSAGE_FORMAT.format(self._program_name, message)
            self._log.warn(msg)

    def error(self, message):
        """
        Log an error message.
        """
        if self.log_error:
            msg = MESSAGE_FORMAT.format(self._program_name, message)
            self._log.error(msg)

    def critical(self, message):
        """
        Log a critical message.
        """
        if self.log_critical:
            msg = MESSAGE_FORMAT.format(self._program_name, message)
            self._log.critical(msg)

def test():

    my_journal = Journal("test", "log-test.log", os.path.basename(__file__))

    print("Log messages with default settings.")

    my_journal.debug("internally speaking, this might be interesting")
    my_journal.information("you might want to know this")
    my_journal.warning("this might be serious")
    my_journal.error("we have a problem Houston")
    my_journal.critical("it's all over")

    my_journal.log_debug = False
    my_journal.log_information = False
    my_journal.log_warning = False
    my_journal.log_error = False
    my_journal.log_critical = False

    print("Log messages with all logging set to False.")

    # None of these should be logged.
    my_journal.debug("internally speaking, this might be interesting")
    my_journal.information("you might want to know this")
    my_journal.warning("this might be serious")
    my_journal.error("we have a problem Houston")
    my_journal.critical("it's all over")

    my_journal.log_debug = True
    my_journal.log_information = True
    my_journal.log_warning = True
    my_journal.log_error = True
    my_journal.log_critical = True

    print("Log messages with all logging set to True.")

    # All of these should be logged.
    my_journal.debug("internally speaking, this might be interesting")
    my_journal.information("you might want to know this")
    my_journal.warning("this might be serious")
    my_journal.error("we have a problem Houston")
    my_journal.critical("it's all over")

def main():
    parser = argparse.ArgumentParser(description="send a message to a log file")
    parser.add_argument("message")
    level_group = parser.add_mutually_exclusive_group()
    level_group.add_argument("-d",
                        "--debug",
                        action='store_true',
                        help="send a debug message to the specified log file",
                        )
    level_group.add_argument("-i",
                        "--info",
                        action='store_true',
                        help="send an information message to the specified log file",
                        )
    level_group.add_argument("-w",
                        "--warn",
                        action='store_true',
                        help="send a warning message to the specified log file",
                        )
    level_group.add_argument("-e",
                        "--error",
                        action='store_true',
                        help="send an error message to the specified log file",
                        )
    level_group.add_argument("-c",
                        "--crit",
                        action='store_true',
                        help="send a critical message to the specified log file",
                        )
    parser.add_argument("-l",
                        "--logfile",
                        required=True,
                        help="send a critical message to the specified log file",
                        )
    parser.add_argument("-t",
                        "--test",
                        action='store_true',
                        help="runs test cases",
                        )

    args = parser.parse_args()

    if args.test:
        test()
    else:
        program_name = os.path.basename(__file__)

        my_journal = Journal("command", args.logfile, program_name)

        if args.debug:
            my_journal.debug(args.message)
        if args.info:
            my_journal.information(args.message)
        if args.warn:
            my_journal.warning(args.message)
        if args.error:
            my_journal.error(args.message)
        if args.crit:
            my_journal.critical(args.message)
       

if __name__ == "__main__":
    main()

