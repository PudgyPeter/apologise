"""
Flask API for Discord Bot Log Dashboard
Provides REST endpoints to access bot logs, search, and manage custom logs
"""
import os
import json
import pathlib
from datetime import datetime
from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS

# Serve React build in production
build_folder = os.path.join(os.path.dirname(__file__), 'build')
app = Flask(__name__, static_folder=build_folder, static_url_path='')
CORS(app)


# --- PATHS (same as bot.py) ---
RAILWAY_DIR = pathlib.Path("/mnt/data")
RAILWAY_APP_DIR = pathlib.Path("/app/data")
LOCAL_DIR = pathlib.Path(__file__).parent.parent / "data"  # Project root / data

# Check Railway paths first (both common mount points)
print(f"[🔍 PATH] Checking /mnt/data exists: {RAILWAY_DIR.exists()}, writable: {os.access(RAILWAY_DIR, os.W_OK) if RAILWAY_DIR.exists() else False}")
print(f"[🔍 PATH] Checking /app/data exists: {RAILWAY_APP_DIR.exists()}, writable: {os.access(RAILWAY_APP_DIR, os.W_OK) if RAILWAY_APP_DIR.exists() else False}")

if RAILWAY_DIR.exists() and os.access(RAILWAY_DIR, os.W_OK):
    BASE_LOG_DIR = RAILWAY_DIR
    print(f"[✅ PATH] Using /mnt/data")
elif RAILWAY_APP_DIR.exists() and os.access(RAILWAY_APP_DIR, os.W_OK):
    BASE_LOG_DIR = RAILWAY_APP_DIR
    print(f"[✅ PATH] Using /app/data")
else:
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    BASE_LOG_DIR = LOCAL_DIR
    print(f"[✅ PATH] Using local dir: {LOCAL_DIR}")

LIVE_MESSAGES_FILE = BASE_LOG_DIR / "live_messages.json"
print(f"[✅ PATH] Final BASE_LOG_DIR: {BASE_LOG_DIR}")
print(f"[✅ PATH] Final LIVE_MESSAGES_FILE: {LIVE_MESSAGES_FILE}")

# Timezone configuration
LOCAL_TIMEZONE_OFFSET = 11  # UTC+11 for Australian Eastern Daylight Time

# In-memory storage for live messages (since volumes can't be shared)
live_messages_cache = []
MAX_LIVE_CACHE = 5000  # Store full day of messages
last_reset_date = None

def get_today_log_path():
    """Get today's log file path in local timezone"""
    from datetime import datetime, timedelta
    local_time = datetime.utcnow() + timedelta(hours=LOCAL_TIMEZONE_OFFSET)
    today_str = local_time.strftime("logs_%Y-%m-%d.json")
    return BASE_LOG_DIR / today_str

def load_today_into_cache():
    """Load today's log file into the live cache"""
    global live_messages_cache, last_reset_date
    from datetime import datetime, timedelta
    
    # Get today's date in local timezone
    local_time = datetime.utcnow() + timedelta(hours=LOCAL_TIMEZONE_OFFSET)
    today = local_time.date()
    
    # Check if we need to reset (new day in local timezone)
    if last_reset_date and last_reset_date != today:
        print(f"[🔄 CACHE] New day detected (local time), clearing cache")
        live_messages_cache = []
    
    last_reset_date = today
    
    # Load today's log if it exists
    today_log = get_today_log_path()
    if today_log.exists():
        try:
            messages = load_log(today_log)
            live_messages_cache = messages[-MAX_LIVE_CACHE:]
            print(f"[✅ CACHE] Loaded {len(live_messages_cache)} messages from today's log")
        except Exception as e:
            print(f"[💥 CACHE] Error loading today's log: {e}")

