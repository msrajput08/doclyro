@echo off
setlocal
cd /d "%~dp0"
where docker >nul 2>nul
if errorlevel 1 (
 echo Docker is not installed. Install Docker Desktop: https://www.docker.com/products/docker-desktop/
 pause
 exit /b 1
)
echo Starting PDFCraft Studio...
echo When the server is ready, open http://localhost:8000
call docker compose up --build
pause
