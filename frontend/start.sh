#!/bin/bash

# Adam Setup Frontend Startup Script

set -e

echo "🚀 Starting Adam Setup Agent Frontend..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js first."
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install npm first."
    exit 1
fi

# Check if .env.local exists
if [ ! -f ".env.local" ]; then
    echo "⚠️  Warning: .env.local file not found. Creating from example..."
    cp env.example .env.local
    echo "📝 Please edit .env.local with your API URL if needed"
fi

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

echo "🔧 Starting development server..."

# Start the development server
npm run dev

echo "✅ Frontend started successfully!"
echo ""
echo "🌐 Frontend URLs:"
echo "   • Local: http://localhost:3000"
echo "   • Network: http://192.168.1.186:3000"
echo ""
echo "🔗 Make sure the API is running on http://localhost:8000"
echo "📋 To stop: Press Ctrl+C" 