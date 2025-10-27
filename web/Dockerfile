# Multi-stage build for React + Flask

# Stage 1: Build React app
FROM node:18-alpine AS frontend-build
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source files
COPY public ./public
COPY src ./src

# Build React app
RUN npm run build

# Stage 2: Python Flask server
FROM python:3.10-slim
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Flask API
COPY api.py .

# Copy built React app from previous stage
COPY --from=frontend-build /app/build ./build

# Expose port
EXPOSE 8080

# Set environment variables
ENV FLASK_ENV=production
ENV PORT=8080

# Run the application
CMD gunicorn api:app --bind 0.0.0.0:$PORT
