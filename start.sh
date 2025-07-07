# IoT Sensor Monitoring System Startup Script

echo "Starting IoT Sensor Monitoring System..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
echo "Installing requirements..."
pip install -r requirements.txt

# Start the server
echo "Starting server on http://localhost:8000"
python run.py
