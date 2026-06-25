Set sh = CreateObject("Shell.Application")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
ps1 = scriptDir & "\install_apple_usb.ps1"
cmd = "-NoProfile -ExecutionPolicy Bypass -NoExit -File """ & ps1 & """"
sh.ShellExecute "powershell.exe", cmd, scriptDir, "runas", 1
