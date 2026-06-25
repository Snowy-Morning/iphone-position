@echo off
:: 发布包 runtime\ 或本地开发 .venv\
if exist "%~dp0runtime\Scripts\pymobiledevice3.exe" (
    set "PMD3=%~dp0runtime\Scripts\pymobiledevice3.exe"
    set "PY=%~dp0runtime\python.exe"
) else if exist "%~dp0runtime\Scripts\pymobiledevice3.cmd" (
    set "PMD3=%~dp0runtime\Scripts\pymobiledevice3.cmd"
    set "PY=%~dp0runtime\python.exe"
) else if exist "%~dp0..\.venv\Scripts\pymobiledevice3.exe" (
    set "PMD3=%~dp0..\.venv\Scripts\pymobiledevice3.exe"
    set "PY=%~dp0..\.venv\Scripts\python.exe"
) else (
    set "PMD3=pymobiledevice3"
    set "PY=python"
)
