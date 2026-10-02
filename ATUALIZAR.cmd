@echo off
setlocal
cd /d "%~dp0"
call :atualizar
set "jessica_exit=%errorlevel%"
if /i not "%~1"=="--no-pause" pause
exit /b %jessica_exit%

:atualizar
where git >nul 2>&1
if errorlevel 1 (
  echo Git nao encontrado. Baixe novamente a versao main do projeto.
  exit /b 1
)
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
  echo Esta copia nao possui Git. Atualize baixando o ZIP da main em outra pasta.
  echo Preserve seus saves e nao substitua a pasta antiga.
  exit /b 1
)
git diff --quiet
if errorlevel 1 goto pendente
git diff --cached --quiet
if errorlevel 1 goto pendente
for /f "delims=" %%R in ('git config --get remote.origin.url 2^>nul') do set "jessica_origin=%%R"
if /i not "%jessica_origin%"=="https://github.com/enriconolasco/jessica-game.git" (
  echo Origem diferente do repositorio oficial. Nenhuma atualizacao aplicada.
  exit /b 1
)
git fetch origin main
if errorlevel 1 exit /b 1
git merge-base --is-ancestor HEAD origin/main
if errorlevel 1 (
  echo Esta copia possui commits fora da main. A integracao precisa ser revisada.
  echo Nenhum commit local sera descartado.
  exit /b 1
)
git merge --ff-only origin/main
if errorlevel 1 exit /b 1
echo Versao instalada:
git rev-parse --short HEAD
echo Atualizacao concluida. Reabra o jogo ou servidor para usar a nova versao.
exit /b 0

:pendente
echo Existem alteracoes locais em arquivos versionados. Atualizacao interrompida.
echo Preserve ou registre essas alteracoes antes de atualizar.
exit /b 1
