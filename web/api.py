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
app = Flask(__name__, static_folder='build', static_url_path='')
CORS(app)

# --- PATHS (same as bot.py) ---
RAILWAY_DIR = pathlib.Path("/mnt/data")
RAILWAY_APP_DIR = pathlib.Path("/app/data")
LOCAL_DIR = pathlib.Path(os.getcwd()).parent / "data"

# Check Railway paths first (both common mount points)
if RAILWAY_DIR.exists() and os.access(RAILWAY_DIR, os.W_OK):
    BASE_LOG_DIR = RAILWAY_DIR
elif RAILWAY_APP_DIR.exists() and os.access(RAILWAY_APP_DIR, os.W_OK):
    BASE_LOG_DIR = RAILWAY_APP_DIR
else:
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    BASE_LOG_DIR = LOCAL_DIR

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
