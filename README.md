# BreathM

BreathM is a cross-platform multiplayer framework and launcher for **The Legend of Zelda: Breath of the Wild** on **Cemu**.

It is inspired by FiveM and RedM. The long-term goal is a true multiplayer platform for BOTW, not just a launcher.

> Early alpha software. Use at your own risk.

## Current Status

BreathM is currently in early alpha.

### Launcher

- Linux support
- Windows support
- Cemu launcher support
- Flatpak Cemu support on Linux
- BOTW `.wua` support only
- Manual path entry for systems where file pickers/desktop portals break
- Config persistence
- Profiles
- Per-profile Cemu path
- Per-profile game path
- Per-profile username
- Per-profile server address

### Multiplayer / Networking

- Basic multiplayer UI
- Go dedicated server prototype
- TCP server listening on `127.0.0.1:30120`
- MessagePack-based hello packet from launcher to server
- Server logs player join and disconnect events

No gameplay synchronization exists yet.

## Requirements

### Launcher

- Python 3.11+
- PySide6
- msgpack
- Cemu 2.x
- BOTW in `.wua` format

Install Python dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows:

```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Server

- Go 1.24+

Server dependency:

- `github.com/vmihailenco/msgpack/v5`

## Running the Launcher

```bash
python3 main.py
```

On Windows:

```powershell
python main.py
```

## Running the Server

From the repository root:

```bash
cd server
go run main.go
```

Expected output:

```text
BreathM server listening on 127.0.0.1:30120
```

Then open the launcher, enter:

```text
Username: Maxim
Server: 127.0.0.1:30120
```

Click **Connect**.

The server should log the player joining.

## Repository Structure

```text
BreathM/
├── main.py
├── requirements.txt
├── README.md
├── .gitignore
└── server/
    ├── go.mod
    ├── go.sum
    └── main.go
```

## Roadmap

### Alpha 0.1 - Launcher

Completed:

- Launch BOTW from BreathM
- Linux support
- Windows support
- Config persistence
- `.wua` support

### Alpha 0.2 - Profiles

Completed:

- Create profile
- Delete profile
- Switch profile
- Per-profile game paths
- Per-profile Cemu paths

### Alpha 0.3 - Multiplayer UI

Completed:

- Username field
- Server address field
- Connect button
- Disconnect button
- Connection status

### Alpha 0.4 - Networking

In progress:

- Dedicated BreathM server
- Client/server protocol
- Join notifications
- Leave notifications
- Player list

### Alpha 0.5 - Presence System

Planned:

- Detect BOTW running
- Detect player connected
- Share basic status information

### Alpha 0.6+ - Cemu Integration Research

Planned:

- Cemu process interaction
- Memory reading
- Coordinate extraction
- Cross-platform memory abstraction

### Alpha 1.0 - Real Multiplayer

Planned:

- Shared player positions
- Ghost players
- Co-op synchronization
- Dedicated servers

## Compatibility Notes

Current versions should prioritize players having the same:

- BOTW region
- Game update version
- DLC version
- Mod set

Cross-region and cross-version compatibility may be researched later.
