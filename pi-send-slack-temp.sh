#!/bin/bash
cpu=$(</sys/class/thermal/thermal_zone0/temp)
gpu=$(/opt/vc/bin/vcgencmd measure_temp)
temp="Garage Door Sensor RPi CPU temp=$((cpu/1000))'C GPU: ${gpu}"
python journal.py "$temp" -l "heat.log" -i
python slack.py "$temp" -d 
