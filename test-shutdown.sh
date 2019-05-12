#!/bin/bash

shutdown=1

if [ $shutdown -eq 1 ]
then
  python journal.py "Garage Door Sensor RPi shutting down!" -l "heat.log" -c
  python slack.py "Garage Door Sensor RPi shutting down!" 
  sudo shutdown -h now
fi