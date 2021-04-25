#!/usr/bin/python

#
# This Python script is used to monitor the status of a garage door and
# report open and close events to a smartphone via slack IOT events.
#
# A Raspberry Pi model 3 or 3+ and a HC-SR05 ultrasonic distance sensor and a
# handful of parts are required.
#

# Import required standard libraries.
from __future__ import print_function
import argparse
import math
import os
import RPi.GPIO as GPIO
import time

# Import required libraries.
import journal
import sensor
import slack

# Define the Raspberry Pi GPIO pins for the sensor and LED.
GPIO_TRIGGER = 25
GPIO_ECHO = 24
GPIO_STATUS_LED = 21

# Define the loggers and log files that will be used to
# record activitiesand when the program has started. A separate
# log is usedto make it easy to see how often the program is
# restarteddue to fatal errors.
GDOOR_ACTIVITY_LOGGER = "activity"
GDOOR_STARTUP_LOGGER = "startup"
GDOOR_ACTIVITY_LOG_FILE = "gdoor-activity.log"
GDOOR_STARTUP_LOG_FILE = "gdoor-startup.log"

# Define the door states.
DOOR_OPEN = "open"
DOOR_CLOSED = "closed"

# Define the messages that will be sent via Slack.
DOOR_OPENED_MESSAGE = "Garage door just opened!"
DOOR_CLOSED_MESSAGE = "Garage door just closed!"
DOOR_OPEN_WARNING_MESSAGE = "Garage door has been open more than {} minutes"

# If SLACK_DEBUG is set to True messages will not be sent to slack.
SLACK_DEBUG = False

# Slack message successfully sent
SLACK_SUCCESS = 200

def get_average_measurement(distance_sensor,
                            num_measurements,
                            delay,
                            door_log,
                            ):
    """
    Collect a set of measurements and return the average measurement.
    """

    measurement = 0.0
    for n in range(num_measurements):

        distance_measurement, echo_counter = distance_sensor.get_measurement()
        measurement += distance_measurement

        logmsg = "Measurement: {} Sensor measurement: {} Echo counter: {}".format(n, distance_measurement, echo_counter)
        door_log.debug(logmsg)

        time.sleep(delay)

    average_measurement = measurement / num_measurements
    return average_measurement


def monitor_door(trigger_pin,
                 echo_pin,
                 led_status_pin,
                 measurements,
                 time_between_indiv_measurements,
                 time_between_avg_measurements,
                 open_threshold,
                 warning_threshold,
                 door_log,
                 ):

    """
    Use the sensor to monitor the status of the door and
    send slack messages when the door state changes. Also
    report via slack if the door is opened a prolonged period of time.
    """

    # Record the start of execution.
    door_log.information("Door Monitoring Started")

    # Setup for sending slack messages
    slack_iot = slack.Iot(debug=SLACK_DEBUG)

    # Initialize the utltrasonic distance sensor.
    distance_sensor = sensor.DistanceSensor(trigger_pin,
                                            echo_pin,
                                            led_status_pin,
                                            0.05,
                                            DOOR_OPEN,
                                            DOOR_CLOSED,
                                            )

    # Keep track of the number of times measurements are taken
    iteration = -1

    # First time through assume door is closed.
    door_previous_status = DOOR_CLOSED
    door_status = DOOR_CLOSED
    last_warning = 0

    while True:

        iteration += 1

        door_log.debug("------- Entering iteration {:,} -------".format(iteration))
        door_log.information("Checking door status ({:,})".format(iteration))

        # Take the specified number of measurements and calculate the average.

        elapsed = get_average_measurement(distance_sensor,
                                          measurements,
                                          time_between_indiv_measurements,
                                          door_log,
                                          )

        door_log.debug("{:,} Average measurement: {}".format(iteration, elapsed))

        # Calculate the distance in centimeters
        distance = distance_sensor.calculate_distance(elapsed)

        door_log.debug("{:,} Distance: {:5.1f} cm".format(iteration, distance))

        # Determine what the current state of the door is by
        # comparing the distance to the number of centimeters above the
        # door is considered open

        if distance < open_threshold:
            door_status = DOOR_OPEN
        else:
            door_status = DOOR_CLOSED

        door_log.information("{:,} Door is currently {}".format(iteration, door_status))

        # Check to see if the state of the door has changed.
        if door_status != door_previous_status:

            # The state of the door has changed.
            # Determine what happened.

            door_log.information("{:,} Door State Change: New Distance: {:5.1f}".format(iteration, distance))

            if door_status == DOOR_OPEN:

                # Log that the door has opened; set the LED to
                # indicate that the door is open; send a message
                # via slack saying the door is open.

                door_previous_status = DOOR_OPEN
                door_log.information(DOOR_OPENED_MESSAGE)
                distance_sensor.set_door_status_led(DOOR_OPEN)
                # Don't send a slack message the first time through
                if iteration > 0:
                    slack_iot.post_message(DOOR_OPENED_MESSAGE)
                    if slack_iot.status_code != SLACK_SUCCESS:
                        door_log.information("Unable to send slack garage door Opened notification")

                # Record the time that door was opened.
                opened_time = time.time()

            else:
                # Log that the door has closed; set the LED to
                # indicate that the door is closed; send a message
                # via slack saying the door is closed.

                door_previous_status = DOOR_CLOSED
                door_log.information(DOOR_CLOSED_MESSAGE)
                distance_sensor.set_door_status_led(DOOR_CLOSED)
                # Don't send a slack message the first time through
                if iteration > 0:
                    slack_iot.post_message(DOOR_CLOSED_MESSAGE)
                    if slack_iot.status_code != SLACK_SUCCESS:
                        door_log.information("Unable to send slack garage door Closed notification")

        # If the door is closed, blink the LED briefly.  This blinking
        # is like what happens on smoke detectors and is done to indicate
        # that the sensor and Raspberry Pi are alive and well.
        if door_status == DOOR_CLOSED:
            distance_sensor.blink_led()

        # If the door is open, calculate how long it's been open, and periodically
        # send slack messages warning that the door has been opened for a prolonged
        # period of time.

        if door_status == DOOR_OPEN:
            elapsed_open_time_mins = (time.time() - opened_time) / 60.0
            door_log.information("{:,} Open door elapsed time is {:06.2f} minutes".format(iteration, elapsed_open_time_mins))
            elapsed_open_time_mins = int(elapsed_open_time_mins)
            #### print("elapsed_open_time_mins {} last_warning {}".format(elapsed_open_time_mins, last_warning))

            # Send the lack message if the door has been opened for a multiple of
            # 'warning_threshold' minutes.

            if ((elapsed_open_time_mins > 0 ) and
                (elapsed_open_time_mins % warning_threshold) == 0):
                #### print("elapsed_open_time {} warning_threshold {}".format(elapsed_open_time_mins, warning_threshold))

                # Make sure only one message is sent per 'warning_threshold' multiple.
                if elapsed_open_time_mins != last_warning:
                    open_warning_message = DOOR_OPEN_WARNING_MESSAGE.format(elapsed_open_time_mins)
                    door_log.warning(open_warning_message)
                    slack_iot.post_message(open_warning_message)
                    last_warning = elapsed_open_time_mins

        # Sleep until time to take the next set of measurements.
        door_log.debug("{:,} Sleeping for {} seconds".format(iteration, time_between_avg_measurements))
        time.sleep(time_between_avg_measurements)
        door_log.debug("{:,} Awoken from sleep".format(iteration))


