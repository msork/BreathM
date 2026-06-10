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
    QFileDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

APP_NAME = "BreathM"
FLATPAK_CEMU_ID = "info.cemu.Cemu"


def get_config_path() -> Path:
    """Return the platform-specific BreathM config path."""
    system = platform.system()

    if system == "Windows":
        return Path.home() / "AppData" / "Roaming" / APP_NAME / "config.json"

    return Path.home() / ".config" / APP_NAME / "config.json"


CONFIG_PATH = get_config_path()


class BreathMLauncher(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.config = self.load_config()

        self.setWindowTitle(APP_NAME)
        self.setMinimumWidth(720)

        self.title_label = QLabel("BreathM")
        self.os_label = QLabel(f"Detected OS: {platform.system()}")

        self.cemu_label = QLabel(self.format_cemu_label())
        self.game_label = QLabel(self.format_game_label())
        self.region_label = QLabel(f"Region: {self.config.get('region', 'Unknown')}")
        self.game_version_label = QLabel(
            f"Game Version: {self.config.get('game_version', 'Unknown')}"
        )

        self.flatpak_checkbox = QCheckBox("Use Flatpak Cemu on Linux")
        self.flatpak_checkbox.setChecked(self.config.get("use_flatpak", False))
        self.flatpak_checkbox.stateChanged.connect(self.save_flatpak_setting)

        self.pick_cemu_button = QPushButton("Pick Cemu executable")
        self.pick_game_button = QPushButton("Pick BOTW .wua")
        self.launch_button = QPushButton("Launch BreathM")

        self.pick_cemu_button.clicked.connect(self.pick_cemu)
        self.pick_game_button.clicked.connect(self.pick_game)
        self.launch_button.clicked.connect(self.launch_game)

        self.build_layout()

        if platform.system() != "Linux":
            self.flatpak_checkbox.hide()

    def build_layout(self) -> None:
        layout = QVBoxLayout()

        layout.addWidget(self.title_label)
        layout.addWidget(self.os_label)

        layout.addWidget(self.flatpak_checkbox)

        layout.addWidget(self.cemu_label)
        layout.addWidget(self.pick_cemu_button)

        layout.addWidget(self.game_label)
        layout.addWidget(self.region_label)
        layout.addWidget(self.game_version_label)
        layout.addWidget(self.pick_game_button)

        layout.addWidget(self.launch_button)

        self.setLayout(layout)

    def load_config(self) -> dict:
        if not CONFIG_PATH.exists():
            return {}

        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            QMessageBox.warning(
                self,
                "Config Error",
                "Your BreathM config file is corrupted. A new config will be used.",
            )
            return {}

    def save_config(self) -> None:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(self.config, indent=2),
            encoding="utf-8",
        )

    def format_cemu_label(self) -> str:
        cemu_path = self.config.get("cemu_path", "not set")

        if platform.system() == "Linux" and self.config.get("use_flatpak", False):
            return f"Cemu: Flatpak ({FLATPAK_CEMU_ID})"

        return f"Cemu: {cemu_path}"

    def format_game_label(self) -> str:
        return f"BOTW .wua: {self.config.get('game_path', 'not set')}"

    def save_flatpak_setting(self) -> None:
        self.config["use_flatpak"] = self.flatpak_checkbox.isChecked()
        self.save_config()
        self.cemu_label.setText(self.format_cemu_label())

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

        self.config["cemu_path"] = path
        self.save_config()
        self.cemu_label.setText(self.format_cemu_label())

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

        self.config["game_path"] = path
        self.config.setdefault("region", "Unknown")
        self.config.setdefault("game_version", "Unknown")

        self.save_config()
        self.refresh_labels()

    def refresh_labels(self) -> None:
        self.cemu_label.setText(self.format_cemu_label())
        self.game_label.setText(self.format_game_label())
        self.region_label.setText(f"Region: {self.config.get('region', 'Unknown')}")
        self.game_version_label.setText(
            f"Game Version: {self.config.get('game_version', 'Unknown')}"
        )

    def build_launch_command(self) -> list[str] | None:
        game_path = self.config.get("game_path")

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

        if platform.system() == "Linux" and self.config.get("use_flatpak", False):
            return ["flatpak", "run", FLATPAK_CEMU_ID, "-g", game_path]

        cemu_path = self.config.get("cemu_path")

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
    window.resize(720, 300)
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
