"""
BreathM Launcher

Cross-platform launcher for Breath of the Wild on Cemu.
Supports Linux and Windows.
Currently expects .wua games only.
"""

import json
import os
import platform
import socket
import subprocess
import threading
import time
from pathlib import Path

import msgpack

try:
    from pypresence import Presence
except ImportError:
    Presence = None

from PySide6.QtCore import QLockFile, QTimer

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QTextEdit,
)

APP_NAME = "BreathM"
FLATPAK_CEMU_ID = "info.cemu.Cemu"
DISCORD_CLIENT_ID = "1514412498814763088"
PROTOCOL_VERSION = "alpha-0.5"

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
            "use_flatpak": False,
            "username": "",
            "server_address": "127.0.0.1:30120",
        }
    },
}


class BreathMLauncher(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.config = self.load_config()
        self.server_socket: socket.socket | None = None
        self.game_process: subprocess.Popen | None = None
        self.detected_cemu_status = "Not running"
        self.message_unpacker: msgpack.Unpacker | None = None
        self.pending_server_messages: list[dict] = []
        self.server_name = ""
        self.connected_player_count = 0
        self.has_received_player_list = False
        self.presence_status = "launcher"
        
        self.discord_rpc = None
        self.discord_lock: QLockFile | None = None

        self.last_discord_attempt = 0
        self.last_discord_details = ""
        self.last_discord_state = ""
        self.discord_started_at = int(time.time())

        self.server_poll_timer = QTimer(self)
        self.server_poll_timer.timeout.connect(self.poll_server_messages)
        self.server_poll_timer.start(100)
        
        self.game_poll_timer = QTimer(self)
        self.game_poll_timer.timeout.connect(self.poll_game_process)
        self.game_poll_timer.start(1000)

        self.setWindowTitle(APP_NAME)
        self.setMinimumWidth(760)

        self.title_label = QLabel("BreathM")
        self.os_label = QLabel(f"Detected OS: {platform.system()}")

        self.profile_box = QComboBox()
        self.profile_box.addItems(self.config["profiles"].keys())
        self.profile_box.setCurrentText(self.config["active_profile"])
        self.profile_box.currentTextChanged.connect(self.change_profile)

        self.new_profile_button = QPushButton("New Profile")
        self.delete_profile_button = QPushButton("Delete Profile")

        self.new_profile_button.clicked.connect(self.new_profile)
        self.delete_profile_button.clicked.connect(self.delete_profile)

        self.cemu_label = QLabel()
        self.game_label = QLabel()

        self.cemu_path_input = QLineEdit()
        self.cemu_path_input.setPlaceholderText("Paste Cemu executable path here")
        self.cemu_path_input.editingFinished.connect(self.save_cemu_path_from_input)

        self.game_path_input = QLineEdit()
        self.game_path_input.setPlaceholderText("Paste BOTW .wua path here")
        self.game_path_input.editingFinished.connect(self.save_game_path_from_input)
        
        
        self.region_box = QComboBox()
        self.region_box.addItems(
            [
                "Unknown",
                "US",
                "Europe",
                "Japan",
            ]
        )
        self.region_box.currentTextChanged.connect(self.save_region_settings)

        self.region_label = QLabel()
        
        self.game_version_input = QLineEdit()
        self.game_version_input.setPlaceholderText("BOTW version (example: 208)")
        self.game_version_input.editingFinished.connect(
            self.save_region_settings
        )
        
        self.game_version_label = QLabel()
        self.cemu_status_label = QLabel("Cemu Status: Not running")

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.editingFinished.connect(self.save_multiplayer_settings)

        self.server_address_input = QLineEdit()
        self.server_address_input.setPlaceholderText("Server address, example: 127.0.0.1:30120")
        self.server_address_input.editingFinished.connect(self.save_multiplayer_settings)

        self.connect_button = QPushButton("Connect")
        self.disconnect_button = QPushButton("Disconnect")
        self.connection_status_label = QLabel("Status: Disconnected")
        self.server_info_label = QLabel("Server: Not connected")
        self.player_list_widget = QListWidget()
        
        self.event_log = QTextEdit()
        self.event_log.setReadOnly(True)

        self.connect_button.clicked.connect(self.connect_to_server)
        self.disconnect_button.clicked.connect(self.disconnect_from_server)

        self.flatpak_checkbox = QCheckBox("Use Flatpak Cemu on Linux")
        self.flatpak_checkbox.stateChanged.connect(self.save_flatpak_setting)

        self.pick_cemu_button = QPushButton("Pick Cemu executable")
        self.pick_game_button = QPushButton("Pick BOTW .wua")
        self.launch_button = QPushButton("Launch BreathM")

        self.pick_cemu_button.clicked.connect(self.pick_cemu)
        self.pick_game_button.clicked.connect(self.pick_game)
        self.launch_button.clicked.connect(self.launch_game)

        self.build_layout()
        self.refresh_labels()

        if platform.system() != "Linux":
            self.flatpak_checkbox.hide()

    def build_layout(self) -> None:
        main_layout = QVBoxLayout()

        profile_row = QHBoxLayout()
        profile_row.addWidget(QLabel("Profile:"))
        profile_row.addWidget(self.profile_box)
        profile_row.addWidget(self.new_profile_button)
        profile_row.addWidget(self.delete_profile_button)

        main_layout.addWidget(self.title_label)
        main_layout.addWidget(self.os_label)
        main_layout.addLayout(profile_row)

        main_layout.addWidget(self.flatpak_checkbox)

        main_layout.addWidget(self.cemu_label)
        main_layout.addWidget(self.cemu_path_input)
        main_layout.addWidget(self.pick_cemu_button)

        main_layout.addWidget(self.game_label)
        main_layout.addWidget(self.game_path_input)
        
        main_layout.addWidget(QLabel("Region"))
        main_layout.addWidget(self.region_box)

        main_layout.addWidget(QLabel("Game Version"))
        main_layout.addWidget(self.game_version_input)

        main_layout.addWidget(self.region_label)
        main_layout.addWidget(self.game_version_label)
        main_layout.addWidget(self.cemu_status_label)
        
        main_layout.addWidget(self.pick_game_button)

        main_layout.addWidget(QLabel("Multiplayer"))
        main_layout.addWidget(self.username_input)
        main_layout.addWidget(self.server_address_input)

        multiplayer_button_row = QHBoxLayout()
        multiplayer_button_row.addWidget(self.connect_button)
        multiplayer_button_row.addWidget(self.disconnect_button)
        main_layout.addLayout(multiplayer_button_row)
        main_layout.addWidget(self.connection_status_label)
        main_layout.addWidget(self.server_info_label)
        main_layout.addWidget(QLabel("Connected Players"))
        main_layout.addWidget(self.player_list_widget)
        
        main_layout.addWidget(QLabel("Events"))
        main_layout.addWidget(self.event_log)

        main_layout.addWidget(self.launch_button)

        self.setLayout(main_layout)

    def load_config(self) -> dict:
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
            config["profiles"]["Default"]["game_version"] = old_config.get(
                "game_version", "Unknown"
            )
            config["profiles"]["Default"]["use_flatpak"] = old_config.get(
                "use_flatpak", False
            )
            config["profiles"]["Default"]["username"] = old_config.get("username", "")
            config["profiles"]["Default"]["server_address"] = old_config.get(
                "server_address", "127.0.0.1:30120"
            )

        if "active_profile" not in config:
            config["active_profile"] = next(iter(config["profiles"]))

        for profile in config["profiles"].values():
            profile.setdefault("cemu_path", "")
            profile.setdefault("game_path", "")
            profile.setdefault("region", "Unknown")
            profile.setdefault("game_version", "Unknown")
            profile.setdefault("use_flatpak", False)
            profile.setdefault("username", "")
            profile.setdefault("server_address", "127.0.0.1:30120")

        return config

    def save_config(self) -> None:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(self.config, indent=2), encoding="utf-8")
        
    def save_region_settings(self) -> None:
        profile = self.current_profile()

        profile["region"] = self.region_box.currentText()
        profile["game_version"] = (
            self.game_version_input.text().strip()
            or "Unknown"
        )

        self.save_config()
        self.refresh_labels()

    def current_profile_name(self) -> str:
        return self.config["active_profile"]

    def current_profile(self) -> dict:
        return self.config["profiles"][self.current_profile_name()]

    def change_profile(self, profile_name: str) -> None:
        if not profile_name:
            return

        self.config["active_profile"] = profile_name
        self.save_config()
        self.refresh_labels()

    def new_profile(self) -> None:
        name, ok = QInputDialog.getText(self, "New Profile", "Profile name:")

        if not ok or not name.strip():
            return

        name = name.strip()

        if name in self.config["profiles"]:
            QMessageBox.warning(self, "Profile Exists", "That profile already exists.")
            return

        self.config["profiles"][name] = {
            "cemu_path": "",
            "game_path": "",
            "region": "Unknown",
            "game_version": "Unknown",
            "use_flatpak": False,
            "username": name,
            "server_address": "127.0.0.1:30120",
        }

        self.config["active_profile"] = name
        self.save_config()

        self.profile_box.addItem(name)
        self.profile_box.setCurrentText(name)
        self.refresh_labels()

    def delete_profile(self) -> None:
        name = self.current_profile_name()

        if len(self.config["profiles"]) <= 1:
            QMessageBox.warning(
                self,
                "Cannot Delete Profile",
                "BreathM needs at least one profile.",
            )
            return

        confirm = QMessageBox.question(
            self,
            "Delete Profile",
            f"Delete profile '{name}'?",
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        del self.config["profiles"][name]
        self.config["active_profile"] = next(iter(self.config["profiles"]))

        self.save_config()

        self.profile_box.clear()
        self.profile_box.addItems(self.config["profiles"].keys())
        self.profile_box.setCurrentText(self.config["active_profile"])
        self.refresh_labels()

    def format_cemu_label(self) -> str:
        profile = self.current_profile()

        if platform.system() == "Linux" and profile.get("use_flatpak", False):
            return f"Cemu: Flatpak ({FLATPAK_CEMU_ID})"

        return f"Cemu: {profile.get('cemu_path') or 'not set'}"

    def format_game_label(self) -> str:
        return f"BOTW .wua: {self.current_profile().get('game_path') or 'not set'}"

    def save_flatpak_setting(self) -> None:
        self.current_profile()["use_flatpak"] = self.flatpak_checkbox.isChecked()
        self.save_config()
        self.refresh_labels()

    def save_cemu_path_from_input(self) -> None:
        path = self.cemu_path_input.text().strip()
        self.current_profile()["cemu_path"] = path
        self.save_config()
        self.refresh_labels()
        
    def auto_detect_game_info(self, game_path: str) -> tuple[str, str]:
        text = Path(game_path).name.lower()

        region = "Unknown"
        game_version = "Unknown"

        if any(token in text for token in ["usa", "us", "american"]):
            region = "US"
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

    def save_game_path_from_input(self) -> None:
        path = self.game_path_input.text().strip()

        if path and not path.lower().endswith(".wua"):
            QMessageBox.critical(
                self,
                "Invalid File",
                "BreathM currently only supports .wua files.",
            )
            self.game_path_input.setText(self.current_profile().get("game_path", ""))
            return

        profile = self.current_profile()
        profile["game_path"] = path

        region, game_version = self.auto_detect_game_info(path)

        if region != "Unknown":
            profile["region"] = region

        if game_version != "Unknown":
            profile["game_version"] = game_version

        self.save_config()
        self.refresh_labels()

    def save_multiplayer_settings(self) -> None:
        profile = self.current_profile()
        profile["username"] = self.username_input.text().strip()
        profile["server_address"] = self.server_address_input.text().strip()
        self.save_config()

    def parse_server_address(self, server_address: str) -> tuple[str, int] | None:
        if ":" not in server_address:
            QMessageBox.warning(
                self,
                "Invalid Server",
                "Server address must look like this: 127.0.0.1:30120",
            )
            return None

        host, port_text = server_address.rsplit(":", 1)
        host = host.strip()

        try:
            port = int(port_text.strip())
        except ValueError:
            QMessageBox.warning(self, "Invalid Server", "Server port must be a number.")
            return None

        if not host or port <= 0 or port > 65535:
            QMessageBox.warning(
                self,
                "Invalid Server",
                "Server address must look like this: 127.0.0.1:30120",
            )
            return None

        return host, port

    def get_discord_lock_path(self) -> Path:
        return CONFIG_PATH.parent / "discord.lock"

    def acquire_discord_lock(self) -> bool:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

        lock = QLockFile(str(self.get_discord_lock_path()))
        lock.setStaleLockTime(10000)

        if not lock.tryLock(100):
            return False

        self.discord_lock = lock
        return True

    def release_discord_lock(self) -> None:
        if self.discord_lock is None:
            return

        self.discord_lock.unlock()
        self.discord_lock = None

    def connect_to_server(self) -> None:
        self.save_multiplayer_settings()

        profile = self.current_profile()
        username = profile.get("username", "").strip()
        server_address = profile.get("server_address", "").strip()

        if not username:
            QMessageBox.warning(self, "Missing Username", "Enter a username first.")
            return

        if not server_address:
            QMessageBox.warning(
                self,
                "Missing Server",
                "Enter a server address first. Example: 127.0.0.1:30120",
            )
            return

        parsed_address = self.parse_server_address(server_address)
        if parsed_address is None:
            return

        if self.server_socket is not None:
            self.disconnect_from_server()

        host, port = parsed_address

        try:
            self.server_socket = socket.create_connection((host, port), timeout=5)
            hello_message = {
                "type": "hello",
                "username": username,
                "protocol_version": PROTOCOL_VERSION,
                "region": profile.get("region", "Unknown"),
                "game_version": profile.get("game_version", "Unknown"),
            }
            self.message_unpacker = msgpack.Unpacker(raw=False, max_map_len=64)
            self.server_socket.sendall(msgpack.packb(hello_message, use_bin_type=True))

            while True:
                welcome_message = self.read_next_server_message()

                message_type = welcome_message.get("type")

                if message_type == "warning":
                    warning = welcome_message.get("warning", "")
                    if warning:
                        self.add_event(f"WARNING: {warning}")
                        QMessageBox.warning(
                            self,
                            "Compatibility Warning",
                            warning,
                        )
                    continue

                if message_type == "error":
                    raise OSError(
                        welcome_message.get(
                            "message",
                            "Server rejected connection",
                        )
                    )

                if message_type == "welcome":
                    break

                raise OSError("Server sent an unexpected response")

            server_name = welcome_message.get("server_name", "Unknown Server")
            self.server_name = server_name
            self.server_socket.setblocking(False)
            self.set_presence_status("launcher")
            
        except (OSError, ValueError, msgpack.ExtraData, msgpack.FormatError) as error:
            if self.server_socket is not None:
                try:
                    self.server_socket.close()
                except OSError:
                    pass

            self.server_socket = None

            QMessageBox.critical(
                self,
                "Connection Failed",
                f"Could not connect to BreathM server:\n\n{error}",
            )
            self.connection_status_label.setText("Status: Disconnected")
            return

        self.connection_status_label.setText(
            f"Status: Connected to {server_name} as {username} ({PROTOCOL_VERSION})"
        )
        
        self.server_info_label.setText(
            f"Server: {server_name} | Protocol: {PROTOCOL_VERSION}"
        )
        
        self.force_discord_update()

    def read_next_server_message(self) -> dict:
        if self.server_socket is None or self.message_unpacker is None:
            raise OSError("Not connected to server")

        if self.pending_server_messages:
            return self.pending_server_messages.pop(0)

        while True:
            chunk = self.server_socket.recv(4096)

            if not chunk:
                raise OSError("Server disconnected before sending message")

            self.message_unpacker.feed(chunk)

            messages = list(self.message_unpacker)

            if messages:
                self.pending_server_messages.extend(messages[1:])
                return messages[0]

    def poll_server_messages(self) -> None:
        if self.server_socket is None or self.message_unpacker is None:
            return

        while self.pending_server_messages:
            self.handle_server_message(self.pending_server_messages.pop(0))

        try:
            while True:
                chunk = self.server_socket.recv(4096)

                if not chunk:
                    self.disconnect_from_server()
                    return

                self.message_unpacker.feed(chunk)

                for message in self.message_unpacker:
                    self.handle_server_message(message)
        except BlockingIOError:
            return
        except OSError:
            self.disconnect_from_server()
            
    def poll_game_process(self) -> None:
        self.update_detected_cemu_status()

        if self.game_process is None:
            return

        if self.game_process.poll() is None:
            return

        self.game_process = None
        self.set_presence_status("launcher")
        
    def update_detected_cemu_status(self) -> None:
        if self.game_process is not None and self.game_process.poll() is None:
            status = "BOTW likely running"
        elif self.is_cemu_process_running():
            status = "Cemu running"
        else:
            status = "Not running"

        if status == self.detected_cemu_status:
            return

        self.detected_cemu_status = status
        self.cemu_status_label.setText(f"Cemu Status: {status}")

    def is_cemu_process_running(self) -> bool:
        if platform.system() == "Windows":
            command = ["tasklist"]
        else:
            command = ["ps", "-A", "-o", "comm="]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
        except OSError:
            return False

        output = result.stdout.lower()
        return "cemu" in output

    def send_server_message(self, message: dict) -> None:
        if self.server_socket is None:
            return

        self.server_socket.sendall(msgpack.packb(message, use_bin_type=True))

    def send_status_to_server(self) -> None:
        self.send_server_message(
            {
                "type": "status",
                "status": self.presence_status,
            }
        )

    def set_presence_status(self, status: str) -> None:
        self.presence_status = status

        if self.server_socket is not None:
            try:
                self.send_status_to_server()
            except OSError:
                self.disconnect_from_server()

        self.update_discord_presence()

    def setup_discord_rpc(self) -> None:
        if self.discord_rpc is not None:
            return

        if self.discord_lock is None and not self.acquire_discord_lock():
            return

        if Presence is None:
            return

        client_id = os.environ.get(
            "BREATHM_DISCORD_CLIENT_ID",
            DISCORD_CLIENT_ID,
        )

        if not client_id:
            return

        try:
            print("Discord RPC connecting...")

            rpc = Presence(client_id)
            rpc.connect()

            self.discord_rpc = rpc

            print("Discord RPC connected")

        except Exception as error:
            print(f"Discord RPC unavailable: {error}")
            return

        self.update_discord_presence()

    def update_discord_presence(self) -> None:
        if self.discord_rpc is None:
            now = time.time()

            if now - self.last_discord_attempt > 2:
                self.last_discord_attempt = now
                threading.Thread(
                    target=self.setup_discord_rpc,
                    daemon=True,
                ).start()

            return

        state = "In Game" if self.presence_status == "in_game" else "In Launcher"

        if self.server_socket is not None:
            if not self.has_received_player_list:
                details = "Connecting to server"
            else:
                player_word = "player" if self.connected_player_count == 1 else "players"
                details = f"{self.connected_player_count} {player_word} connected"
        else:
            details = "Using BreathM Launcher"

        if details == self.last_discord_details and state == self.last_discord_state:
            return

        try:
            self.discord_rpc.update(
                details=details,
                state=state,
                large_text="BreathM",
                start=self.discord_started_at,
            )

            self.last_discord_details = details
            self.last_discord_state = state
        except Exception as error:
            print(f"Discord RPC update failed: {error}")

            try:
                self.discord_rpc.close()
            except Exception:
                pass

            self.discord_rpc = None

    def close_discord_rpc(self) -> None:
        if self.discord_rpc is None:
            return

        try:
            self.discord_rpc.close()
        except Exception:
            pass

        self.discord_rpc = None
        self.release_discord_lock()
        
    def force_discord_update(self) -> None:
        self.last_discord_details = ""
        self.last_discord_state = ""
        self.update_discord_presence()

    def handle_server_message(self, message: dict) -> None:
        message_type = message.get("type")

        if message_type == "player_list":
            players = message.get("players", [])
            self.update_player_list(players)

        elif message_type == "event":
            event = message.get("event", "")
            if event:
                self.add_event(event)
                
        elif message_type == "warning":
            warning = message.get("warning", "")
            if warning:
                self.add_event(f"WARNING: {warning}")
                QMessageBox.warning(self, "Compatibility Warning", warning)

    def update_player_list(self, players: list[dict]) -> None:
        self.connected_player_count = len(players)
        self.has_received_player_list = True

        self.update_discord_presence()
        
        self.player_list_widget.clear()

        for player in players:
            if isinstance(player, dict):
                username = str(player.get("username", "Unknown"))
                status = str(player.get("status", "launcher"))
                status_text = "In Game" if status == "in_game" else "In Launcher"
                region = str(player.get("region", "Unknown"))
                game_version = str(player.get("game_version", "Unknown"))
                self.player_list_widget.addItem(
                    f"{username} - {status_text} - {region} - v{game_version}"
                )
            else:
                self.player_list_widget.addItem(str(player))
            
    def add_event(self, text: str) -> None:
        self.event_log.append(text)

    def disconnect_from_server(self) -> None:
        if self.server_socket is not None:
            try:
                self.server_socket.close()
            except OSError:
                pass

            self.server_socket = None
            self.message_unpacker = None
            self.server_name = ""

        self.player_list_widget.clear()
        self.has_received_player_list = False
        self.connected_player_count = 0
        
        self.presence_status = "launcher"
        self.update_discord_presence()
        self.connection_status_label.setText("Status: Disconnected")
        self.server_info_label.setText("Server: Not connected")
        self.event_log.clear()

    def pick_cemu(self) -> None:
        if platform.system() == "Windows":
            file_filter = "Cemu executable (Cemu.exe);;Executables (*.exe)"
        else:
            file_filter = "Cemu executable (*)"

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Cemu executable",
            "",
            file_filter,
        )

        if not path:
            return

        self.current_profile()["cemu_path"] = path
        self.save_config()
        self.refresh_labels()

    def pick_game(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select BOTW .wua",
            "",
            "Wii U Archive (*.wua)",
        )

        if not path:
            return

        if not path.lower().endswith(".wua"):
            QMessageBox.critical(
                self,
                "Invalid File",
                "BreathM currently only supports .wua files.",
            )
            return

        profile = self.current_profile()
        profile["game_path"] = path

        region, game_version = self.auto_detect_game_info(path)

        if region != "Unknown":
            profile["region"] = region
        else:
            profile.setdefault("region", "Unknown")

        if game_version != "Unknown":
            profile["game_version"] = game_version
        else:
            profile.setdefault("game_version", "Unknown")

        self.save_config()
        self.refresh_labels()

    def refresh_labels(self) -> None:
        profile = self.current_profile()

        self.cemu_label.setText(self.format_cemu_label())
        self.game_label.setText(self.format_game_label())

        self.cemu_path_input.blockSignals(True)
        self.cemu_path_input.setText(profile.get("cemu_path", ""))
        self.cemu_path_input.blockSignals(False)

        self.game_path_input.blockSignals(True)
        self.game_path_input.setText(profile.get("game_path", ""))
        self.game_path_input.blockSignals(False)

        self.username_input.blockSignals(True)
        self.username_input.setText(profile.get("username", ""))
        self.username_input.blockSignals(False)

        self.server_address_input.blockSignals(True)
        self.server_address_input.setText(profile.get("server_address", "127.0.0.1:30120"))
        self.server_address_input.blockSignals(False)

        self.connection_status_label.setText("Status: Disconnected")
        self.server_info_label.setText("Server: Not connected")
        
        self.region_box.blockSignals(True)
        self.region_box.setCurrentText(
            profile.get("region", "Unknown")
        )
        self.region_box.blockSignals(False)

        self.game_version_input.blockSignals(True)
        self.game_version_input.setText(
            profile.get("game_version", "")
        )
        self.game_version_input.blockSignals(False)

        self.region_label.setText(f"Region: {profile.get('region', 'Unknown')}")
        self.game_version_label.setText(
            f"Game Version: {profile.get('game_version', 'Unknown')}"
        )

        self.flatpak_checkbox.blockSignals(True)
        self.flatpak_checkbox.setChecked(profile.get("use_flatpak", False))
        self.flatpak_checkbox.blockSignals(False)

    def build_launch_command(self) -> list[str] | None:
        profile = self.current_profile()
        game_path = profile.get("game_path")

        if not game_path:
            QMessageBox.warning(self, "Missing Game", "Pick your BOTW .wua first.")
            return None

        if not game_path.lower().endswith(".wua"):
            QMessageBox.critical(
                self,
                "Invalid Game",
                "BreathM currently only supports .wua files.",
            )
            return None

        if platform.system() == "Linux" and profile.get("use_flatpak", False):
            return ["flatpak", "run", FLATPAK_CEMU_ID, "-g", game_path]

        cemu_path = profile.get("cemu_path")

        if not cemu_path:
            QMessageBox.warning(
                self,
                "Missing Cemu",
                "Pick your Cemu executable first.",
            )
            return None

        return [cemu_path, "-g", game_path]

    def launch_game(self) -> None:
        command = self.build_launch_command()

        if command is None:
            return

        try:
            self.game_process = subprocess.Popen(command)
            self.set_presence_status("in_game")
            self.force_discord_update()
        except OSError as error:
            QMessageBox.critical(
                self,
                "Launch Failed",
                f"Could not launch Cemu:\n\n{error}",
            )

    def closeEvent(self, event) -> None:  # noqa: N802
        try:
            self.server_poll_timer.stop()
            self.game_poll_timer.stop()

            if self.server_socket is not None:
                try:
                    self.server_socket.close()
                except OSError:
                    pass

                self.server_socket = None
                self.message_unpacker = None
                self.pending_server_messages.clear()

            self.close_discord_rpc()
        finally:
            event.accept()


def main() -> None:
    app = QApplication([])
    window = BreathMLauncher()
    window.resize(760, 680)
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
