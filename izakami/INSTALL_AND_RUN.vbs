' Starts Izakami without showing a terminal window (installs on the first run).
Option Explicit
Dim shell, fso, folder, code
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
folder = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = folder
shell.Environment("Process")("IZAKAMI_SILENT") = "1"
code = shell.Run("cmd /c """ & folder & "\RUN_IZAKAMI.bat""", 0, True)
If code <> 0 Then
    MsgBox "Izakami could not start." & vbCrLf & vbCrLf & _
           "Details were saved to install.log in:" & vbCrLf & folder, vbExclamation, "Izakami Risk Calculator"
End If
