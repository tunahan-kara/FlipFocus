# FlipFocus

A minimal Windows desktop clock, stopwatch and Pomodoro timer with a split-flap inspired aesthetic.

## Features

- Clock, stopwatch and Pomodoro modes
- Smooth split-flap animation for hour/minute changes
- Seconds update without flip animation
- Frameless draggable desktop widget
- Always-on-top mode
- Adjustable opacity
- Compact mode (double-click or press `C`)
- Auto-hiding controls for a cleaner desktop look
- System tray icon; closing the window hides it to tray
- Persistent window position, size and preferences
- Pomodoro focus / short break / long break settings
- Automatic long break every 4 completed focus sessions
- Keyboard shortcuts:
  - `Space`: start / pause
  - `R`: reset
  - `C`: compact mode
- Right-click quick settings

## Tech

- Python 3.11+
- PySide6

## Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Build Windows EXE

Quick local build:

```text
build.bat
```

or manually:

```bash
pip install pyinstaller
pyinstaller --noconfirm --clean --windowed --onefile --name FlipFocus main.py
```

The executable will be created at `dist/FlipFocus.exe`.

## GitHub Actions

Every push to `main` builds a Windows executable and uploads it as an Actions artifact.

Pushing a version tag such as `v0.2.0` also creates a GitHub Release and attaches `FlipFocus.exe`.

## Planned

- Theme presets
- Start with Windows toggle
- Optional custom notification sounds
- Lock position
- Installer build

## License

MIT
