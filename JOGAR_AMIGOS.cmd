@echo off
setlocal
cd /d "%~dp0"
call JOGAR.cmd amigos
if errorlevel 1 pause
