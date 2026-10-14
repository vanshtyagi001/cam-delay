Set objFSO = CreateObject("Scripting.FileSystemObject")
strCurrentDir = objFSO.GetParentFolderName(WScript.ScriptFullName)

Set objShell = CreateObject("WScript.Shell")
objShell.CurrentDirectory = strCurrentDir

' Launch main.py with pythonw.exe with 0 window style (completely hidden)
strCommand = "pythonw.exe """ & strCurrentDir & "\main.py"""
objShell.Run strCommand, 0, False
