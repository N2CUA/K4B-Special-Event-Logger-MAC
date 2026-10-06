#!/bin/bash
set -u
cd "$(dirname "$0")" || exit 1

APP_NAME="K4B Special Event Logger"
PYINSTALLER_VERSION="6.22.3"
VENV_DIR=".k4b_mac_build_venv"

fail() {
  echo
  echo "BUILD FAILED: $1"
  echo "Press Return to close."
  read -r _
  exit 1
}

printf '\nK4B Special Event Logger 2.0.4 - Intel Mac Build\n'
printf '-------------------------------------------------\n'

[ "$(uname -s)" = "Darwin" ] || fail "This build script must be run on macOS."
ARCH="$(uname -m)"
echo "Mac architecture: $ARCH"
if [ "$ARCH" != "x86_64" ]; then
  echo "WARNING: This kit is intended for Jamie's Intel MacBook Air."
  echo "Current machine is $ARCH. The build will still request an x86_64 target,"
  echo "but an Intel Mac is the preferred build machine for this kit."
fi

PYTHON=""
if [ -x "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3" ]; then
  PYTHON="/Library/Frameworks/Python.framework/Versions/3.13/bin/python3"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="$(command -v python3)"
fi
[ -n "$PYTHON" ] || fail "Python 3 was not found. Install the official Python 3.13 macOS installer from python.org."

"$PYTHON" -c 'import sys; assert sys.version_info >= (3,8)' >/dev/null 2>&1 || fail "Python 3.8 or newer is required."
"$PYTHON" -c 'import tkinter' >/dev/null 2>&1 || fail "Tkinter is missing. The official python.org macOS Python installer includes Tk support."

echo "Using: $($PYTHON --version 2>&1)"

echo
echo "Creating an isolated build environment..."
if [ ! -x "$VENV_DIR/bin/python" ]; then
  "$PYTHON" -m venv "$VENV_DIR" || fail "Could not create the local build environment."
fi
VENV_PY="$VENV_DIR/bin/python"

echo "Installing pinned PyInstaller $PYINSTALLER_VERSION from the official PyPI index..."
"$VENV_PY" -m pip install --disable-pip-version-check --index-url https://pypi.org/simple "pyinstaller==$PYINSTALLER_VERSION" || fail "PyInstaller installation failed."

rm -rf build "dist/$APP_NAME" "$APP_NAME.spec"

echo
echo "Building the Intel macOS application..."
"$VENV_PY" -m PyInstaller \
  --noconfirm \
  --clean \
  --onedir \
  --windowed \
  --target-arch x86_64 \
  --osx-bundle-identifier "com.n2cua.k4bspecialeventlogger" \
  --name "$APP_NAME" \
  --add-data "LICENSE.txt:." \
  run_logger.py || fail "PyInstaller did not complete successfully."

APP_PATH="dist/$APP_NAME.app"
[ -d "$APP_PATH" ] || fail "The expected .app bundle was not created."

echo
echo "Creating a ZIP of the finished .app using macOS ditto..."
/usr/bin/ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "dist/K4B_Special_Event_Logger_v2.0.4_macOS_Intel.zip" || fail "Could not create the final ZIP."

echo
echo "BUILD COMPLETE"
echo "Application: $APP_PATH"
echo "Shareable ZIP: dist/K4B_Special_Event_Logger_v2.0.4_macOS_Intel.zip"
echo
echo "This is an unsigned personal build. On first launch, Jamie may need to"
echo "Control-click the app, choose Open, and confirm. macOS may also ask for"
echo "permission to use the Documents folder."
echo
echo "Press Return to close."
read -r _
