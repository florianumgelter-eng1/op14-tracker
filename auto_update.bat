@echo off
title OP-14 Auto-Update (alle 6 Stunden)
echo.
echo  Auto-Update gestartet (alle 6 Stunden)
echo  Fenster offen lassen - STRG+C zum Beenden
echo.

:loop
echo [%date% %time%] Fetching...
python "%~dp0scraper.py"
echo.
echo  Naechstes Update in 6 Stunden...
timeout /t 21600 /nobreak
goto loop
