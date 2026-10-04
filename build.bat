@echo off
setlocal
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller pillow
python assets\create_icon.py
python -m py_compile main.py assets\create_icon.py
pyinstaller --noconfirm --clean --windowed --onefile --name FlipFocus --icon assets\flipfocus.ico --version-file version_info.txt main.py
echo.
echo Build complete: dist\FlipFocus.exe
pause
