#!/bin/bash
echo "Starting debugging mail server"
python -m smtpd -n -c DebuggingServer localhost:1025 &


