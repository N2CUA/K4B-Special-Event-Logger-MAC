K4B Special Event Logger 2.0.4
===============================

Purpose
-------
A simple Generation 2 special-event logger for K4B during Blind Equality Achievement Month, based on the General QSO Logger workflow.

Key behavior
------------
- Compact Station Setup and dedicated Logging screen.
- K4B special-event call plus individual operator call.
- Optional POTA Activation checkbox and POTA Park Reference.
- U.S. POTA setup references accept forms such as 2155, US2155, or US-2155 and normalize to US-2155.
- Optional Park 2 Park field for P2P contacts; common missing-dash entry is normalized automatically.
- Voice reports default to 59; CW/RTTY to 599; reports remain editable.
- Frequency accepts MHz or kHz input (for example 7.225 or 7225).
- Callsign commit validation follows the current logger-family sanity rule.
- Live UTC plus captured/editable QSO timestamp.
- Setup is automatically saved to Setups\K4B_Auto_Setup.json whenever Logging is entered; Save/Load Setup remain available for named reusable profiles.
- Every QSO/change is automatically written to Logs\K4B_Auto_Log.json. A normal close/reopen silently restores the working log even if Save Log was never used.
- A separate recovery snapshot is retained for interrupted/crashed sessions.
- Save/Load Log, edit/delete, sorting and previous-contact history.
- Import ADIF appends QSOs to the current log, allowing K4B logs from multiple operators to be combined.
- POTA MY_SIG_INFO is preserved per QSO during ADIF import/export so combined logs from different parks are not stamped with one setup park.
- Export ADIF writes MY_SIG=POTA / MY_SIG_INFO for activator parks and SIG=POTA / SIG_INFO for P2P contacts.
- No Cabrillo export or contest scoring is included because K4B is a special-event log, not a contest.

POTA terminology
----------------
Parks on the Air calls the park identifier a Park Reference. It is a prefix, a dash, and a number, for example US-0005. U.S. references can contain four or more digits.

Files are stored under:
Documents\K4B Special Event Logger\

Run from Python:
python run_logger.py

No third-party Python packages are required to run the source version.

Windows build
-------------
Double-click BUILD_EXE.bat to create dist\K4B Special Event Logger.exe with PyInstaller.
Then compile INSTALLER.iss in Inno Setup to create the installer.

License: GNU GPL version 3. See LICENSE.txt.

Copyright © 2026 Randy Swart - N2CUA
Developed by Randy Swart with assistance from OpenAI ChatGPT.

Version 2.0.4 refinements
- Stores POTA/non-POTA status per QSO so a single log can safely mix home and park operations.
- Shows the activating POTA park in the QSO table; Park 2 Park remains the other activator's reference.
- ADIF export uses each QSO's stored POTA status rather than the current setup checkbox.
- ADIF import preserves per-QSO POTA status when MY_SIG_INFO is present.
- Moves the POTA Park Reference entry to leave the full label visible with normal padding.

Mac build kit note
------------------
This Mac kit adds RUN_K4B_MAC.command, BUILD_MAC.command, README_MAC.txt, and
SOURCE_SHA256.txt. See README_MAC.txt before running or building on macOS.
