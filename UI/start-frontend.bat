@echo off
echo ====================================
echo  Quicbo Frontend — Starting...
echo ====================================
cd /d c:\quicbo\frontend
echo Installing npm packages...
npm install
echo.
echo Starting Vite dev server on http://localhost:5173
echo.
npm run dev
