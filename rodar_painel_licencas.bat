@echo off
cd /d "%~dp0"
echo Abrindo Painel de Licencas...
python painel_licencas.py
if errorlevel 1 pause

