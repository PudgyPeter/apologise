# Supabase Quick Start - Dream Journal

Get your Dream Journal running with cloud storage in 5 minutes!

## ⚡ Quick Setup

### 1. Create Supabase Project (2 min)
1. Go to [supabase.com](https://supabase.com) and sign up
2. Click "New Project"
3. Name it `dream-journal`, set a password, choose region
4. Wait for project to be ready

### 2. Create Database Table (1 min)
1. In Supabase dashboard, click **SQL Editor**
2. Click **New Query**
3. Paste this:

```sql
CREATE TABLE dreams (
  id BIGSERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  date DATE NOT NULL,
  tags TEXT[] DEFAULT '{}',
  keywords JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX dreams_date_idx ON dreams(date DESC);

ALTER TABLE dreams ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all operations" ON dreams
  FOR ALL USING (true) WITH CHECK (true);

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_dreams_updated_at
  BEFORE UPDATE ON dreams
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();
```

4. Click **Run**

### 3. Get API Keys (30 sec)
1. Click **Settings** (gear icon) → **API**
2. Copy:
   - **Project URL**: `https://xxxxx.supabase.co`
   - **anon public key**: `eyJhbGc...`

### 4. Configure Your App (1 min)
Create `web/.env` file:

```bash
REACT_APP_SUPABASE_URL=https://xxxxx.supabase.co
REACT_APP_SUPABASE_ANON_KEY=eyJhbGc...your-key...
```

### 5. Install & Run (1 min)
```bash
cd web
npm install
npm start
```

Visit `http://localhost:3000/dreams` and start logging dreams! 🌙

## ✨ What You Get

- ☁️ **Cloud Storage** - Dreams saved to PostgreSQL
- 🔄 **Real-time Sync** - Changes appear instantly on all devices
- 📱 **Cross-Device** - Access from phone, tablet, desktop
- 🔒 **Secure** - Row-level security enabled
- 💾 **Automatic Backups** - Daily backups included
- 🆓 **Free Tier** - 500MB database, plenty for dreams!

## 🚀 Enable Real-time (Optional)

For instant sync across devices:

1. In Supabase: **Database** → **Replication**
2. Find `dreams` table
3. Toggle **"Enable Realtime"** ON
4. Save

Now when you create a dream on your phone, it appears instantly on your laptop! ✨

## 📱 Deploy to Production

### Railway
```bash
# Add environment variables in Railway dashboard:
REACT_APP_SUPABASE_URL=https://xxxxx.supabase.co
REACT_APP_SUPABASE_ANON_KEY=your-key
```

### Heroku
```bash
heroku config:set REACT_APP_SUPABASE_URL=https://xxxxx.supabase.co
heroku config:set REACT_APP_SUPABASE_ANON_KEY=your-key
```

## 🔍 Verify It's Working

1. Create a dream in your app
2. Go to Supabase → **Table Editor** → `dreams`
3. You should see your dream entry!
4. Open app on another device → dream appears there too! 🎉

## 💡 Tips

- **Sync Status**: Green "Synced" = all saved to cloud
- **Offline Mode**: Create dreams offline, they sync when back online
- **Multiple Devices**: Install PWA on phone + tablet + desktop
- **Backup**: Supabase backs up daily automatically

## 🆘 Troubleshooting

**"Failed to fetch dreams"**
- Check `.env` file exists in `web/` folder
- Verify API keys are correct
- Restart dev server (`npm start`)

**Dreams not syncing**
- Enable Realtime in Supabase dashboard
- Check internet connection
- Look for sync status in app header

## 📚 Full Documentation

- **Complete Setup**: `SUPABASE_SETUP.md`
- **Dream Journal Guide**: `DREAM_JOURNAL_README.md`
- **PWA Setup**: `DREAM_JOURNAL_PWA_SETUP.md`

---

That's it! Your dreams are now in the cloud! 🌙✨
