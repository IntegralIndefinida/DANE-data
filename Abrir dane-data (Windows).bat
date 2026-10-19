@echo off
rem Lanzador de dane-data para Windows.
rem La primera vez instala "uv" (que a su vez trae Python y las librerias); luego solo abre la app.
setlocal
cd /d "%~dp0"
title dane-data
set "PATH=%USERPROFILE%\.local\bin;%PATH%"

echo ==============================================
echo   dane-data - Microdatos del DANE
echo ==============================================

where uv >nul 2>nul
if not errorlevel 1 goto preparar

echo.
echo Primera vez: instalando el asistente uv, unos segundos...
rem Sin tocar el PATH del usuario: este lanzador agrega %USERPROFILE%\.local\bin solo para si mismo.
set "UV_NO_MODIFY_PATH=1"
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
where uv >nul 2>nul
if not errorlevel 1 goto preparar
echo.
echo No se pudo instalar uv. Revise su conexion a internet e intente de nuevo.
pause
exit /b 1

:preparar
echo.
echo Preparando la aplicacion... la primera vez tarda 1 a 3 minutos: descarga Python y librerias.
echo.
uv run --frozen --quiet --extra app dane-data app
if errorlevel 1 goto error
exit /b 0

:error
echo.
echo La aplicacion se cerro con un error. Si persiste, envie una captura de esta ventana.
pause
exit /b 1
