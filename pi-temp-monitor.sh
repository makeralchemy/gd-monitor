#!/bin/bash
cpu=$(</sys/class/thermal/thermal_zone0/temp)
cputemp=$((cpu/1000))
gpu=$(/opt/vc/bin/vcgencmd measure_temp)
gputemp=$(echo $gpu | cut -c 6-7)
shutdown=0
msg="Garage Door Sensor RPi Temperatures CPU: $cputemp'C GPU: $gputemp'C"

if [ $cputemp -ge 80 ]
then
  python /home/pi/Code/garage/journal.py "CPU TOO HOT!" -l "/home/pi/Code/garage/heat.log" -c
  python /home/pi/Code/garage/slack.py "CPU TOO HOT!" -d
  shutdown=1
else
  python /home/pi/Code/garage/journal.py "CPU temperature is OK $cputemp" -l "/home/pi/Code/garage/heat.log" -i
fi

if [ $gputemp -ge 80 ]
then
  python /home/pi/Code/garage/journal.py "GPU TOO HOT!" -l "/home/pi/Code/garage/heat.log" -c
  python /home/pi/Code/garage/slack.py "GPU TOO HOT!" -d
  shutdown=1
else
  python /home/pi/Code/garage/journal.py "GPU temperature is OK $gputemp" -l "/home/pi/Code/garage/heat.log" -i
fi

if [ $shutdown -eq 1 ]
then
  python /home/pi/Code/garage/journal.py "$msg" -l "/home/pi/Code/garage/heat.log" -c
  python /home/pi/Code/garage/slack.py "$msg" -d
  python /home/pi/Code/garage/journal.py "Garage Door Sensor RPi shutting down!" -l "heat.log" -c
  python /home/pi/Code/garage/slack.py "Garage Door Sensor RPi shutting down!" 
  sudo shutdown -h now
fi
