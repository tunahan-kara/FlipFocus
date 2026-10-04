@echo off
setlocal
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller
pyinstaller --noconfirm --clean --windowed --onefile --name FlipFocus main.py
echo.
echo Build complete: dist\FlipFocus.exe
pause
