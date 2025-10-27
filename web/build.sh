#!/bin/bash
set -e

echo "Installing Node dependencies..."
npm install --legacy-peer-deps

echo "Building React app..."
npm run build

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Build complete!"
