@echo off
rem Construit l'installateur Windows (.exe) sur un PC Windows.
rem Prérequis : Python 3.12 ou plus, Inno Setup 6 (https://jrsoftware.org/isinfo.php).
rem Depuis le dossier du projet :  packaging\construire_windows.bat
cd /d "%~dp0\.."
set /p VERSION=<packaging\VERSION
python -m pip install -r requirements.txt "pyinstaller>=6.16" || exit /b 1
python -m PyInstaller packaging\mapping_epi.spec --noconfirm --distpath dist --workpath build || exit /b 1
"%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" /DAppVersion=%VERSION% packaging\windows\mapping_epi.iss || exit /b 1
echo Installateur : dist\MappingEpi-%VERSION%-Windows-Installation.exe
