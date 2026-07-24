@echo off
echo ============================================
echo   Wahabix Medicare Solution - Setup + Run
echo ============================================

if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo Installing dependencies...
pip install -q -r requirements.txt

if not exist .env (
    echo Creating default .env file...
    copy .env.example .env
)

echo Applying database migrations...
python manage.py migrate

echo.
echo ============================================
echo   Setup complete! Starting server...
echo   Open: http://127.0.0.1:8000
echo   (Press CTRL+C to stop the server)
echo ============================================
echo.

python manage.py runserver
pause
