<p align="center">
  <img src="assets/flipfocus.svg" width="112" alt="FlipFocus logo">
</p>

<h1 align="center">FlipFocus</h1>

<p align="center">
  Minimal Windows split-flap clock, stopwatch and Pomodoro timer.
</p>

## 1.0

FlipFocus is feature-complete for the first stable release.

### Core features

- Clock, stopwatch and Pomodoro modes
- Four independent HH:MM split-flap digit cards
- Downward calendar-style flip animation
- Small optional seconds badge
- Turkish / English interface
- Bottom-right hover resize handle
- Window size and position persistence
- Compact mode with double-click or `C`
- Always-on-top and lock-position modes
- 12 / 24-hour clock
- Adjustable opacity
- Start with Windows toggle
- System tray support
- Configurable Pomodoro focus, short break, long break and round count
- Tray notification when a Pomodoro phase completes

### Close behavior

The close button now behaves like a normal Windows application by default: **X fully exits FlipFocus**.

If you prefer tray behavior, enable **“Çarpıya basınca arka planda çalıştır / Keep running in tray when closed”** from the right-click menu.

`Esc` always hides to the system tray when a tray is available.

### Performance

- Visible UI timer runs at a modest 250 ms interval.
- Stopwatch timing uses `time.perf_counter()`, so elapsed time remains accurate without constant redraws.
- When hidden, unnecessary updates stop.
- A running Pomodoro switches to a low-frequency background timer and still fires its completion notification.

### Windows packaging

The executable has:
- a dedicated FlipFocus split-flap icon,
- Windows product/version metadata,
- a deterministic icon build step,
- syntax/import checks before packaging.

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

The executable will be created at `dist/FlipFocus.exe`.

## Keyboard shortcuts

- `Space` — start / pause
- `R` — reset
- `C` — compact mode
- `Esc` — hide to tray

## License

MIT
