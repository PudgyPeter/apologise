# Dream Journal PWA Setup Guide

Your Dream Journal is now a Progressive Web App (PWA) that can be installed on your phone like a native app!

## 🎨 Step 1: Generate App Icons

Before deploying, create the Dream Journal icons:

1. Open `web/public/generate-dream-icons.html` in your browser
2. Click **"📥 Download 192x192 Icon"** and save as `dream-icon-192.png`
3. Click **"📥 Download 512x512 Icon"** and save as `dream-icon-512.png`
4. Move both PNG files to the `web/public/` folder

The icons feature a beautiful moon with stars on a purple gradient background - perfect for a dream journal!

## 🚀 Step 2: Build and Deploy

```bash
cd web
npm run build
```

Then push to GitHub and deploy to Railway (or your hosting platform).

## 📱 Step 3: Install on iPhone

### Method 1: Direct Installation (Recommended)
1. **Open Safari** on your iPhone (must use Safari, not Chrome)
2. **Navigate to** `https://your-app-url.com/dreams`
3. **Tap the Share button** (square with arrow pointing up)
4. **Scroll down** and tap **"Add to Home Screen"**
5. **Name it** "Dream Journal" or whatever you prefer
6. **Tap "Add"** in the top right

### Method 2: From Main App
1. Navigate to your main app URL
2. Go to the `/dreams` route
3. Follow the same "Add to Home Screen" steps

## ✨ What You Get

### 🌙 Standalone App Experience
- **Dedicated app icon** with moon and stars design
- **Full-screen mode** (no Safari UI bars)
- **Splash screen** when launching
- **Separate from main app** (can install both!)

### 📴 Offline Functionality
- **View dreams** you've previously loaded
- **Create new dreams** while offline (syncs when back online)
- **Search cached dreams** without internet
- **Statistics** calculated from cached data

### ⚡ Performance Features
- **Instant loading** (cached resources)
- **Background sync** for offline dream entries
- **Persistent storage** (won't be cleared automatically)
- **Automatic updates** when you deploy changes

### 🎯 App Shortcuts
Long-press the app icon to access:
- **New Dream** - Jump straight to creating a dream
- **Statistics** - View your dream stats

## 🔧 Technical Details

### PWA Manifest
The Dream Journal uses a dedicated manifest (`dreams-manifest.json`) with:
- **Start URL**: `/dreams`
- **Theme Color**: Purple (#667eea)
- **Display**: Standalone
- **Orientation**: Portrait
- **Scope**: Limited to `/dreams` route

### Service Worker Features
- **Network-first strategy** for API calls (always fresh data)
- **Cache-first strategy** for static assets (fast loading)
- **Background sync** for offline dream submissions
- **Automatic cache updates** on new deployments

### Data Persistence
- **LocalStorage** for app preferences (dark mode)
- **IndexedDB** via service worker for offline queue
- **Persistent storage** request (prevents automatic clearing)

## 📊 Offline Capabilities

### What Works Offline
✅ View previously loaded dreams  
✅ Search through cached dreams  
✅ View statistics (from cached data)  
✅ Create new dreams (queued for sync)  
✅ Edit cached dreams (queued for sync)  
✅ Toggle dark mode  
✅ Browse keyword analysis  

### What Requires Internet
❌ Loading new dreams from server  
❌ Deleting dreams (requires server confirmation)  
❌ Fetching latest statistics  
❌ Syncing offline-created dreams  

### Offline Dream Creation
When you create a dream while offline:
1. Dream is saved to offline queue
2. Visual indicator shows "Pending sync"
3. When internet returns, background sync triggers
4. Dream is automatically uploaded to server
5. Queue is cleared on success

## 🎨 Customization

### Change Theme Color
Edit `web/public/dreams-manifest.json`:
```json
{
  "theme_color": "#667eea",  // Change this
  "background_color": "#1a202c"  // And this
}
```

### Change App Name
Edit `web/public/dreams-manifest.json`:
```json
{
  "name": "My Dream Diary",  // Full name
  "short_name": "Dreams"     // Home screen name
}
```

### Custom Icons
Replace `dream-icon-192.png` and `dream-icon-512.png` with your own designs.

## 🔍 Troubleshooting

### "Add to Home Screen" not showing?
- ✅ Use Safari (not Chrome or Firefox)
- ✅ Visit the actual deployed URL (not localhost)
- ✅ Ensure icons exist in `web/public/`
- ✅ Check manifest is accessible at `/dreams-manifest.json`

### App not loading offline?
- ✅ First visit must be online to cache resources
- ✅ Check service worker installed (Safari Dev Tools)
- ✅ Try force-refreshing the page
- ✅ Clear Safari cache and revisit

### Icons not showing?
- ✅ Verify `dream-icon-192.png` and `dream-icon-512.png` exist
- ✅ Check file names match exactly (case-sensitive)
- ✅ Clear Safari cache
- ✅ Delete and reinstall the app

### Dreams not syncing after going back online?
- ✅ Open the app (background sync requires app to be open)
- ✅ Check browser console for sync errors
- ✅ Verify API endpoint is accessible
- ✅ Check network connection is stable

### Updates not appearing?
- ✅ Service worker updates in background (may take time)
- ✅ Close and reopen the app
- ✅ Force refresh (pull down to refresh)
- ✅ Delete and reinstall if persistent

## 💡 Usage Tips

### For Best Results
1. **Install on home screen** for quick access
2. **Log dreams immediately** upon waking (best recall)
3. **Use offline mode** if logging in bed without WiFi
4. **Enable notifications** (if implemented) for daily reminders
5. **Backup regularly** by exporting dream data

### Privacy & Security
- Dreams stored locally in browser cache
- Offline queue encrypted by browser
- No data shared without your permission
- Delete app to remove all local data

### Battery & Storage
- Minimal battery impact (service worker is efficient)
- Cache size: ~5-10MB (depends on dream count)
- Automatically cleans old cache versions
- Request persistent storage to prevent clearing

## 🌟 Advanced Features

### Install Both Apps
You can install both the main dashboard and Dream Journal as separate apps:
- Main app: `https://your-url.com/` → "Discord Dashboard"
- Dream Journal: `https://your-url.com/dreams` → "Dream Journal"

Each has its own icon, manifest, and can run independently!

### Share Dreams
Use the native share API (if implemented):
1. Open a dream
2. Tap share icon
3. Choose sharing method
4. Share as text or link

### Export Data
Future feature: Export all dreams as JSON or PDF for backup.

## 📱 Platform Support

### iOS (iPhone/iPad)
✅ Full PWA support  
✅ Add to Home Screen  
✅ Standalone mode  
✅ Service worker  
✅ Offline functionality  

### Android
✅ Full PWA support  
✅ Install prompt  
✅ Standalone mode  
✅ Service worker  
✅ Background sync  

### Desktop
✅ Chrome/Edge: Install as app  
✅ Safari: Bookmark for quick access  
✅ Firefox: Limited PWA support  

## 🎉 Enjoy Your Dream Journal!

Your dreams are now just a tap away. Sweet dreams! 🌙✨

---

**Need help?** Check the browser console for detailed logs or contact support.
