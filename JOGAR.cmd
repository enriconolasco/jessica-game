@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if errorlevel 1 goto erro
)
".venv\Scripts\python.exe" -c "import rich" >nul 2>&1
if errorlevel 1 (
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto erro
)
if /i "%~1"=="web" goto web
if /i "%~1"=="online" goto online
".venv\Scripts\python.exe" -m jessica.main
if errorlevel 1 goto erro
exit /b 0
:web
echo Abra http://127.0.0.1:8765 no navegador. Mantenha esta janela aberta.
echo Para encerrar o servidor, pressione Ctrl+C nesta janela.
".venv\Scripts\python.exe" -m jessica.web.server
if errorlevel 1 goto erro
exit /b 0
:erro
echo Nao foi possivel iniciar. Confira o Python instalado e a mensagem acima.
pause
exit /b 1

:online
".venv\Scripts\python.exe" -c "import websockets; assert websockets.__version__.split('.')[0] == '17'" >nul 2>&1
if errorlevel 1 (
  ".venv\Scripts\python.exe" -m pip install -r requirements-online.txt
  if errorlevel 1 goto erro
)
echo Online experimental: abra http://127.0.0.1:8767 em quatro abas.
echo Salas ainda ficam em memoria. Nao reinicie o servidor durante a partida.
echo Para encerrar, pressione Ctrl+C.
".venv\Scripts\python.exe" -m jessica.web.online_server
if errorlevel 1 goto erro
exit /b 0
