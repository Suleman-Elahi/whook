#!/bin/bash

echo "🚀 Starting Webhook Manager..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Start Docker services
echo "📦 Starting PostgreSQL and Redis..."
docker-compose up -d

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
until docker-compose exec -T postgres pg_isready -U webhook_user -d webhooks_db > /dev/null 2>&1; do
    sleep 1
done

echo "✅ PostgreSQL is ready!"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -q -r requirements.txt

# Initialize database
echo "🔧 Initializing database..."
python init_db.py

echo ""
echo "✨ Setup complete!"
echo ""
echo "📍 Services:"
echo "   - Webhook Manager: http://localhost:5000"
echo "   - pgAdmin: http://localhost:5050 (admin@webhooks.local / admin)"
echo "   - PostgreSQL: localhost:5432"
echo "   - Redis: localhost:6379"
echo ""
echo "🚀 To start the application:"
echo "   Terminal 1: python main.py"
echo "   Terminal 2: python worker.py"
echo ""
