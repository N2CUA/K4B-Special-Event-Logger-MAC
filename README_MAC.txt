K4B SPECIAL EVENT LOGGER 2.0.4 - MAC BUILD KIT
================================================
Prepared for Jamie's 2014 Intel MacBook Air.

WHAT THIS IS
------------
This is the same K4B Special Event Logger 2.0.4 Python source, packaged with
Mac-specific launch/build helpers. The final Mac application must be built on
macOS. Nothing in this kit installs GitHub or requires a GitHub account.

FIRST: TRY THE SOURCE VERSION
-----------------------------
1. Double-click RUN_K4B_MAC.command.
2. If macOS says Python 3 is missing, install the official Python 3.13 macOS
   installer from python.org and try again.
3. If macOS blocks the .command file because it was downloaded, Control-click
   it and choose Open. Depending on the macOS version, you may instead need
   System Settings/System Preferences > Privacy & Security > Open Anyway.
4. If the K4B setup screen opens, close it normally after a quick look.

THEN: BUILD THE .APP
--------------------
1. Double-click BUILD_MAC.command.
2. The script creates a private Python virtual environment inside this folder.
   It does not replace the Mac's system Python.
3. It installs exactly PyInstaller 6.22.3 from the official PyPI index.
4. It builds an Intel x86_64 application bundle.
5. When finished, look in the dist folder for:

      K4B Special Event Logger.app
      K4B_Special_Event_Logger_v2.0.4_macOS_Intel.zip

The ZIP is the easiest file to send to another Intel Mac.

FIRST LAUNCH OF THE BUILT APP
-----------------------------
This is a personal unsigned build, not an Apple-notarized App Store program.
macOS may refuse the first ordinary double-click. Control-click the app,
choose Open, then confirm that you want to open it. macOS may also ask whether
K4B Special Event Logger may access the Documents folder; allow it if you want
the logger to store its setups/logs/exports there.

DATA LOCATION
-------------
The logger stores its working data under:

  ~/Documents/K4B Special Event Logger/

That folder contains Setups, Logs, Exports, and Archived Logs.

COMPATIBILITY
-------------
- Intended CPU: Intel x86_64 (Jamie's 2014 MacBook Air).
- Python.org's Python 3.13 macOS installer supports macOS 10.13 and later.
- The current PyInstaller used by this kit is 6.22.3.
- If Jamie's Mac is older than macOS 10.13, stop and tell Randy/Sam the exact
  macOS version before installing Python or building.

SECURITY / TRANSPARENCY
-----------------------
- BUILD_MAC.command runs only on the Mac where Jamie launches it.
- It creates an isolated .k4b_mac_build_venv folder locally.
- The only Python package it deliberately downloads is the pinned
  PyInstaller 6.22.3 package and its normal dependencies from pypi.org.
- No GitHub connector, GitHub Actions, or cloud build is involved.
- Original K4B source files are plain text and can be inspected before running.
- SOURCE_SHA256.txt contains SHA-256 hashes of the packaged files.

If anything unexpected appears, close the Terminal window and stop. Nothing in
this package requires entering an Apple ID, GitHub password, or other account
credentials.
