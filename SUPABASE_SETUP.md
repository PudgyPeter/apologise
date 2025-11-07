# Supabase Setup Guide for Dream Journal

This guide will help you set up Supabase for cloud-based dream storage with automatic cross-device syncing.

## Why Supabase?

- ✅ **Cloud Storage**: Dreams stored in PostgreSQL database
- ✅ **Cross-Device Sync**: Access from any device automatically
- ✅ **Real-time Updates**: See changes instantly across devices
- ✅ **Offline Support**: Works with PWA offline mode
- ✅ **Free Tier**: 500MB database, 2GB bandwidth/month
- ✅ **Secure**: Row-level security policies
- ✅ **Scalable**: Grows with your needs

## Step 1: Create Supabase Project

1. Go to [supabase.com](https://supabase.com)
2. Click **"Start your project"** and sign up (free)
3. Click **"New Project"**
4. Fill in:
   - **Name**: `dream-journal` (or your choice)
   - **Database Password**: Create a strong password (save it!)
   - **Region**: Choose closest to you
   - **Pricing Plan**: Free
5. Click **"Create new project"**
6. Wait 2-3 minutes for setup to complete

## Step 2: Create Dreams Table

1. In your Supabase project, click **"SQL Editor"** in the left sidebar
2. Click **"New Query"**
3. Copy and paste this SQL:

```sql
-- Create dreams table
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

-- Create index on date for faster queries
CREATE INDEX dreams_date_idx ON dreams(date DESC);

-- Create index on created_at for sorting
CREATE INDEX dreams_created_at_idx ON dreams(created_at DESC);

-- Enable Row Level Security (RLS)
ALTER TABLE dreams ENABLE ROW LEVEL SECURITY;

-- Create policy to allow all operations (adjust for authentication later)
CREATE POLICY "Allow all operations for now" ON dreams
  FOR ALL
  USING (true)
  WITH CHECK (true);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update updated_at
CREATE TRIGGER update_dreams_updated_at
  BEFORE UPDATE ON dreams
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();
```

4. Click **"Run"** (or press Ctrl+Enter)
5. You should see "Success. No rows returned"

## Step 3: Get API Credentials

1. Click **"Settings"** (gear icon) in the left sidebar
2. Click **"API"** under Project Settings
3. Copy these values (you'll need them):
   - **Project URL**: `https://xxxxx.supabase.co`
   - **anon public key**: `eyJhbGc...` (long string)

## Step 4: Configure Your App

### For Local Development

1. Create `.env` file in the `web/` folder:

```bash
# web/.env
REACT_APP_SUPABASE_URL=https://xxxxx.supabase.co
REACT_APP_SUPABASE_ANON_KEY=eyJhbGc...your-anon-key...
```

2. Add `.env` to `.gitignore` (if not already):

```bash
# In web/.gitignore
.env
.env.local
.env.development
.env.production
```

### For Production (Railway/Heroku)

Add environment variables in your hosting platform:

**Railway:**
1. Go to your project → Variables
2. Add:
   - `REACT_APP_SUPABASE_URL` = `https://xxxxx.supabase.co`
   - `REACT_APP_SUPABASE_ANON_KEY` = `your-anon-key`

**Heroku:**
```bash
heroku config:set REACT_APP_SUPABASE_URL=https://xxxxx.supabase.co
heroku config:set REACT_APP_SUPABASE_ANON_KEY=your-anon-key
```

## Step 5: Install Dependencies

```bash
cd web
npm install
```

This will install `@supabase/supabase-js` that was added to package.json.

## Step 6: Test the Connection

1. Start your development server:
```bash
npm start
```

2. Navigate to `/dreams`
3. Try creating a dream
4. Check Supabase dashboard → Table Editor → dreams
5. You should see your dream entry!

## Step 7: Enable Real-time (Optional)

For instant sync across devices:

1. In Supabase dashboard, go to **Database** → **Replication**
2. Find the `dreams` table
3. Toggle **"Enable Realtime"** to ON
4. Click **"Save"**

Now changes will appear instantly on all connected devices!

## Database Schema

```
dreams
├── id (bigserial, primary key)
├── title (text, required)
├── content (text, required)
├── date (date, required)
├── tags (text[], array of strings)
├── keywords (jsonb, object with word frequencies)
├── created_at (timestamptz, auto)
└── updated_at (timestamptz, auto)
```

## Security Considerations

### Current Setup (Development)
- **RLS Enabled**: Row Level Security is on
- **Public Access**: Anyone can read/write (for testing)
- ⚠️ **Not recommended for production**

### For Production (Add Authentication)

1. **Enable Supabase Auth**:
```sql
-- Update policy to require authentication
DROP POLICY "Allow all operations for now" ON dreams;

CREATE POLICY "Users can manage their own dreams" ON dreams
  FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);
```

2. **Add user_id column**:
```sql
ALTER TABLE dreams ADD COLUMN user_id UUID REFERENCES auth.users(id);
CREATE INDEX dreams_user_id_idx ON dreams(user_id);
```

3. **Implement authentication in your app** (see Supabase Auth docs)

## Migration from JSON File

To migrate existing dreams from `data/dreams.json`:

1. Export your dreams:
```bash
cat data/dreams.json
```

2. In Supabase SQL Editor:
```sql
-- Insert dreams (adjust values)
INSERT INTO dreams (title, content, date, tags, keywords, created_at)
VALUES 
  ('Dream Title', 'Dream content...', '2024-11-07', 
   ARRAY['tag1', 'tag2'], 
   '{"flying": 3, "sky": 2}'::jsonb,
   '2024-11-07T14:30:00Z');
```

Or use the Table Editor to manually add dreams.

## Backup & Export

### Backup Dreams
```sql
-- In SQL Editor
SELECT * FROM dreams ORDER BY created_at DESC;
```

Copy results and save as JSON.

### Automated Backups
Supabase automatically backs up your database daily (free tier: 7 days retention).

## Troubleshooting

### "Failed to fetch dreams"
- Check Supabase project is running (green status)
- Verify API credentials in `.env`
- Check browser console for errors
- Ensure RLS policy allows access

### "Invalid API key"
- Regenerate anon key in Supabase dashboard
- Update `.env` file
- Restart development server

### Dreams not syncing across devices
- Check internet connection
- Verify both devices use same Supabase project
- Enable real-time replication
- Check browser console for errors

### Real-time not working
- Enable Realtime in Database → Replication
- Check subscription in browser console
- Verify network allows WebSocket connections

## Cost Estimation

**Free Tier Limits:**
- 500MB database storage
- 2GB bandwidth/month
- 50,000 monthly active users
- Unlimited API requests

**Estimated Usage (1 user, 1 dream/day):**
- Storage: ~1KB per dream = 365KB/year
- Bandwidth: ~10KB per sync = ~300KB/month
- **Well within free tier!** ✅

## Next Steps

1. ✅ Set up Supabase project
2. ✅ Create dreams table
3. ✅ Configure environment variables
4. ✅ Install dependencies
5. ✅ Test dream creation
6. ✅ Enable real-time (optional)
7. 🔒 Add authentication (recommended for production)
8. 📊 Set up analytics (optional)

Your dreams are now stored in the cloud and accessible from any device! 🌙✨
