#!/usr/bin/python
# Module: slack

from __future__ import print_function
import argparse
import os
import requests
import sys

_READ_ONLY = "r"

_URL = "https://hooks.slack.com/services/"
_CREDENTIALS_FILE_NAME = "slack.credentials"
_CREDENTIALS_LENGTH = 44

_CREDENTIALS_SLASH_1 = 9
_CREDENTIALS_SLASH_2 = 19

# Exception messages.
_CRED_ERROR_BAD_LENGTH = "Credentials have incorrect length"
_CRED_ERROR_SLASH_1 = "Credentials not properly formed: first / missing or in wrong place"
_CRED_ERROR_SLASH_2 = "Credentials not properly formed: second / missing or in wrong place"


class Iot(object):
    """
    Verify the credentials file exists, read and validate the credentials,
    and store them for use when 'post_message' is called to send an IOT
    message to Slack.
    """

    def __init__(self,
                 url="https://hooks.slack.com/services/",
                 credentials_file="slack.credentials",
                 debug=False,
                 ):

        self.url = url
        self.credentials_file = credentials_file
        self.debug = debug
        self.status_code = 0

        if os.path.isfile(credentials_file):

            try:
                # Read the credentials from the file.
                with open(credentials_file, _READ_ONLY) as file:
                    self.credentials = file.readline().rstrip()

                # Verify correct formatting of the credentials.

                # Check for correct credentials length.
                if len(self.credentials) != _CREDENTIALS_LENGTH:
                    raise SystemError(_CRED_ERROR_BAD_LENGTH)

                # Ensure the first "/" is in the correct location.
                if self.credentials[_CREDENTIALS_SLASH_1] != "/":
                    raise SystemError(_CRED_ERROR_SLASH_1)

                # Ensure the second "/" is in the correct location.
                if self.credentials[_CREDENTIALS_SLASH_2] != "/":
                    raise SystemError(_CRED_ERROR_SLASH_2)

            except IOError:
                raise IOError("Error reading ()".format(credentials_file))

            # Construct the webhook by catenating the URL and credentials
            self.webhook = self.url + self.credentials

        else:
            raise SystemError("credentials file missing")

    def post_message(self, message):

        """
        Send an IOT message to Slack.
        """

        # In debugging mode, messages are sent to stout rather than slack
        # and the status and reason codes saved simulates success.
        if self.debug:
            print("Slack message: ", message)
            self.status_code = 200

        # Send a message to the slack webhook and save the status and
        # reason codes.
        else:
            try:
                response = requests.post(self.webhook,
                                         json={"text": message},
                                         )
                self.status_code = response.status_code
            except requests.exceptions.RequestException as e:
                print("Failed to send slack message:", e, file=sys.stderr)
                self.status_code = 999

#
# This main function is used for testing this library.
#
if __name__ == "__main__":

    # Get the message from the command line.
    # Determine whether to send a message to Slack or print it.

    parser = argparse.ArgumentParser(description="send an IOT message to slack")
    parser.add_argument("message")
    parser.add_argument("-d",
                        "--debug",
                        action='store_true',
                        help="in debug mode messages are printed and not sent to slack",
                        )
    args = parser.parse_args()

    # Get the slack credentials
    slack_webhook = Iot(debug=args.debug)

    # Send the message to slack
    slack_webhook.post_message(args.message)

    # If failure, print the status code, exit with non-zero return code
    if slack_webhook.status_code != requests.codes.ok:
        print("Failed to send slack message. Status code: {}".format(slack_webhook.status_code))
        sys.exit(1)
