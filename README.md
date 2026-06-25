# <img src="assets/icon.png" width="2.5%" alt="BreathM Icon"> BreathM

BreathM is a cross-platform multiplayer framework and launcher for **The Legend of Zelda: Breath of the Wild** running on **Cemu**.

Inspired by **FiveM** and **RedM**, the long-term goal is to create a true multiplayer platform for BOTW.

> **Status:** Early alpha software. Features and networking are under active development.

---

# Features

## Launcher

- Linux support
- Windows support
- Native Cemu support
- Flatpak Cemu support (Linux)
- BOTW `.wua` support
- Configuration persistence
- Multi-profile support
- Automatic BOTW metadata detection
- Automatic compatibility validation

## Automatic Game Detection

BreathM automatically detects from your `.wua`:

- Region
- Game Update Version
- DLC Version

Detection is cached, so reopening the launcher is nearly instant unless the game file changes.

No Cemu launch or memory reading is required.

---

## Profiles

Each profile stores:

- Username
- Server address
- Cemu path
- BOTW path
- Region
- Game Version
- DLC Version
- Flatpak preference (Linux)

---

## Multiplayer

- Dedicated Go server
- TCP networking
- MessagePack protocol
- Live player list
- Join notifications
- Leave notifications
- Event log
- Player status synchronization
- Automatic reconnect handling

---

## Compatibility

Before allowing players to join the same session, BreathM validates:

- BreathM protocol version
- BOTW Region
- BOTW Update Version
- BOTW DLC Version

Players with incompatible versions are rejected with a clear error message.

---

## Discord Rich Presence

Features include:

- Launcher status
- In-game status
- Connected player count
- Automatic game detection
- Automatic reconnect handling
- Multi-instance support (only one launcher on the same PC owns Discord RPC)
- Timer persistence while connected

---

# Current Status

**Current Version:** **Alpha 0.7**

Completed:

- Cross-platform launcher
- Multi-profile system
- Dedicated multiplayer server
- TCP networking
- MessagePack protocol
- Discord Rich Presence
- Automatic BOTW detection
- Region validation
- Game version validation
- DLC version validation
- Protocol validation
- Live player list
- Event log
- Graceful shutdown
- Automatic game detection cache

Gameplay synchronization has **not** started yet.

---

# Requirements

## Launcher

- Python 3.11+
- Cemu 2.x
- BOTW `.wua`

Python dependencies:

- PySide6
- msgpack
- pypresence

Install:

### Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Windows

```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

---

## Server

Requirements:

- Go 1.24+

Dependency:

```text
github.com/vmihailenco/msgpack/v5
```

---

# Running the Server

```bash
cd server
go run main.go
```

Expected output:

```text
BreathM server listening on 127.0.0.1:30120
```

---

# Running the Launcher

Linux:

```bash
python3 main.py
```

Windows:

```powershell
python main.py
```

---

# Connecting

Example:

```text
Username: Maxim
Server: 127.0.0.1:30120
```

Click **Connect**.

The server will:

- Register the player
- Validate compatibility
- Synchronize player status
- Broadcast player lists
- Broadcast join events
- Broadcast leave events

---

# Repository Structure

```text
BreathM/
├── assets/
│   └── icon.png
├── server/
│   ├── go.mod
│   ├── go.sum
│   └── main.go
├── .gitignore
├── main.py
├── README.md
└── requirements.txt
```

---

# Roadmap

## Alpha 0.1 — Launcher ✅

- Launch BOTW from BreathM
- Linux support
- Windows support
- `.wua` support
- Configuration persistence

---

## Alpha 0.2 — Profiles ✅

- Multiple profiles
- Per-profile game paths
- Per-profile Cemu paths
- Flatpak support

---

## Alpha 0.3 — Multiplayer UI ✅

- Username
- Server address
- Connect / Disconnect
- Player list
- Connection status

---

## Alpha 0.4 — Networking ✅

- Dedicated Go server
- TCP networking
- MessagePack protocol
- Join / Leave events

---

## Alpha 0.5 — Presence ✅

- Discord Rich Presence
- Launcher / In-game status
- Automatic game close detection
- Presence synchronization

---

## Alpha 0.6 — Compatibility & Networking Polish ✅

- Protocol validation
- Region validation
- Multi-instance Discord support
- Graceful shutdown
- Event log
- Server information
- Live player synchronization

---

## Alpha 0.7 — Automatic Game Detection ✅

- Automatic Region detection
- Automatic Game Version detection
- Automatic DLC Version detection
- Cached metadata detection
- Game Version validation
- DLC Version validation
- Improved reconnect handling

---

## Alpha 0.8 — Planned

- Server browser
- Saved servers
- Recent servers
- Improved connection UI

---

## Alpha 0.9 — Planned

- Cemu integration research
- Cross-platform abstractions
- Memory interaction research

---

## Alpha 1.0 — Multiplayer

- Shared player positions
- Ghost players
- Gameplay synchronization
- Dedicated multiplayer sessions

---

# Compatibility Goals

Players should use the same:

- BreathM protocol version
- BOTW region
- BOTW update version
- BOTW DLC version
- Mod configuration

Future releases may include:

- Automatic mod detection
- Mod synchronization
- Cross-version compatibility research

---

# License

A project license will be added before the first public release.
