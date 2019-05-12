#!/usr/bin/python

from __future__ import print_function

import argparse
import subprocess
import time


def issue_command(command):
    return subprocess.call(command, shell=True)  


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="run a program on a schedule")
    parser.add_argument("command")
    level_group = parser.add_mutually_exclusive_group(required=True)
    level_group.add_argument("-z",
                        "--hours",
                        action='store_true',
                        help="issue command every n hours",
                        )
    level_group.add_argument("-m",
                        "--minutes",
                        action='store_true',
                        help="issue command every n minutes",
                        )
    level_group.add_argument("-s",
                        "--seconds",
                        action='store_true',
                        help="issue command every n seconds",
                        )
    parser.add_argument("-n",
                        "--number",
                        required=True,
                        type=float,
                        help="number of specified units to wait between commands",
                        )
    args = parser.parse_args()

    units = args.number
    
    if args.hours:
        units = units * 60 * 60
        print("hours={}".format(units))

    if args.minutes:
        units = units * 60 
        print("minutes={}".format(units))

    if args.seconds:
        units = units
        print("seconds={}".format(units))

    success = 0
    try:
        while success == 0:
            print("Issuing command: {}".format(args.command))
            success = issue_command(args.command)
            if success == 0:
                print("sleeping {} seconds".format(units))
                time.sleep(units)

                
    except KeyboardInterrupt:
        print("\nKeyboard Interrupt!")
