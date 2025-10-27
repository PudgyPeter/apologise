# 🚀 Railway Deployment Guide

## Prerequisites
- GitHub account
- Railway account (sign up at [railway.app](https://railway.app))
- Your code pushed to GitHub

## Step-by-Step Deployment

### 1. Push Code to GitHub

```bash
cd c:\Users\PenderITAdmin\Documents\GitHub\apologise
git add .
git commit -m "Add web dashboard"
git push origin main
```

### 2. Create New Railway Service

1. Go to [railway.app](https://railway.app)
2. Click **"New Project"** or open your existing project
3. Click **"+ New"** → **"GitHub Repo"**
4. Select your `apologise` repository
5. Railway will detect the web folder automatically

### 3. Configure the Service

#### Set Root Directory
1. In Railway, click on your new service
2. Go to **Settings** → **Service**
3. Set **Root Directory** to: `web`
4. Click **Save**

#### Add Environment Variables
1. Go to **Variables** tab
2. Add these variables:
   - `PORT` = `8080` (or any port)
   - `FLASK_ENV` = `production`

#### Mount the Data Volume
1. Go to **Settings** → **Volumes**
2. Click **"+ New Volume"**
3. Set **Mount Path** to: `/app/data`
4. Click **Add**

**IMPORTANT:** Make sure this is the SAME volume your Discord bot uses!

### 4. Deploy

Railway will automatically:
1. Install Node.js dependencies (`npm install`)
2. Build the React app (`npm run build`)
3. Install Python dependencies (`pip install -r requirements.txt`)
4. Start the server with Gunicorn

### 5. Access Your Dashboard

1. Go to **Settings** → **Networking**
2. Click **"Generate Domain"**
3. Your dashboard will be available at: `https://your-service.up.railway.app`

## Sharing Data with Discord Bot

To ensure both services use the same data:

### Option A: Same Volume (Recommended)
1. Both services should mount the same volume at `/app/data`
2. In Railway, when creating the volume, use the same volume for both services

### Option B: Separate Services, Shared Volume
1. Create a volume in your Railway project
2. Mount it to both the bot service and web service
3. Both will read/write to the same log files

## Environment Variables Summary

**Web Dashboard Service:**
```
PORT=8080
FLASK_ENV=production
```

**Discord Bot Service:**
```
TOKEN=your_discord_token
```

## Updating the Dashboard

Just push to GitHub:
```bash
git add .
git commit -m "Update dashboard"
git push
```

Railway will automatically rebuild and redeploy!

## Troubleshooting

### Build Fails
- Check the build logs in Railway
- Ensure `nixpacks.toml` is in the web folder
- Verify Node.js and Python versions are compatible

### No Logs Showing
- Verify the volume is mounted at `/app/data`
- Check that the Discord bot is writing to the same volume
- Look at the API logs: `/api/logs` endpoint

### 502 Bad Gateway
- Check that Gunicorn is starting correctly
- Verify PORT environment variable is set
- Check Railway logs for errors

## Local Development

To test locally before deploying:

```bash
# Build React
npm run build

# Run Flask (serves both API and React)
python api.py
```

Visit `http://localhost:5000` to see the production build.
