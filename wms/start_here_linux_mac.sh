#!/bin/bash
set -e
echo "============================================"
echo "  Wahabix Medicare Solution - Setup + Run"
echo "============================================"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "Installing dependencies..."
pip install -q -r requirements.txt

if [ ! -f ".env" ]; then
    echo "Creating default .env file..."
    cp .env.example .env
fi

echo "Applying database migrations..."
python manage.py migrate

echo ""
echo "============================================"
echo "  Setup complete! Starting server..."
echo "  Open: http://127.0.0.1:8000"
echo "  (Press CTRL+C to stop the server)"
echo "============================================"
echo ""

python manage.py runserver
