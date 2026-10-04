# FlipFocus

FlipFocus is a minimal Windows desktop clock, stopwatch and Pomodoro timer with a split-flap inspired interface.

## v0.4

This update focuses on interaction and physical feel.

### New in v0.4

- Bottom-right resize handle that appears on hover
- Free window resizing with sensible minimum/maximum limits
- Window size persistence
- Turkish and English interface
- Language switcher in the right-click menu
- Reworked split-flap animation:
  - old top page falls into the hinge,
  - the new lower page unfolds downward,
  - moving shadows reinforce the physical drop
- Small seconds badge stays on the far right
- Existing compact mode, opacity, tray, always-on-top and Pomodoro features remain

### Features

- Clock, stopwatch and Pomodoro modes
- Four independent HH:MM split-flap digit cards
- Downward calendar-style flip animation
- Small optional seconds badge
- Auto-hiding controls
- Hover resize handle
- Turkish / English language support
- Compact mode with double-click or `C`
- Frameless draggable window
- Lock-position mode
- Always-on-top mode
- 12 / 24-hour clock
- Adjustable opacity
- Start with Windows toggle
- System tray support
- Window position and size persistence
- Configurable Pomodoro cycle
- Keyboard shortcuts:
  - `Space`: start / pause
  - `R`: reset
  - `C`: compact mode
  - `Esc`: hide to tray

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

## GitHub Actions

Every push to `main` syntax-checks the source, builds `FlipFocus.exe`, and uploads it as the `FlipFocus-Windows` artifact.

## License

MIT
