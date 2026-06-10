"""
BreathM Launcher

Cross-platform launcher for Breath of the Wild on Cemu.
Supports Linux and Windows.
Currently expects .wua games only.
"""

import json
import platform
import subprocess
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

APP_NAME = "BreathM"
FLATPAK_CEMU_ID = "info.cemu.Cemu"


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
        }
    },
}


class BreathMLauncher(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.config = self.load_config()

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
        self.region_label = QLabel()
        self.game_version_label = QLabel()

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
        main_layout.addWidget(self.region_label)
        main_layout.addWidget(self.game_version_label)
        main_layout.addWidget(self.pick_game_button)

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

        if "active_profile" not in config:
            config["active_profile"] = next(iter(config["profiles"]))

        return config

    def save_config(self) -> None:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(self.config, indent=2), encoding="utf-8")

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

        self.current_profile()["game_path"] = path
        self.save_config()
        self.refresh_labels()

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
        profile.setdefault("region", "Unknown")
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
            subprocess.Popen(command)
        except OSError as error:
            QMessageBox.critical(
                self,
                "Launch Failed",
                f"Could not launch Cemu:\n\n{error}",
            )


def main() -> None:
    app = QApplication([])
    window = BreathMLauncher()
    window.resize(760, 420)
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
