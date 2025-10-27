"""
Migration script to add avatar_url and role_color to existing log entries.
Run this once to update all historical logs.
"""
import json
import pathlib
import os

# --- PATHS ---
RAILWAY_DIR = pathlib.Path("/mnt/data")
RAILWAY_APP_DIR = pathlib.Path("/app/data")
LOCAL_DIR = pathlib.Path(os.getcwd()) / "data"

# Check Railway paths first
if RAILWAY_DIR.exists() and os.access(RAILWAY_DIR, os.W_OK):
    BASE_LOG_DIR = RAILWAY_DIR
elif RAILWAY_APP_DIR.exists() and os.access(RAILWAY_APP_DIR, os.W_OK):
    BASE_LOG_DIR = RAILWAY_APP_DIR
else:
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    BASE_LOG_DIR = LOCAL_DIR

print(f"Using log directory: {BASE_LOG_DIR}")

# Default avatar URL (Discord default)
DEFAULT_AVATAR = "https://cdn.discordapp.com/embed/avatars/0.png"

def migrate_file(filepath):
    """Add missing fields to log entries"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        updated = False
        for entry in data:
            # Add avatar_url if missing
            if 'avatar_url' not in entry:
                entry['avatar_url'] = DEFAULT_AVATAR
                updated = True
            
            # Add role_color if missing (will be None, but field exists)
            if 'role_color' not in entry:
                entry['role_color'] = None
                updated = True
            
            # Add author_display if missing
            if 'author_display' not in entry and 'author' in entry:
                entry['author_display'] = entry['author']
                updated = True
            
            # Add author_id if missing
            if 'author_id' not in entry:
                entry['author_id'] = 0
                updated = True
        
        if updated:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"✅ Updated {filepath.name} ({len(data)} entries)")
        else:
            print(f"⏭️  Skipped {filepath.name} (already up to date)")
        
        return updated
    except Exception as e:
        print(f"❌ Error processing {filepath.name}: {e}")
        return False

# Migrate all JSON log files
total_updated = 0
for log_file in sorted(BASE_LOG_DIR.glob("*.json")):
    if migrate_file(log_file):
        total_updated += 1

print(f"\n🎉 Migration complete! Updated {total_updated} files.")
