from pathlib import Path

from breathm.config import BOTW_TITLE_IDS, WUA_TITLE_FOLDER_RE


def get_game_file_signature(game_path: str) -> tuple[int, float] | None:
    try:
        stat = Path(game_path).stat()
    except OSError:
        return None

    return stat.st_size, stat.st_mtime


def cached_game_detection_is_valid(profile: dict, game_path: str) -> bool:
    signature = get_game_file_signature(game_path)

    if signature is None:
        return False

    file_size, file_mtime = signature

    return (
        profile.get("game_path") == game_path
        and profile.get("game_file_size") == file_size
        and profile.get("game_file_mtime") == file_mtime
        and profile.get("region", "Unknown") != "Unknown"
        and profile.get("game_version", "Unknown") != "Unknown"
        and profile.get("dlc_version", "Unknown") != "Unknown"
    )


def auto_detect_game_info(game_path: str) -> tuple[str, str, str]:
    region = "Unknown"
    game_version = "Unknown"
    dlc_version = "Unknown"

    detected_titles = scan_wua_title_folders(game_path)

    for title_id, version in detected_titles:
        title_info = BOTW_TITLE_IDS.get(title_id.lower())

        if title_info is None:
            continue

        detected_region, title_type = title_info

        if region == "Unknown":
            region = detected_region

        if title_type == "update":
            game_version = version
        elif title_type == "dlc":
            dlc_version = version

    if region != "Unknown" or game_version != "Unknown" or dlc_version != "Unknown":
        return region, game_version, dlc_version

    fallback_region, fallback_game_version = detect_game_info_from_filename(game_path)
    return fallback_region, fallback_game_version, "Unknown"


def scan_wua_title_folders(game_path: str) -> list[tuple[str, str]]:
    titles: list[tuple[str, str]] = []
    found_types: set[str] = set()

    try:
        with open(game_path, "rb") as file:
            previous_chunk = b""

            while True:
                chunk = file.read(1024 * 1024 * 16)

                if not chunk:
                    break

                search_data = previous_chunk + chunk

                for match in WUA_TITLE_FOLDER_RE.finditer(search_data):
                    title_id = match.group(1).decode("ascii").lower()
                    version = match.group(2).decode("ascii")

                    entry = (title_id, version)
                    if entry not in titles:
                        titles.append(entry)

                    title_info = BOTW_TITLE_IDS.get(title_id)
                    if title_info is not None:
                        _, title_type = title_info
                        found_types.add(title_type)

                if {"base", "update", "dlc"}.issubset(found_types):
                    break

                previous_chunk = search_data[-128:]

    except OSError:
        return []

    return titles


def detect_game_info_from_filename(game_path: str) -> tuple[str, str]:
    text = Path(game_path).name.lower()

    region = "Unknown"
    game_version = "Unknown"

    if any(token in text for token in ["usa", "us", "american"]):
        region = "USA"
    elif any(token in text for token in ["europe", "eur", "eu"]):
        region = "Europe"
    elif any(token in text for token in ["japan", "jpn", "jp"]):
        region = "Japan"

    version_markers = ["v", "version", "update"]

    for marker in version_markers:
        marker_index = text.find(marker)
        if marker_index == -1:
            continue

        after_marker = text[marker_index + len(marker):]
        digits = ""

        for char in after_marker:
            if char.isdigit():
                digits += char
            elif digits:
                break

        if digits:
            game_version = digits
            break

    return region, game_version
    
def is_botw_wua(game_path: str) -> bool:
    detected_titles = scan_wua_title_folders(game_path)

    return any(
        title_id.lower() in BOTW_TITLE_IDS
        for title_id, _version in detected_titles
    )
