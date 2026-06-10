import json
import platform
import subprocess
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QFileDialog,
    QLabel,
    QMessageBox,
    QCheckBox,
)

APP_NAME = "BreathM"


def config_path() -> Path:
    if platform.system() == "Windows":
        return Path.home() / "AppData" / "Roaming" / APP_NAME / "config.json"

    return Path.home() / ".config" / APP_NAME / "config.json"


CONFIG = config_path()


class BreathMLauncher(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BreathM")

        self.config = self.load_config()

        layout = QVBoxLayout()

        self.title_label = QLabel("BreathM")
        self.os_label = QLabel(f"Detected OS: {platform.system()}")
        self.cemu_label = QLabel(f"Cemu: {self.config.get('cemu_path', 'not set')}")
        self.game_label = QLabel(f"BOTW .wua: {self.config.get('game_path', 'not set')}")
        self.region_label = QLabel(f"Region: {self.config.get('region', 'Unknown')}")
        self.game_version_label = QLabel(
            f"Game Version: {self.config.get('game_version', 'Unknown')}"
        )

        self.flatpak_checkbox = QCheckBox("Use Flatpak Cemu on Linux")
        self.flatpak_checkbox.setChecked(self.config.get("use_flatpak", False))
        self.flatpak_checkbox.stateChanged.connect(self.save_flatpak_setting)

        pick_cemu = QPushButton("Pick Cemu executable")
        pick_game = QPushButton("Pick BOTW .wua")
        launch = QPushButton("Launch BreathM")

        pick_cemu.clicked.connect(self.pick_cemu)
        pick_game.clicked.connect(self.pick_game)
        launch.clicked.connect(self.launch_game)

        layout.addWidget(self.title_label)
        layout.addWidget(self.os_label)
        layout.addWidget(self.flatpak_checkbox)
        layout.addWidget(self.cemu_label)
        layout.addWidget(pick_cemu)
        layout.addWidget(self.game_label)
        layout.addWidget(self.region_label)
        layout.addWidget(self.game_version_label)
        layout.addWidget(pick_game)
        layout.addWidget(launch)

        self.setLayout(layout)

        if platform.system() != "Linux":
            self.flatpak_checkbox.hide()

    def load_config(self) -> dict:
        if CONFIG.exists():
            try:
                return json.loads(CONFIG.read_text())
            except json.JSONDecodeError:
                return {}
        return {}

    def save_config(self):
        CONFIG.parent.mkdir(parents=True, exist_ok=True)
        CONFIG.write_text(json.dumps(self.config, indent=2))

    def save_flatpak_setting(self):
        self.config["use_flatpak"] = self.flatpak_checkbox.isChecked()
        self.save_config()

    def pick_cemu(self):
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

        if path:
            self.config["cemu_path"] = path
            self.save_config()
            self.cemu_label.setText(f"Cemu: {path}")

    def pick_game(self):
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
                "Invalid file",
                "BreathM only supports .wua files.",
            )
            return

        self.config["game_path"] = path

        if "region" not in self.config:
            self.config["region"] = "Unknown"

        if "game_version" not in self.config:
            self.config["game_version"] = "Unknown"

        self.save_config()

        self.game_label.setText(f"BOTW .wua: {path}")
        self.region_label.setText(f"Region: {self.config.get('region', 'Unknown')}")
        self.game_version_label.setText(
            f"Game Version: {self.config.get('game_version', 'Unknown')}"
        )

    def launch_game(self):
        game = self.config.get("game_path")

        if not game:
            QMessageBox.warning(self, "Missing game", "Pick your BOTW .wua first.")
            return

        if not game.lower().endswith(".wua"):
            QMessageBox.critical(
                self,
                "Invalid game",
                "BreathM only supports .wua files.",
            )
            return

        if platform.system() == "Linux" and self.config.get("use_flatpak", False):
            cmd = ["flatpak", "run", "info.cemu.Cemu", "-g", game]
        else:
            cemu = self.config.get("cemu_path")

            if not cemu:
                QMessageBox.warning(
                    self,
                    "Missing Cemu",
                    "Pick your Cemu executable first.",
                )
                return

            cmd = [cemu, "-g", game]

        try:
            subprocess.Popen(cmd)
        except Exception as e:
            QMessageBox.critical(self, "Launch failed", str(e))


if __name__ == "__main__":
    app = QApplication([])
    window = BreathMLauncher()
    window.resize(720, 270)
    window.show()
    app.exec()
