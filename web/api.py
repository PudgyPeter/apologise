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

# --- HOSPITALITY STATS ENDPOINTS ---
HOSPITALITY_STATS_FILE = BASE_LOG_DIR / "hospitality_stats.json"

def load_hospitality_stats():
    """Load hospitality statistics from file"""
    if not HOSPITALITY_STATS_FILE.exists():
        return []
    try:
        return json.loads(HOSPITALITY_STATS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

def save_hospitality_stats(stats):
    """Save hospitality statistics to file"""
    with open(HOSPITALITY_STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

@app.route('/api/hospitality/stats', methods=['GET'])
def get_hospitality_stats():
    """Get all hospitality statistics"""
    try:
        stats = load_hospitality_stats()
        return jsonify(stats)
    except Exception as e:
        print(f"[💥 API] Error loading hospitality stats: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/hospitality/stats', methods=['POST'])
def add_hospitality_stat():
    """Add a new hospitality statistic entry"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required = ['miv', 'average_spend', 'staff_member', 'meal_period']
        for field in required:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Validate meal_period
        if data['meal_period'] not in ['lunch', 'dinner']:
            return jsonify({"error": "meal_period must be 'lunch' or 'dinner'"}), 400
        
        # Auto-generate date in local timezone if not provided
        from datetime import datetime, timedelta
        if 'date' not in data or not data['date']:
            local_time = datetime.utcnow() + timedelta(hours=LOCAL_TIMEZONE_OFFSET)
            data['date'] = local_time.strftime("%Y-%m-%d")
        
        # Add timestamp
        data['created_at'] = datetime.utcnow().isoformat()
        
        # Load existing stats
        stats = load_hospitality_stats()
        
        # Add new entry
        stats.append(data)
        
        # Save back to file
        save_hospitality_stats(stats)
        
        print(f"[📊 HOSPITALITY] Added stat: {data['date']} {data['meal_period']} - MIV: {data['miv']}, A$: {data['average_spend']}, Staff: {data['staff_member']}")
        
        return jsonify({"status": "ok", "entry": data}), 201
    except Exception as e:
        print(f"[💥 API] Error adding hospitality stat: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/hospitality/stats/<entry_id>', methods=['PUT'])
def update_hospitality_stat(entry_id):
    """Update a hospitality statistic entry"""
    try:
        data = request.get_json()
        stats = load_hospitality_stats()
        
        # Find and update entry by index
        try:
            index = int(entry_id)
            if 0 <= index < len(stats):
                # Validate meal_period if provided
                if 'meal_period' in data and data['meal_period'] not in ['lunch', 'dinner']:
                    return jsonify({"error": "meal_period must be 'lunch' or 'dinner'"}), 400
                
                # Update fields
                stats[index].update(data)
                stats[index]['updated_at'] = datetime.utcnow().isoformat()
                
                save_hospitality_stats(stats)
                print(f"[📊 HOSPITALITY] Updated entry {index}: {stats[index]}")
                return jsonify({"status": "ok", "entry": stats[index]})
            else:
                return jsonify({"error": "Entry not found"}), 404
        except ValueError:
            return jsonify({"error": "Invalid entry ID"}), 400
    except Exception as e:
        print(f"[💥 API] Error updating hospitality stat: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/hospitality/stats/<entry_id>', methods=['DELETE'])
def delete_hospitality_stat(entry_id):
    """Delete a hospitality statistic entry"""
    try:
        stats = load_hospitality_stats()
        
        # Find and remove entry by index
        try:
            index = int(entry_id)
            if 0 <= index < len(stats):
                removed = stats.pop(index)
                save_hospitality_stats(stats)
                print(f"[📊 HOSPITALITY] Deleted entry {index}: {removed}")
                return jsonify({"status": "ok", "removed": removed})
            else:
                return jsonify({"error": "Entry not found"}), 404
        except ValueError:
            return jsonify({"error": "Invalid entry ID"}), 400
    except Exception as e:
        print(f"[💥 API] Error deleting hospitality stat: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/hospitality/analytics', methods=['GET'])
def get_hospitality_analytics():
    """Calculate analytics from hospitality statistics"""
    try:
        stats = load_hospitality_stats()
        
        if not stats:
            return jsonify({
                "total_entries": 0,
                "staff_performance": [],
                "day_of_week_avg": {},
                "overall_avg_miv": 0,
                "overall_avg_spend": 0
            })
        
        from collections import defaultdict
        from datetime import datetime
        
        # Staff performance tracking
        staff_data = defaultdict(lambda: {"total_spend": 0, "total_miv": 0, "count": 0, "entries": []})
        
        # Day of week tracking
        day_data = defaultdict(lambda: {"total_miv": 0, "total_spend": 0, "count": 0})
        
        # Meal period tracking
        meal_data = defaultdict(lambda: {"total_miv": 0, "total_spend": 0, "count": 0})
        
        total_miv = 0
        total_spend = 0
        
        for entry in stats:
            staff = entry.get('staff_member', 'Unknown')
            miv = float(entry.get('miv', 0))
            avg_spend = float(entry.get('average_spend', 0))
            meal_period = entry.get('meal_period', 'unknown')
            
            # Staff stats
            staff_data[staff]["total_spend"] += avg_spend
            staff_data[staff]["total_miv"] += miv
            staff_data[staff]["count"] += 1
            staff_data[staff]["entries"].append(entry)
            
            # Day of week stats
            if 'date' in entry:
                try:
                    date_obj = datetime.strptime(entry['date'], "%Y-%m-%d")
                    day_name = date_obj.strftime("%A")
                    day_data[day_name]["total_miv"] += miv
                    day_data[day_name]["total_spend"] += avg_spend
                    day_data[day_name]["count"] += 1
                except:
                    pass
            
            # Meal period stats
            meal_data[meal_period]["total_miv"] += miv
            meal_data[meal_period]["total_spend"] += avg_spend
            meal_data[meal_period]["count"] += 1
            
            total_miv += miv
            total_spend += avg_spend
        
        # Calculate staff performance
        staff_performance = []
        for staff, data in staff_data.items():
            staff_performance.append({
                "staff_member": staff,
                "avg_spend": round(data["total_spend"] / data["count"], 2),
                "avg_miv": round(data["total_miv"] / data["count"], 2),
                "total_entries": data["count"]
            })
        
        # Sort by average spend (highest first)
        staff_performance.sort(key=lambda x: x["avg_spend"], reverse=True)
        
        # Calculate day of week averages
        day_of_week_avg = {}
        for day, data in day_data.items():
            day_of_week_avg[day] = {
                "avg_miv": round(data["total_miv"] / data["count"], 2),
                "avg_spend": round(data["total_spend"] / data["count"], 2),
                "count": data["count"]
            }
        
        # Calculate meal period averages
        meal_period_avg = {}
        for meal, data in meal_data.items():
            meal_period_avg[meal] = {
                "avg_miv": round(data["total_miv"] / data["count"], 2),
                "avg_spend": round(data["total_spend"] / data["count"], 2),
                "count": data["count"]
            }
        
        return jsonify({
            "total_entries": len(stats),
            "staff_performance": staff_performance,
            "day_of_week_avg": day_of_week_avg,
            "meal_period_avg": meal_period_avg,
            "overall_avg_miv": round(total_miv / len(stats), 2),
            "overall_avg_spend": round(total_spend / len(stats), 2)
        })
    except Exception as e:
        print(f"[💥 API] Error calculating analytics: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

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
