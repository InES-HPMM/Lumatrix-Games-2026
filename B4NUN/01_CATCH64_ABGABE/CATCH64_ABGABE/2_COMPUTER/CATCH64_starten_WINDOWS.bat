@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo CATCH 64 wird einmalig eingerichtet ...
    py -3 -m venv .venv
    if errorlevel 1 goto :error
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto :error
)

".venv\Scripts\python.exe" catch64.py
goto :end

:error
echo.
echo Einrichtung fehlgeschlagen. Bitte Python 3 installieren und erneut starten.
pause

:end
endlocal

