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
DREAMS_FILE = BASE_LOG_DIR / "dreams.json"
print(f"[✅ PATH] Final BASE_LOG_DIR: {BASE_LOG_DIR}")
print(f"[✅ PATH] Final LIVE_MESSAGES_FILE: {LIVE_MESSAGES_FILE}")
print(f"[✅ PATH] Final DREAMS_FILE: {DREAMS_FILE}")

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
MANAGER_REPORTS_FILE = BASE_LOG_DIR / "manager_reports.json"

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
    # Ensure the directory exists
    HOSPITALITY_STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HOSPITALITY_STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f"[📊 HOSPITALITY] Saved {len(stats)} entries to {HOSPITALITY_STATS_FILE}")

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
        print(f"[📊 HOSPITALITY] Delete request for index {entry_id}")
        print(f"[📊 HOSPITALITY] Current stats count: {len(stats)}")
        print(f"[📊 HOSPITALITY] Stats data: {stats}")
        
        # Find and remove entry by index
        try:
            index = int(entry_id)
            print(f"[📊 HOSPITALITY] Parsed index: {index}, Valid range: 0 to {len(stats)-1}")
            if 0 <= index < len(stats):
                removed = stats.pop(index)
                save_hospitality_stats(stats)
                print(f"[📊 HOSPITALITY] Deleted entry {index}: {removed}")
                return jsonify({"status": "ok", "removed": removed})
            else:
                print(f"[💥 HOSPITALITY] Index {index} out of range (0-{len(stats)-1})")
                return jsonify({"error": "Entry not found", "index": index, "total": len(stats)}), 404
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

# --- MANAGER REPORTS ENDPOINTS ---

def load_manager_reports():
    """Load manager reports from file"""
    if not MANAGER_REPORTS_FILE.exists():
        return []
    try:
        return json.loads(MANAGER_REPORTS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

def save_manager_reports(reports):
    """Save manager reports to file"""
    MANAGER_REPORTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MANAGER_REPORTS_FILE, "w", encoding="utf-8") as f:
        json.dump(reports, f, indent=2, ensure_ascii=False)
    print(f"[📊 MANAGER] Saved {len(reports)} reports to {MANAGER_REPORTS_FILE}")

