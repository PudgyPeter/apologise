# Discord Log Dashboard

A modern web interface to view and search your Discord bot logs.

## Features

- 📊 **Dashboard Overview** - View statistics about your logs
- 📁 **Log Browser** - Browse all daily and custom logs
- 🔍 **Search** - Fuzzy search across all logs
- 💾 **Download** - Download logs in text format
- 🗑️ **Manage** - Delete custom logs
- 📱 **Responsive** - Works on desktop and mobile

## Setup

### Backend (Flask API)

1. Install Python dependencies:
```bash
cd web
pip install -r requirements.txt
```

2. Run the API server:
```bash
python api.py
```

The API will run on `http://localhost:5000`

### Frontend (React)

1. Install Node.js dependencies:
```bash
cd web
npm install
```

2. Start the development server:
```bash
npm start
```

The web app will open at `http://localhost:3000`

## Production Deployment

### Build the React app:
```bash
npm run build
```

### Run both services:

**Option 1: Separate processes**
- Run Flask API: `gunicorn -w 4 -b 0.0.0.0:5000 api:app`
- Serve React build folder with a web server (nginx, Apache, etc.)

**Option 2: Flask serves React**
Modify `api.py` to serve the React build folder as static files.

## API Endpoints

- `GET /api/logs` - List all log files
- `GET /api/logs/<filename>` - Get log content
- `GET /api/logs/<filename>/download` - Download log file
- `POST /api/search` - Search logs (body: `{"term": "search term"}`)
- `DELETE /api/logs/custom/<name>` - Delete custom log
- `GET /api/stats` - Get statistics
- `GET /api/health` - Health check

## Environment Variables

- `PORT` - API server port (default: 5000)

## Notes

- The API reads from the same data directory as your Discord bot
- Logs are stored in `/mnt/data` (Railway) or `../data` (local)
- Search supports fuzzy matching for better results
