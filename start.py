#!/usr/bin/env python3
"""
Startup script to run both Discord bot and Flask web API in the same process.
This allows both services to share the same volume on Railway.
"""
import os
import sys
import threading
import time
from pathlib import Path

def run_bot():
    """Run the Discord bot"""
    print("[🤖 BOT] Starting Discord bot...")
    try:
        # Import and run the bot
        sys.path.insert(0, str(Path(__file__).parent / "discord_bot"))
        import bot
        # The bot.py file runs automatically when imported
    except Exception as e:
        print(f"[💥 BOT] Error: {e}")
        import traceback
        traceback.print_exc()

def run_web():
    """Run the Flask web API"""
    print("[🌐 WEB] Starting Flask web API...")
    try:
        # Change to web directory
        web_dir = Path(__file__).parent / "web"
        os.chdir(web_dir)
        
        # Import and run the Flask app
        sys.path.insert(0, str(web_dir))
        from api import app
        
        port = int(os.environ.get('PORT', 5000))
        debug = os.environ.get('FLASK_ENV') != 'production'
        
        # Run Flask app
        app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=False)
    except Exception as e:
        print(f"[💥 WEB] Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Starting combined Discord Bot + Web API service")
    print("=" * 60)
    
    # Start bot in a separate thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Give bot a moment to initialize
    time.sleep(2)
    
    # Run web API in main thread (this blocks)
    run_web()