#
# This is the main processing where the command line arguments are
# parsed and the monitoring function is called.
#

def main():

    program_name = os.path.basename(__file__)
    door_log = journal.Journal(GDOOR_ACTIVITY_LOGGER,
                               GDOOR_ACTIVITY_LOG_FILE,
                               program_name)

    startup_log = journal.Journal(GDOOR_STARTUP_LOGGER,
                                  GDOOR_STARTUP_LOG_FILE,
                                  program_name)

    startup_log.information("Garage door monitor started.")

    parser = argparse.ArgumentParser()
    parser.add_argument("-c",
                        "--checkstatus",
                        type=float,
                        default=1.0,
                        help="delay in minutes between checking door status",
                        )
    parser.add_argument("-i",
                        "--individual",
                        type=float,
                        default=0.5,
                        help="delay in seconds between taking individual measurements",
                        )
    parser.add_argument("-m",
                        "--measurements",
                        type=int,
                        default=3,
                        help="number of measurements for averaging",
                        )
    parser.add_argument("-o",
                        "--open",
                        type=int,
                        default=50,
                        help="number of cm above the door is considered open",
                        )
    parser.add_argument("-w",
                        "--warning",
                        type=int,
                        default=30,
                        help="display warnings when the door is open more than this many minutes",
                        )
    parser.add_argument("-d",
                        "--debug",
                        action='store_true',
                        help="print and log debugging messages",
                        )

    args = parser.parse_args()

    msg = "Each average will use {} measurements.".format(args.measurements)
    door_log.information(msg)

    msg = "There will be {} seconds delay between individual measurements.".format(args.individual)
    door_log.information(msg)

    msg = "There will be {} minutes ({} seconds) delay between checking the door's status.".format(args.checkstatus, args.checkstatus*60)
    door_log.information(msg)

    msg = "Door is considered open if sensor reading is less than {}".format(args.open)
    door_log.information(msg)

    msg = "Warnings will be sent every {} minutes while the door is open".format(args.warning)
    door_log.information(msg)

    # Set whether debug messages are printed and logged based on 
    # what was specified on the command.
    door_log.log_debug = args.debug

    # Convert the time between taking averaged measurements from
    # minutes to seconds.
    checkstatus = 60 * args.checkstatus

    monitor_door(GPIO_TRIGGER,
                 GPIO_ECHO,
                 GPIO_STATUS_LED,
                 args.measurements,
                 args.individual,
                 checkstatus,
                 args.open,
                 args.warning,
                 door_log,
                 )

    door_log.debug("Exiting...")

if __name__ == "__main__":
    main()
