# Deployment Guide

## Architecture

This project runs as a **single Railway service** that combines:
- Discord bot (runs in background thread)
- Flask web API (serves the dashboard)

Both services share the same persistent volume at `/mnt/data`.

## Railway Setup

### 1. Create a Single Service

1. Create one Railway service from this repository
2. Add a persistent volume mounted to `/mnt/data`
3. Set the following environment variables:
   - `TOKEN` - Your Discord bot token
   - `PORT` - Railway will set this automatically (usually 5000)
   - `FLASK_ENV=production`

### 2. Build Configuration

Railway will automatically:
- Install dependencies from `requirements.txt`
- Run `python start.py` (defined in `Procfile`)
- Expose the web API on the PORT

### 3. Volume Configuration

- **Mount point**: `/mnt/data`
- **Purpose**: Stores all log files (daily logs, custom logs, live messages)
- Both bot and web API read/write to this shared location

## Local Development

Run both services together:

```bash
python start.py
```

Or run them separately:

```bash
# Terminal 1 - Discord Bot
python discord_bot/bot.py

# Terminal 2 - Web API
cd web
python api.py
```

Both will use the local `data/` directory.

## File Structure

```
apologise/
├── start.py              # Combined startup script
├── Procfile              # Railway process definition
├── requirements.txt      # All dependencies (bot + web)
├── data/                 # Local development logs
│   └── logs_*.json
├── discord_bot/
│   ├── bot.py           # Discord bot
│   └── migrate_logs.py
└── web/
    ├── api.py           # Flask API
    ├── build/           # React frontend (built)
    └── src/             # React source
```

## How It Works

1. `start.py` launches both services:
   - Discord bot runs in a background thread
   - Flask web API runs in the main thread
2. Both services check for `/mnt/data` (Railway volume)
3. If not found, they fall back to local `data/` directory
4. Logs are written to the same location by both services
5. Live feed messages persist throughout the day
6. At midnight (UTC+11), logs roll over to a new daily file

## Troubleshooting

### Logs not appearing on website
- Check that both services are using the same data directory
- Verify the volume is mounted correctly on Railway
- Check Railway logs for path detection messages

### Bot not starting
- Verify `TOKEN` environment variable is set
- Check Railway logs for bot initialization messages

### Web API not accessible
- Ensure Railway has assigned a public URL
- Check that `PORT` environment variable is set
- Verify the React app is built (`web/build/` exists)
