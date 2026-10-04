# FlipFocus

A minimal Windows desktop clock, stopwatch and Pomodoro timer with a split-flap inspired aesthetic.

## Features

- Clock mode
- Stopwatch mode
- Pomodoro mode
- Smooth hour/minute flip animation
- Seconds update without flip animation
- Frameless draggable window
- Always on top
- Adjustable opacity
- Persistent window position, size and preferences
- Custom Pomodoro focus/break durations
- Keyboard shortcuts:
  - `Space`: start / pause
  - `R`: reset
- Right-click menu for quick settings

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

```bash
pip install pyinstaller
pyinstaller --noconfirm --clean --windowed --onefile --name FlipFocus main.py
```

The executable will be created in:

```text
dist/FlipFocus.exe
```

## Planned

- Better physical flip-card animation
- Tray icon
- Start with Windows
- Long break / session counter
- Optional notification sound
- Theme presets
- Compact mode
- Lock position
- Auto-hide controls
- Release builds through GitHub Actions

## License

MIT
