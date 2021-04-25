#!/bin/bash
python /home/pi/Code/garage/gdoor-up.py
if [ $? -ne 0 ]; then
  python /home/pi/Code/garage/journal.py "gdmonitor not running reboot required" -l "/home/pi/Code/garage/gdoor-up.log" -c
  echo "sudo /sbin/reboot"
else
  python /home/pi/Code/garage/journal.py "gdmonitor running" -l "/home/pi/Code/garage/gdoor-up.log" -i
fi

