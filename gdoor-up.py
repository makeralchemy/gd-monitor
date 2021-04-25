#!/usr/bin/python

from __future__ import print_function

import psutil
import sys
from subprocess import Popen

RUNNING = 0
NOT_RUNNING = 1

for process in psutil.process_iter():
  #print(process.cmdline()[0:2])
  if process.cmdline()[0:2] == ['python','garage-monitor.py']:
    sys.exit(RUNNING)

# process not found
sys.exit(NOT_RUNNING)

