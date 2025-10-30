# Split Sections - Discord & Hospitality

## Overview
The application has been split into two completely separate sections to allow sharing the hospitality stats without exposing Discord logs.

## Routes

### 1. Discord Dashboard (Private)
- **URL**: `https://yourdomain.com/`
- **Access**: Main dashboard with Discord logs, search, and live feed
- **Features**:
  - View daily Discord logs
  - Search across all logs
  - Live message feed
  - Download and manage custom logs

### 2. Hospitality Stats (Shareable)
- **URL**: `https://yourdomain.com/hospitality`
- **Access**: Public-facing hospitality statistics dashboard
- **Features**:
  - Add daily MIV and average spend entries
  - View analytics by meal period (lunch/dinner)
  - Staff performance tracking
  - Day of week analysis
  - Edit and delete entries

## How to Share

### Share Hospitality Stats Only
Simply share this URL with staff or management:
```
https://yourdomain.com/hospitality
```

This URL provides **NO ACCESS** to Discord logs, search, or live feed. Users can only:
- View hospitality statistics
- Add new entries
- Edit/delete existing entries

### Keep Discord Dashboard Private
The main dashboard at `https://yourdomain.com/` contains all Discord-related features and should remain private.

## Technical Implementation

### File Structure
```
web/src/
├── App.js                           # Main router
├── components/
│   ├── DiscordDashboard.js         # Discord logs component
│   └── HospitalityStats.js         # Hospitality stats component
└── App.css                          # Shared styles
```

### API Endpoints
Both sections use the same backend API:

**Discord Endpoints** (used by `/`):
- `GET /api/logs` - List all logs
- `GET /api/logs/:filename` - Get log content
- `POST /api/search` - Search logs
- `GET /api/live` - Get live messages
- `GET /api/stats` - Get Discord stats

**Hospitality Endpoints** (used by `/hospitality`):
- `GET /api/hospitality/stats` - Get all entries
- `POST /api/hospitality/stats` - Add new entry
- `PUT /api/hospitality/stats/:id` - Update entry
- `DELETE /api/hospitality/stats/:id` - Delete entry
- `GET /api/hospitality/analytics` - Get calculated analytics

## Future Enhancements

### Optional: Add Password Protection
If you want to add password protection to the Discord dashboard:

1. Add a simple password check in `DiscordDashboard.js`
2. Store password in environment variable
3. Use localStorage to persist authentication

### Optional: Separate Deployments
For maximum security, you could deploy these as two completely separate apps:
- Discord Dashboard on a private subdomain
- Hospitality Stats on a public subdomain

## Development

### Install Dependencies
```bash
cd web
npm install
```

### Run Development Server
```bash
npm start
```

Then access:
- Discord Dashboard: http://localhost:3000/
- Hospitality Stats: http://localhost:3000/hospitality

### Build for Production
```bash
npm run build
```

## Notes
- Both sections share the same dark mode preference (stored in localStorage)
- The backend API remains unchanged
- All existing functionality is preserved
- No data migration required
