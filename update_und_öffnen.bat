@echo off
title OP-14 Preistracker
echo.
echo  Aktualisiere Preisdaten...
echo.
python "%~dp0scraper.py"
echo.
echo  Offne Web-Interface...
start "" "%~dp0index.html"
echo.
echo  Fertig! Das Dashboard wurde im Browser geoffnet.
timeout /t 3 >nul
