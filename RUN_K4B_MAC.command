#!/bin/bash
set -u
cd "$(dirname "$0")" || exit 1

printf '\nK4B Special Event Logger 2.0.4 - Mac source test\n'
printf '------------------------------------------------\n'

if [ "$(uname -s)" != "Darwin" ]; then
  echo "This launcher is for macOS."
  echo "Press Return to close."
  read -r _
  exit 1
fi

PYTHON=""
if [ -x "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3" ]; then
  PYTHON="/Library/Frameworks/Python.framework/Versions/3.13/bin/python3"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="$(command -v python3)"
fi

if [ -z "$PYTHON" ]; then
  echo "Python 3 was not found."
  echo "Install the official Python 3.13 macOS installer from python.org, then run this again."
  echo "Press Return to close."
  read -r _
  exit 1
fi

if ! "$PYTHON" -c 'import tkinter; import sys; assert sys.version_info >= (3,8)' >/dev/null 2>&1; then
  echo "Python 3 with Tkinter is required."
  echo "The official Python 3.13 installer from python.org includes the needed Tk support."
  echo "Press Return to close."
  read -r _
  exit 1
fi

echo "Using: $($PYTHON --version 2>&1)"
echo "Starting K4B Logger from source..."
"$PYTHON" run_logger.py
STATUS=$?

echo
if [ $STATUS -ne 0 ]; then
  echo "K4B Logger exited with status $STATUS."
else
  echo "K4B Logger closed normally."
fi
echo "Press Return to close."
read -r _
exit $STATUS
