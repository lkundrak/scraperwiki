#!/bin/sh
echo "Starting debugging mail server"
# The -u option means that we see the messages on stdout as soon as they have
# been written.  Useful when we redirect to a file.
python -u -m smtpd -n -c DebuggingServer localhost:1025 &
