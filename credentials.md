**Credentials should never be stored as constants as code.**

The 'slack.py' module requires credentials for the slack webhook.
Instead of storing the credentials as a constant in the Python code,
the credentials are stored in a file in the same directory as the 
'slack.py' module. 

The default name of the file is 'slack.credentials'.
The default can be overriden by specifying 
`credentials_file="anotherfile.credentials"`
when instantiating an Iot object. 

It's recommended that the file type of .credentials is used to identify
files with credentials and that a line be added to .gitignore to prevent
accidentially pushing the files to github repositories.

The format of the credentials files is a single line containing the
slack webhook credentials.  The format of the credentials is:

XXXXXXXXX/XXXXXXXXX/XXXXXXXXXXXXXXXXXXXXXXXX

When an Iot object is instantiated, it will read in the first line,
validate the length of the credentials, and verify the placement of 
the two slashes before issuing the Post to slack.
