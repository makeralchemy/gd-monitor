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
import requests
import RPi.GPIO as GPIO
import time

# Import required libraries.
import gd_closer_credentials
import journal
import sensor
import slack

# Define the Raspberry Pi GPIO pins for the sensor and LED.
GPIO_TRIGGER = 25
GPIO_ECHO = 24
GPIO_STATUS_LED = 21

# Define the loggers and log files that will be used to
# record activities and when the program has started. A separate
# log is used to make it easy to see how often the program is
# restart due to fatal errors.
GDOOR_ACTIVITY_LOGGER = "activity"
GDOOR_STARTUP_LOGGER = "startup"
GDOOR_ERROR_LOGGER = "errors"
GDOOR_INTERNET_LOGGER = "internet"

GDOOR_ACTIVITY_LOG_FILE = "gdoor-activity.log"
GDOOR_STARTUP_LOG_FILE = "gdoor-startup.log"
GDOOR_ERROR_LOG_FILE = "gdoor-errors.log"
GDOOR_INTERNET_LOG_FILE = "gdoor-internet.log"

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

# Garage door closing device status update commands
GD_CLOSER_CLOSED = "setgdclosed"
GD_CLOSER_OPEN   = "setgdopen"

INTERNET_CHECK_URL = "http://www.google.com"
INTERNET_CHECK_TIMEOUT = 5
INTERNET_CHECK_INTERVAL = 600.0   # Check every 10 minutes


def post_gdoor_status(status):
    """
    Send a HTTPS POST to a Particle Photon microcontroller attached to the Particle Cloud.
    The Photon keeps track of the garage door status and via an app will allow a person to
    close the garage door. The Photon will only allow the garage door to be closed (not opened)
    and to enforce that requires up-to-date status of whether the garage door is currently open
    or closed. A string with the status of the POST request is returned from this function.
    """

    GD_CLOSER_SOURCE = "gdmonitor"  # used to indicate where the POST command came from

    # Define the parameters that will be sent in the POST request
    headers = { 'Authorization' : 'Bearer ' + gd_closer_credentials.GD_CLOSER_BEARER }
    data = { 'arg' : GD_CLOSER_SOURCE }
    url = 'https://api.particle.io/v1/devices/' + gd_closer_credentials.GD_CLOSER_DEVICE + '/' + status

    # Attempt to send the POST request. Failure will not stop the monitor program.
    try:
        response = requests.post(url, headers=headers, data=data)
        return True, "POST to gdcloser with status={} was successful".format(status)
    except requests.exceptions.RequestException as err:
        return False, "POST to gdcloser Request failed with error: {}".format(err)
    except Exception as err:
        return False, "POST to gdcloser failed with an unexpected error: {}".format(err)


def check_internet():
    """ Check to see if the internet is available """
    try:
        response = requests.get(INTERNET_CHECK_URL, timeout=INTERNET_CHECK_TIMEOUT)
        return True
    except (requests.ConnectionError, requests.Timeout) as err:
        return False
    except Exception as err:
        return False


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
                 error_log,
                 internet_log,
                 ):

    """
    Use the sensor to monitor the status of the door and
    send slack messages when the door state changes. Also
    report via slack if the door is opened a prolonged period of time.
    """

    # Record the start of execution.
    door_log.information("Door Monitor Started")

    internet_available = False
    while not internet_available:
        # Check for internet availability
        if check_internet():
            door_log.information("Internet is available")
            internet_available = True
        else:
            door_log.information("Internet is not available, waiting 5 seconds for retry")
            error_log.information("Internet is not available, waiting 5 seconds for retry")
            time.sleep(5)

    # Setup for sending slack messages
    slack_iot = slack.Iot(debug=SLACK_DEBUG)
    # DEBUG: see if there is a timing issue with doing a post too soon after setting slack up
    time.sleep(5)

    # Post a slack message indicating that the monitor has started
    slack_iot.post_message("Garage door monitor started")
    if slack_iot.status_code != SLACK_SUCCESS:
        door_log.information("Unable to send initial slack message, see error log for details")
        error_log.information("Unable to send initial slack message: " + slack_iot.error_message)
    else:
        door_log.information("Successfully sent initial slack message")

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

    # Reset seconds counter for internet check
    internet_check_timer = 0

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
                        error_log.information("Unable to send slack garage door Opened notification" + slack_iot.error_message)

                # Record the time that door was opened.
                opened_time = time.time()

                # Send HTTPS POST with current status to the garage door closer device.
                post_status_success, post_status_message = post_gdoor_status(GD_CLOSER_OPEN)
                if post_status_success:
                   door_log.information(post_status_message)
                else:
                   door_log.information(post_status_message)
                   error_log.information(post_status_message)

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
                        error_log.information("Unable to send slack garage door Closed notification" + slack_iot.error_message)

                # Send HTTPS POST with current status to the garage door closer device.
                post_status_success, post_status_message = post_gdoor_status(GD_CLOSER_CLOSED)
                if post_status_success:
                    door_log.information(post_status_message)
                else:
                    door_log.information(post_status_message)
                    error_log.information(post_status_message)

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

        # every 10 minutes check to see if the internet is up
        if internet_check_timer >= INTERNET_CHECK_INTERVAL:
            if check_internet:
                door_log.information("Internet check PASSED")
                internet_log.information("Internet check PASSED")
                internet_check_timer = 0.0
            else:
                door_log.information("Internet check FAILED")
                error_log.information("Internet check FAILED")
                internet_log.information("Internet check FAILED")
                internet_check_timer = 0.0
        else:
            internet_check_timer += time_between_avg_measurements

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

    error_log = journal.Journal(GDOOR_ERROR_LOGGER,
                                GDOOR_ERROR_LOG_FILE,
                                program_name)

    internet_log = journal.Journal(GDOOR_INTERNET_LOGGER,
                                   GDOOR_INTERNET_LOG_FILE,
                                   program_name)

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

    try:
        monitor_door(GPIO_TRIGGER,
                     GPIO_ECHO,
                     GPIO_STATUS_LED,
                     args.measurements,
                     args.individual,
                     checkstatus,
                     args.open,
                     args.warning,
                     door_log,
                     error_log,
                     internet_log,
                    )
    except Exception as e:
        door_log.information("Exception raised: " + str(e))
        error_log.information("Exception raised: " + str(e))
    finally:
        door_log.information("Exiting...")

if __name__ == "__main__":
    main()
