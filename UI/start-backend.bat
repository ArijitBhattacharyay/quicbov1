@echo off
echo ====================================
echo  Quicbo Backend — Starting...
echo ====================================
cd /d c:\quicbo\backend
echo Installing dependencies...
pip install -r requirements.txt
echo.
echo Installing Playwright Chromium browser...
python -m playwright install chromium
echo.
echo Starting FastAPI server on http://localhost:8000
echo.
uvicorn main:app --reload --port 8000 --host 0.0.0.0
