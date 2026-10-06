import ctypes
import json
import os
import sys
from pathlib import Path


def get_documents_folder():
    """Return the user's actual Windows Documents folder when possible."""
    if sys.platform == "win32":
        try:
            buffer = ctypes.create_unicode_buffer(32768)
            # CSIDL_PERSONAL = 5 (Documents)
            result = ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buffer)
            if result == 0 and buffer.value:
                return Path(buffer.value)
        except Exception:
            pass
    return Path.home() / "Documents"


APP_NAME = "K4B Special Event Logger"
DOCUMENTS_DIR = get_documents_folder()
DATA_DIR = DOCUMENTS_DIR / APP_NAME
SETUPS_DIR = DATA_DIR / "Setups"
LOGS_DIR = DATA_DIR / "Logs"
LEGACY_SESSIONS_DIR = DATA_DIR / "Sessions"
EXPORTS_DIR = DATA_DIR / "Exports"
ARCHIVES_DIR = DATA_DIR / "Archived Logs"
LEGACY_ARCHIVES_DIR = DATA_DIR / "Archived Sessions"
RECOVERY_FILE = DATA_DIR / "_recovery.json"
AUTO_LOG_FILE = LOGS_DIR / "K4B_Auto_Log.json"
UI_PREFS_FILE = DATA_DIR / "_ui_preferences.json"
LEGACY_CURRENT_SETUP_FILE = DATA_DIR / "_current_setup.json"
CURRENT_SETUP_FILE = SETUPS_DIR / "K4B_Auto_Setup.json"
CLEAN_SHUTDOWN_FILE = DATA_DIR / "_clean_shutdown"

for folder in (DATA_DIR, SETUPS_DIR, LOGS_DIR, EXPORTS_DIR, ARCHIVES_DIR):
    folder.mkdir(parents=True, exist_ok=True)


def _migrate_legacy_json_files(source, destination):
    """Move old JSON log files forward without overwriting anything."""
    try:
        if not source.exists() or source.resolve() == destination.resolve():
            return
        for old_file in source.glob("*.json"):
            new_file = destination / old_file.name
            if not new_file.exists():
                old_file.replace(new_file)
        try:
            source.rmdir()
        except OSError:
            pass
    except OSError:
        pass


def _migrate_legacy_archive_folders(source, destination):
    """Move old archive subfolders forward without overwriting anything."""
    try:
        if not source.exists() or source.resolve() == destination.resolve():
            return
        for old_item in source.iterdir():
            target = destination / old_item.name
            if not target.exists():
                old_item.replace(target)
        try:
            source.rmdir()
        except OSError:
            pass
    except OSError:
        pass


_migrate_legacy_json_files(LEGACY_SESSIONS_DIR, LOGS_DIR)
_migrate_legacy_archive_folders(LEGACY_ARCHIVES_DIR, ARCHIVES_DIR)


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(temp, path)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
