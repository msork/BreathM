import re
from pathlib import Path
import platform

APP_NAME = "BreathM"
FLATPAK_CEMU_ID = "info.cemu.Cemu"
DISCORD_CLIENT_ID = "1514412498814763088"
PROTOCOL_VERSION = "alpha-0.6"
BOTW_TITLE_IDS = {
    "00050000101c9300": ("Japan", "base"),
    "00050000101c9400": ("US", "base"),
    "00050000101c9500": ("Europe", "base"),
    "0005000e101c9300": ("Japan", "update"),
    "0005000e101c9400": ("US", "update"),
    "0005000e101c9500": ("Europe", "update"),
    "0005000c101c9300": ("Japan", "dlc"),
    "0005000c101c9400": ("US", "dlc"),
    "0005000c101c9500": ("Europe", "dlc"),
}

WUA_TITLE_FOLDER_RE = re.compile(
    rb"(0005000[0ce][0-9a-fA-F]{8})_v([0-9]{1,6})"
)
WUA_SCAN_LIMIT_BYTES = 1024 * 1024 * 512

def get_config_path() -> Path:
    if platform.system() == "Windows":
        return Path.home() / "AppData" / "Roaming" / APP_NAME / "config.json"

    return Path.home() / ".config" / APP_NAME / "config.json"


CONFIG_PATH = get_config_path()


DEFAULT_CONFIG = {
    "active_profile": "Default",
    "profiles": {
        "Default": {
            "cemu_path": "",
            "game_path": "",
            "region": "Unknown",
            "game_version": "Unknown",
            "dlc_version": "Unknown",
            "game_file_size": 0,
            "game_file_mtime": 0.0,
            "use_flatpak": False,
            "username": "",
            "server_address": "127.0.0.1:30120",
        }
    },
}

