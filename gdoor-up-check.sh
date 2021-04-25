#!/bin/bash
ps -fC python | grep "garage-monitor.py"
if [ $? -eq 0 ]; then
  python /home/pi/Code/garage/journal.py "gdmonitor running" -l "/home/pi/Code/garage/gdoor-up.log" -i
else
  python /home/pi/Code/garage/journal.py "gdmonitor not running reboot required" -l "/home/pi/Code/garage/gdoor-up.log" -c
  echo "not running"
  sudo /sbin/reboot
fi

