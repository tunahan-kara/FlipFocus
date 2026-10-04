# FlipFocus

FlipFocus is a minimal Windows desktop clock, stopwatch and Pomodoro timer with a split-flap inspired interface.

## v0.3

The interface was rebuilt around a cleaner four-card clock layout so every digit flips independently, closer to a real split-flap clock.

### Features

- Clock, stopwatch and Pomodoro modes
- Four independent HH:MM split-flap digit cards
- Two-stage hinge animation with shadows and pivot details
- Small optional seconds badge
- Auto-hiding controls so the clock can sit quietly on the desktop
- Compact mode with double-click or `C`
- Frameless draggable window
- Lock-position mode
- Always-on-top mode
- 12 / 24-hour clock
- Adjustable opacity
- Start with Windows toggle
- System tray support
- Window position persistence
- Pomodoro focus / short break / long break settings
- Configurable number of focus rounds before a long break
- Long break cycle tracking
- Keyboard shortcuts:
  - `Space`: start / pause
  - `R`: reset
  - `C`: compact mode
  - `Esc`: hide to tray
- Right-click quick settings

## Run from source

Requires Python 3.11+.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Build Windows EXE locally

```text
build.bat
```

The executable will be created at:

```text
dist/FlipFocus.exe
```

## GitHub Actions

Every push to `main`:

1. checks that the Python source compiles,
2. builds `FlipFocus.exe` on Windows,
3. uploads it as the `FlipFocus-Windows` artifact.

Pushing a tag such as `v0.3.0` also creates a GitHub Release and attaches the executable.

## Roadmap

- Signed Windows builds
- Installer
- Optional notification sounds
- Additional visual themes
- More polished Windows startup/install experience

## License

MIT
