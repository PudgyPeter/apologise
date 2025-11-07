# Quick Setup: Dream Journal PWA

Follow these steps to enable PWA support for your Dream Journal:

## 1️⃣ Generate Icons (Required)

Open in your browser:
```
web/public/generate-dream-icons.html
```

Download both icons and save them in `web/public/` as:
- `dream-icon-192.png`
- `dream-icon-512.png`

## 2️⃣ Build the App

```bash
cd web
npm run build
```

## 3️⃣ Test Locally

Start your server:
```bash
python web/api.py
```

Visit: `http://localhost:5000/dreams`

## 4️⃣ Deploy

Push to GitHub and deploy to your hosting platform.

## 5️⃣ Install on Phone

### iPhone (Safari)
1. Visit `https://your-app.com/dreams`
2. Tap Share → "Add to Home Screen"
3. Enjoy! 🌙

### Android (Chrome)
1. Visit `https://your-app.com/dreams`
2. Tap the install prompt or Menu → "Install app"
3. Enjoy! 🌙

## ✅ Features Enabled

- ✨ Standalone app mode
- 📴 Offline functionality
- 🔄 Background sync
- 💾 Persistent storage
- ⚡ Fast loading (cached)
- 🎨 Custom moon icon
- 🌙 Purple theme

## 📱 Multiple Apps

You can install:
1. **Main Dashboard** from `/` 
2. **Dream Journal** from `/dreams`
3. **Hospitality Stats** from `/hospitality`

Each as a separate app on your home screen!

## 🆘 Troubleshooting

**Icons not showing?**
- Make sure you generated and saved both PNG files
- Check they're named exactly: `dream-icon-192.png` and `dream-icon-512.png`
- Clear browser cache and rebuild

**Can't install?**
- Use Safari on iPhone (not Chrome)
- Use Chrome on Android
- Make sure you're on the deployed URL (not localhost)

**Not working offline?**
- Visit the app online first to cache resources
- Check service worker is registered (browser dev tools)

---

For detailed documentation, see `DREAM_JOURNAL_PWA_SETUP.md`
