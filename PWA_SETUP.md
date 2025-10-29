# PWA Setup Guide - Install on iPhone

Your dashboard is now a Progressive Web App (PWA) that can be installed on your iPhone like a native app!

## Step 1: Generate App Icons

Before deploying, you need to create the app icons:

1. Open `web/public/generate-icons.html` in your browser
2. Click "Download 192x192" and save as `icon-192.png`
3. Click "Download 512x512" and save as `icon-512.png`
4. Move both PNG files to `web/public/` folder

## Step 2: Build and Deploy

```bash
cd web
npm run build
```

Then push to GitHub and deploy to Railway.

## Step 3: Install on iPhone

1. **Open Safari** on your iPhone (must use Safari, not Chrome)
2. **Navigate to your Railway URL** (e.g., https://your-app.up.railway.app)
3. **Tap the Share button** (square with arrow pointing up at bottom of screen)
4. **Scroll down** and tap **"Add to Home Screen"**
5. **Edit the name** if you want (default: "Logs & Stats")
6. **Tap "Add"** in the top right

## What You Get

✅ **App icon** on your home screen  
✅ **Full-screen experience** (no Safari UI)  
✅ **Offline functionality** (caches data)  
✅ **Fast loading** (service worker caching)  
✅ **iPhone notch support** (safe area insets)  
✅ **Optimized for touch** (larger buttons, no zoom on input)

## Features

### Offline Mode
- View previously loaded logs even without internet
- Analytics data is cached
- Form submissions queue when offline (sync when back online)

### Mobile Optimizations
- Responsive layout for small screens
- Touch-friendly buttons (44px minimum)
- No auto-zoom on input fields
- Smooth scrolling
- Swipeable tabs

### iPhone Specific
- Works with iPhone notch/Dynamic Island
- Respects safe areas
- Status bar integration
- Standalone app mode

## Troubleshooting

**"Add to Home Screen" not showing?**
- Make sure you're using Safari (not Chrome or other browsers)
- Check that you're on the actual website (not localhost)
- Ensure the manifest.json is accessible

**App not loading offline?**
- First visit must be online to cache resources
- Service worker needs to install (check browser console)

**Icons not showing?**
- Make sure icon-192.png and icon-512.png are in web/public/
- Clear Safari cache and try again

## Usage Tips

### For Hospitality Stats
- Add to home screen for quick access during shifts
- Enter stats immediately after closing
- Works offline if WiFi is spotty
- Data syncs when connection restored

### For Discord Logs
- Check logs on-the-go
- Search works offline with cached data
- Live feed updates when app is open

## Updating the App

When you deploy updates:
1. Users will get the new version automatically
2. Service worker updates in background
3. Refresh the app to see changes
4. No need to reinstall

Enjoy your native-like app experience! 📱✨
