#!/usr/bin/python

# Import required Python libraries
from __future__ import print_function

import RPi.GPIO as GPIO
import time

# Speed of sound in cm/s at temperature
_TEMPERATURE = 20
_SPEED_OF_SOUND = 33100 + (0.6 * _TEMPERATURE)

# Maximum number of tries to get the echo response
_MAX_ECHO_COUNT = 1000

_ECHO_PULSE_LOST_1 = "echo pulse lost 1"
_ECHO_PULSE_LOST_2 = "echo pulse lost 2"
_ECHO_EXCEPTION_MSG = "exception in take_sensor_measurement: re-executing..."


class DistanceSensor(object):

    def __init__(self,
                 trigger_pin,
                 echo_pin,
                 led_status_pin,
                 led_blink_delay,
                 door_open_constant,
                 door_closed_constant,
                 ):

        """
        Configures the GPIO pins used for the sensor and the LED.
        """

        self._trigger_pin = trigger_pin
        self._echo_pin = echo_pin
        self._led_status_pin = led_status_pin
        self._led_blink_delay = led_blink_delay
        self._door_open_constant = door_open_constant

        # set GPIO mode to GPIO references rather than pin numbers
        GPIO.setmode(GPIO.BCM)

        # Set the modes for the pins
        GPIO.setup(self._trigger_pin, GPIO.OUT)      # trigger is output
        GPIO.setup(self._echo_pin, GPIO.IN)          # echo is input
        GPIO.setup(self._led_status_pin, GPIO.OUT)   # led is output

        self._start()

    def turn_led_on(self):

        """
        Turn on the status LED.
        """

        GPIO.output(self._led_status_pin, True)

    def turn_led_off(self):

        """
        Turn off the status LED.
        """

        GPIO.output(self._led_status_pin, False)

    def blink_led(self):

        """
        Blinks the LED on for the specific time and then turns it off.
        """

        self.turn_led_on()
        time.sleep(self._led_blink_delay)
        self.turn_led_off()

    def set_door_status_led(self,
                            door_status,
                            ):

        """
        Turns the LED on when the door is open and off when it's closed.
        """

        if door_status == self._door_open_constant:
            self.turn_led_on()
        else:
            self.turn_led_off()

    def _start(self):

        """
        Initialize the distance sensor.
        """

        # Set trigger to False (Low)
        GPIO.output(self._trigger_pin, False)

        # Allow module to settle
        time.sleep(0.5)

    def stop(self):

        GPIO.cleanup()

    def calculate_distance(self, measurement):
        """
        Calculate the distance from the measurement
        """

        # Distance pulse travelled in that time is time
        # multiplied by the speed of sound (cm/s)
        distance = measurement * _SPEED_OF_SOUND

        # That was the distance there and back so halve the value
        distance = distance / 2

        return distance

    def get_measurement(self):

        """
        Take a single distance measurement.
        """

        # print("entering get_measurement")

        execute_measurement = True

        while execute_measurement:

            try:

                execute_measurement = False

                # print("*** sensor measurement started")

                # Send 10us pulse to trigger
                GPIO.output(self._trigger_pin, True)

                # Wait 10us
                time.sleep(0.00001)

                # Stop pulse
                GPIO.output(self._trigger_pin, False)

                start_time = time.time()

                echo_counter = 1
                while GPIO.input(self._echo_pin) == 0:
                    if echo_counter < _MAX_ECHO_COUNT:
                        start_time = time.time()
                        echo_counter += 1
                    else:
                        raise SystemError(_ECHO_PULSE_LOST_1)

                while GPIO.input(self._echo_pin) == 0:
                    if echo_counter < _MAX_ECHO_COUNT:
                        start_time = time.time()
                        echo_counter += 1
                    else:
                        raise SystemError(_ECHO_PULSE_LOST_2)

                while GPIO.input(self._echo_pin) == 1:
                    stop_time = time.time()

                elapsed_time = stop_time - start_time

                # print("*** sensor measurement ended")

            except Exception as e:
                print(_ECHO_EXCEPTION_MSG)
                print(e)
                execute_measurement = True

        # print("exiting get_measurement")

        return elapsed_time, echo_counter




if __name__ == "__main__":

    dsensor = DistanceSensor(trigger_pin,
                             echo_pin,
                             led_status_pin,
                             led_blink_delay,
                             door_open_constant,
                             door_closed_constant,
                             )

    dmeasurement = dsensor.get_measurement()

    print("Distance is {}".format(dmeasurement))

    dsensor.stop()