def load_log(log_path: pathlib.Path):
    """Load a JSON log file"""
    if not log_path.exists():
        return []
    try:
        return json.loads(log_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

def fuzzy_contains(text, keyword, tolerance=2):
    """Simple fuzzy matching"""
    text = (text or "").lower()
    keyword = (keyword or "").lower()
    return keyword in text

# Load today's log into cache on startup
load_today_into_cache()

# --- API ENDPOINTS ---

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """List all available log files"""
    files = sorted(BASE_LOG_DIR.glob("logs_*.json"))
    custom = sorted(BASE_LOG_DIR.glob("custom_*.json"))
    all_files = files + custom
    
    result = []
    for f in all_files:
        date_str = f.stem.replace("logs_", "").replace("custom_", "")
        size_kb = f.stat().st_size // 1024
        is_custom = f.stem.startswith("custom_")
        result.append({
            "name": date_str,
            "filename": f.name,
            "size_kb": size_kb,
            "is_custom": is_custom,
            "path": str(f)
        })
    
    return jsonify(result)

@app.route('/api/logs/<filename>', methods=['GET'])
def get_log_content(filename):
    """Get content of a specific log file"""
    log_path = BASE_LOG_DIR / filename
    if not log_path.exists():
        return jsonify({"error": "Log file not found"}), 404
    
    data = load_log(log_path)
    return jsonify(data)

@app.route('/api/logs/<filename>/download', methods=['GET'])
def download_log(filename):
    """Download a log file"""
    # Support both .json and .txt
    base_name = filename.replace('.json', '').replace('.txt', '')
    txt_path = BASE_LOG_DIR / f"{base_name}.txt"
    json_path = BASE_LOG_DIR / f"{base_name}.json"
    
    # Prefer txt file for download
    if txt_path.exists():
        return send_file(txt_path, as_attachment=True, download_name=txt_path.name)
    elif json_path.exists():
        return send_file(json_path, as_attachment=True, download_name=json_path.name)
    else:
        return jsonify({"error": "Log file not found"}), 404

@app.route('/api/search', methods=['POST'])
def search_logs():
    """Search across all logs"""
    data = request.get_json()
    term = data.get('term', '')
    max_results = data.get('max_results', 200)
    
    if not term:
        return jsonify({"error": "Search term required"}), 400
    
    results = []
    for log_file in sorted(BASE_LOG_DIR.glob("*.json")):
        log_data = load_log(log_file)
        for entry in log_data:
            if fuzzy_contains(entry.get("content", ""), term):
                entry['log_file'] = log_file.stem
                results.append(entry)
            if len(results) >= max_results:
                break
        if len(results) >= max_results:
            break
    
    return jsonify({
        "term": term,
        "count": len(results),
        "results": results
    })

@app.route('/api/logs/custom/<name>', methods=['DELETE'])
def delete_custom_log(name):
    """Delete a custom log"""
    removed = False
    for ext in [".json", ".txt"]:
        p = BASE_LOG_DIR / f"custom_{name}{ext}"
        if p.exists():
            p.unlink()
            removed = True
    
    if removed:
        return jsonify({"message": f"Deleted custom log: {name}"})
    else:
        return jsonify({"error": "Log not found"}), 404

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get overall statistics"""
    total_logs = len(list(BASE_LOG_DIR.glob("logs_*.json")))
    custom_logs = len(list(BASE_LOG_DIR.glob("custom_*.json")))
    
    # Count total messages
    total_messages = 0
    for log_file in BASE_LOG_DIR.glob("*.json"):
        data = load_log(log_file)
        total_messages += len(data)
    
    return jsonify({
        "total_logs": total_logs,
        "custom_logs": custom_logs,
        "total_messages": total_messages
    })

@app.route('/api/live', methods=['GET'])
def get_live_messages():
    """Get live messages from in-memory cache"""
    try:
        # Check if we need to reset for a new day
        load_today_into_cache()
        
        # Return last 500 messages to avoid overwhelming the browser
        recent_messages = live_messages_cache[-500:]
        print(f"[🔴 API] Returning {len(recent_messages)} of {len(live_messages_cache)} cached messages")
        return jsonify(recent_messages)
    except Exception as e:
        print(f"[💥 API] Error in get_live_messages: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/live', methods=['POST'])
def add_live_message():
    """Receive live message from bot"""
    global live_messages_cache
    try:
        message = request.get_json()
        live_messages_cache.append(message)
        # Keep only last MAX_LIVE_CACHE messages
        live_messages_cache = live_messages_cache[-MAX_LIVE_CACHE:]
        
        # Note: Bot already writes to the log file, so we only maintain the in-memory cache here
        print(f"[🔴 API] Added message, cache now has {len(live_messages_cache)} messages")
        
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"[💥 API] Error adding live message: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()})

# Catch-all route for React app (must be last!)
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    """Serve React app for all non-API routes"""
    # Skip API routes
    if path.startswith('api/'):
        return jsonify({"error": "Not found"}), 404
    
    # Serve static files
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    
    # Serve index.html for all other routes
    try:
        return send_from_directory(app.static_folder, 'index.html')
    except Exception as e:
        return jsonify({
            "error": "Build folder not found",
            "static_folder": app.static_folder,
            "cwd": os.getcwd(),
            "message": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    app.run(host='0.0.0.0', port=port, debug=debug)