@app.route('/api/manager/reports', methods=['GET'])
def get_manager_reports():
    """Get all manager reports"""
    try:
        reports = load_manager_reports()
        return jsonify(reports)
    except Exception as e:
        print(f"[💥 API] Error loading manager reports: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/manager/reports', methods=['POST'])
def add_manager_report():
    """Add a new manager report"""
    try:
        data = request.get_json()
        
        # Add timestamp if not present
        if 'date' not in data:
            data['date'] = datetime.utcnow().isoformat()
        
        # Load existing reports
        reports = load_manager_reports()
        
        # Add new report
        reports.append(data)
        
        # Save back to file
        save_manager_reports(reports)
        
        print(f"[📊 MANAGER] Added report: {data.get('date')} - Managers: {data.get('managers', [])}")
        
        return jsonify({"status": "ok", "report": data}), 201
    except Exception as e:
        print(f"[💥 API] Error adding manager report: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/manager/reports/<report_id>', methods=['DELETE'])
def delete_manager_report(report_id):
    """Delete a manager report"""
    try:
        reports = load_manager_reports()
        
        try:
            index = int(report_id)
            if 0 <= index < len(reports):
                removed = reports.pop(index)
                save_manager_reports(reports)
                print(f"[📊 MANAGER] Deleted report {index}")
                return jsonify({"status": "ok", "removed": removed})
            else:
                return jsonify({"error": "Report not found"}), 404
        except ValueError:
            return jsonify({"error": "Invalid report ID"}), 400
    except Exception as e:
        print(f"[💥 API] Error deleting manager report: {e}")
        return jsonify({"error": str(e)}), 500

# --- DREAM LOGGING FUNCTIONS ---
def load_dreams():
    """Load dreams from JSON file"""
    try:
        if DREAMS_FILE.exists():
            with open(DREAMS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"[💥 DREAMS] Error loading dreams: {e}")
        return []

def save_dreams(dreams):
    """Save dreams to JSON file"""
    try:
        with open(DREAMS_FILE, 'w', encoding='utf-8') as f:
            json.dump(dreams, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[💥 DREAMS] Error saving dreams: {e}")
        return False

def extract_keywords(text, min_word_length=3):
    """Extract keywords from text, excluding common filler words"""
    # Common filler words to exclude
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
        'before', 'after', 'above', 'below', 'between', 'under', 'again', 'further',
        'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'both',
        'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
        'only', 'own', 'same', 'so', 'than', 'too', 'very', 'can', 'will', 'just',
        'should', 'now', 'was', 'were', 'been', 'being', 'have', 'has', 'had',
        'do', 'does', 'did', 'doing', 'would', 'could', 'ought', 'i', 'you', 'he',
        'she', 'it', 'we', 'they', 'them', 'their', 'what', 'which', 'who', 'whom',
        'this', 'that', 'these', 'those', 'am', 'is', 'are', 'be', 'as', 'if', 'my',
        'your', 'his', 'her', 'its', 'our', 'me', 'him', 'us', 'myself', 'yourself',
        'himself', 'herself', 'itself', 'ourselves', 'themselves'
    }
    
    # Clean and split text
    import re
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    
    # Filter out stop words and short words
    keywords = [w for w in words if w not in stop_words and len(w) >= min_word_length]
    
    # Count frequencies
    word_freq = {}
    for word in keywords:
        word_freq[word] = word_freq.get(word, 0) + 1
    
    return word_freq

def calculate_dream_stats(dreams):
    """Calculate statistics across all dreams"""
    if not dreams:
        return {
            'total_dreams': 0,
            'total_words': 0,
            'avg_words_per_dream': 0,
            'top_keywords': [],
            'dreams_by_month': {}
        }
    
    total_words = 0
    all_keywords = {}
    dreams_by_month = {}
    
    for dream in dreams:
        # Count words
        content = dream.get('content', '')
        words = len(content.split())
        total_words += words
        
        # Aggregate keywords
        keywords = dream.get('keywords', {})
        for word, count in keywords.items():
            all_keywords[word] = all_keywords.get(word, 0) + count
        
        # Group by month
        date_str = dream.get('date', '')
        if date_str:
            month_key = date_str[:7]  # YYYY-MM
            dreams_by_month[month_key] = dreams_by_month.get(month_key, 0) + 1
    
    # Sort keywords by frequency
    top_keywords = sorted(all_keywords.items(), key=lambda x: x[1], reverse=True)[:50]
    
    return {
        'total_dreams': len(dreams),
        'total_words': total_words,
        'avg_words_per_dream': round(total_words / len(dreams), 1) if dreams else 0,
        'top_keywords': [{'word': word, 'count': count} for word, count in top_keywords],
        'dreams_by_month': dreams_by_month
    }

# --- DREAM API ENDPOINTS ---
@app.route('/api/dreams', methods=['GET'])
def get_dreams():
    """Get all dreams with optional filtering"""
    try:
        dreams = load_dreams()
        
        # Optional search filter
        search = request.args.get('search', '').lower()
        if search:
            dreams = [d for d in dreams if search in d.get('content', '').lower() or 
                     search in d.get('title', '').lower()]
        
        # Optional date range filter
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        if start_date:
            dreams = [d for d in dreams if d.get('date', '') >= start_date]
        if end_date:
            dreams = [d for d in dreams if d.get('date', '') <= end_date]
        
        return jsonify(dreams)
    except Exception as e:
        print(f"[💥 API] Error getting dreams: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/dreams', methods=['POST'])
def create_dream():
    """Create a new dream entry"""
    try:
        data = request.json
        dreams = load_dreams()
        
        # Extract keywords from content
        content = data.get('content', '')
        keywords = extract_keywords(content)
        
        # Create new dream entry
        new_dream = {
            'id': len(dreams) + 1,
            'title': data.get('title', ''),
            'content': content,
            'date': data.get('date', datetime.now().strftime('%Y-%m-%d')),
            'tags': data.get('tags', []),
            'keywords': keywords,
            'created_at': datetime.now().isoformat()
        }
        
        dreams.append(new_dream)
        save_dreams(dreams)
        
        print(f"[✨ DREAMS] Created new dream: {new_dream['title']}")
        return jsonify(new_dream), 201
    except Exception as e:
        print(f"[💥 API] Error creating dream: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/dreams/<int:dream_id>', methods=['PUT'])
def update_dream(dream_id):
    """Update an existing dream"""
    try:
        data = request.json
        dreams = load_dreams()
        
        # Find dream by ID
        dream_index = next((i for i, d in enumerate(dreams) if d.get('id') == dream_id), None)
        if dream_index is None:
            return jsonify({"error": "Dream not found"}), 404
        
        # Extract keywords from updated content
        content = data.get('content', dreams[dream_index].get('content', ''))
        keywords = extract_keywords(content)
        
        # Update dream
        dreams[dream_index].update({
            'title': data.get('title', dreams[dream_index].get('title', '')),
            'content': content,
            'date': data.get('date', dreams[dream_index].get('date', '')),
            'tags': data.get('tags', dreams[dream_index].get('tags', [])),
            'keywords': keywords,
            'updated_at': datetime.now().isoformat()
        })
        
        save_dreams(dreams)
        
        print(f"[✏️ DREAMS] Updated dream {dream_id}")
        return jsonify(dreams[dream_index])
    except Exception as e:
        print(f"[💥 API] Error updating dream: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/dreams/<int:dream_id>', methods=['DELETE'])
def delete_dream(dream_id):
    """Delete a dream"""
    try:
        dreams = load_dreams()
        
        # Find and remove dream
        dream_index = next((i for i, d in enumerate(dreams) if d.get('id') == dream_id), None)
        if dream_index is None:
            return jsonify({"error": "Dream not found"}), 404
        
        removed = dreams.pop(dream_index)
        save_dreams(dreams)
        
        print(f"[🗑️ DREAMS] Deleted dream {dream_id}")
        return jsonify({"status": "ok", "removed": removed})
    except Exception as e:
        print(f"[💥 API] Error deleting dream: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/dreams/stats', methods=['GET'])
def get_dream_stats():
    """Get statistics about all dreams"""
    try:
        dreams = load_dreams()
        stats = calculate_dream_stats(dreams)
        return jsonify(stats)
    except Exception as e:
        print(f"[💥 API] Error getting dream stats: {e}")
        return jsonify({"error": str(e)}), 500

# Explicit route for hospitality (React Router will handle it)
@app.route('/hospitality')
def serve_hospitality():
    """Serve hospitality-specific HTML with correct manifest"""
    print(f"[🌐 ROUTE] Hospitality route hit!")
    try:
        # Try to serve hospitality.html first (for PWA)
        hospitality_html = os.path.join(app.static_folder, 'hospitality.html')
        if os.path.exists(hospitality_html):
            print(f"[🌐 ROUTE] Serving hospitality.html")
            return send_from_directory(app.static_folder, 'hospitality.html')
        else:
            print(f"[🌐 ROUTE] hospitality.html not found, serving index.html")
            return send_from_directory(app.static_folder, 'index.html')
    except Exception as e:
        print(f"[🌐 ROUTE] Error: {e}")
        return jsonify({"error": str(e)}), 500

# Service Worker route (must be at root for proper scope)
@app.route('/service-worker.js')
def serve_service_worker():
    """Serve service worker with correct MIME type and no caching"""
    print(f"[🌐 ROUTE] Service worker requested")
    try:
        response = send_from_directory(app.static_folder, 'service-worker.js')
        response.headers['Content-Type'] = 'application/javascript'
        response.headers['Service-Worker-Allowed'] = '/'
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response
    except Exception as e:
        print(f"[🌐 ROUTE] Service worker error: {e}")
        return jsonify({"error": "Service worker not found"}), 404

# Explicit route for dreams (let React Router handle it)
@app.route('/dreams')
def serve_dreams():
    """Serve main index.html - React Router will handle the /dreams route"""
    print(f"[🌐 ROUTE] Dreams route hit - serving index.html for React Router")
    try:
        return send_from_directory(app.static_folder, 'index.html')
    except Exception as e:
        print(f"[🌐 ROUTE] Error: {e}")
        return jsonify({"error": str(e)}), 500

# Catch-all route for React app (must be last!)
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    """Serve React app for all non-API routes"""
    print(f"[🌐 ROUTE] Requested path: '{path}'")
    print(f"[🌐 ROUTE] Static folder: {app.static_folder}")
    print(f"[🌐 ROUTE] Static folder exists: {os.path.exists(app.static_folder)}")
    
    # Skip API routes
    if path.startswith('api/'):
        return jsonify({"error": "Not found"}), 404
    
    # Serve static files (CSS, JS, images, etc.)
    static_file_path = os.path.join(app.static_folder, path)
    if path != "" and os.path.exists(static_file_path):
        print(f"[🌐 ROUTE] Serving static file: {path}")
        return send_from_directory(app.static_folder, path)
    
    # For all other routes (including /hospitality), serve index.html
    # This allows React Router to handle client-side routing
    try:
        index_path = os.path.join(app.static_folder, 'index.html')
        print(f"[🌐 ROUTE] Checking index.html at: {index_path}")
        print(f"[🌐 ROUTE] Index exists: {os.path.exists(index_path)}")
        
        if os.path.exists(index_path):
            print(f"[🌐 ROUTE] ✅ Serving index.html for path: {path}")
            return send_from_directory(app.static_folder, 'index.html')
        else:
            print(f"[🌐 ROUTE] ❌ Index.html not found!")
            return jsonify({
                "error": "Build folder not found",
                "static_folder": app.static_folder,
                "index_path": index_path,
                "index_exists": os.path.exists(index_path),
                "cwd": os.getcwd(),
                "build_contents": os.listdir(app.static_folder) if os.path.exists(app.static_folder) else "folder not found"
            }), 500
    except Exception as e:
        print(f"[🌐 ROUTE] ❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": "Error serving React app",
            "static_folder": app.static_folder,
            "cwd": os.getcwd(),
            "message": str(e),
            "traceback": traceback.format_exc()
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    app.run(host='0.0.0.0', port=port, debug=debug)
