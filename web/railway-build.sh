#!/bin/sh
# Build script for Railway

echo "Installing Node dependencies..."
npm install --legacy-peer-deps

echo "Building React app..."
npm run build

echo "Build complete!"
