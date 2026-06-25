import json

from breathm.config import CONFIG_PATH, DEFAULT_CONFIG


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return DEFAULT_CONFIG.copy()

    try:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return DEFAULT_CONFIG.copy()

    if "profiles" not in config:
        old_config = config
        config = DEFAULT_CONFIG.copy()
        config["profiles"]["Default"]["cemu_path"] = old_config.get("cemu_path", "")
        config["profiles"]["Default"]["game_path"] = old_config.get("game_path", "")
        config["profiles"]["Default"]["region"] = old_config.get("region", "Unknown")
        config["profiles"]["Default"]["game_version"] = old_config.get("game_version", "Unknown")
        config["profiles"]["Default"]["dlc_version"] = old_config.get("dlc_version", "Unknown")
        config["profiles"]["Default"]["use_flatpak"] = old_config.get("use_flatpak", False)
        config["profiles"]["Default"]["username"] = old_config.get("username", "")
        config["profiles"]["Default"]["server_address"] = old_config.get("server_address", "127.0.0.1:30120")

    if "active_profile" not in config:
        config["active_profile"] = next(iter(config["profiles"]))

    for profile in config["profiles"].values():
        profile.setdefault("cemu_path", "")
        profile.setdefault("game_path", "")
        profile.setdefault("region", "Unknown")
        profile.setdefault("game_version", "Unknown")
        profile.setdefault("dlc_version", "Unknown")
        profile.setdefault("game_file_size", 0)
        profile.setdefault("game_file_mtime", 0.0)
        profile.setdefault("use_flatpak", False)
        profile.setdefault("username", "")
        profile.setdefault("server_address", "127.0.0.1:30120")

    return config


def save_config(config: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")
