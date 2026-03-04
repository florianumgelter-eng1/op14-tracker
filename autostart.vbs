' Startet den OP-14 Server unsichtbar und öffnet Chrome
Dim shell
Set shell = CreateObject("WScript.Shell")

Dim pythonw
pythonw = "C:\Users\flori\AppData\Local\Programs\Python\Python312\pythonw.exe"

Dim serverScript
serverScript = "C:\Users\flori\op14-tracker\server.py"

Dim chrome
chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"

' Server starten (unsichtbar, kein Fenster)
shell.Run Chr(34) & pythonw & Chr(34) & " " & Chr(34) & serverScript & Chr(34), 0, False

' 3 Sekunden warten bis Server bereit ist
WScript.Sleep 3000

' Chrome mit dem Dashboard öffnen
shell.Run Chr(34) & chrome & Chr(34) & " --new-window http://localhost:8765", 1, False

Set shell = Nothing
