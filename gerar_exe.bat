@echo off
setlocal
cd /d "%~dp0"

if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
)

echo === Gerando lancamento-conta-apagar.exe ===
pyinstaller lancamento-conta-apagar.spec
if errorlevel 1 (
    echo ERRO no PyInstaller.
    exit /b 1
)

echo.
echo === Copiando licenca_config.py para dist\ ===
python pos_build_dist.py
if errorlevel 1 exit /b 1

echo.
echo Concluido. Veja a pasta dist\
pause
