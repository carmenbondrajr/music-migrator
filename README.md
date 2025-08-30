# Spotify to YouTube Music Migrator

Migrate your owned playlists from one tech behemoth to another. Because a lesser of two evils is still less evil.  

## ✨ Features

- 🎵 **Complete Migration**: Migrate all playlists + liked songs
- 🔄 **Idempotent & Track-Aware**: Only adds missing tracks, never duplicates
- 📦 **Chunked Processing**: Processes tracks in batches with real-time progress
- 🎨 **Beautiful UI**: Rich terminal output with progress bars and track counters
- 📊 **Detailed Reporting**: Migration summary and failed tracks report
- 🏷️ **Smart Naming**: "Liked Songs - Spot" and "Spot [Name]" prefixes
- 💾 **Persistent State**: Resumes where it left off if interrupted
- 🔍 **Smart Search**: Matches tracks by name, artist, and album

## 🚀 Quick Start

```bash
# 1. Setup project
make setup

# 2. Add your Spotify credentials to .env
# 3. Add YouTube OAuth credentials to .env (see below)

# 4. Setup YouTube Music authentication 
make ytmusic-setup-oauth

# 5. Run migration
make migrate
```

## 🛠️ Detailed Setup

### 1. Install Dependencies
```bash
make install
# or: pip install -r requirements.txt
```

### 2. Configure Spotify API
1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
2. Create a new app
3. Add redirect URI: `http://127.0.0.1:8888/callback`
4. Copy `.env.example` to `.env` and add your credentials:

```env
SPOTIFY_CLIENT_ID=your_spotify_client_id_here
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret_here
```

### 3. Configure YouTube Music OAuth
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create project → Enable "YouTube Data API v3"
3. Create OAuth 2.0 credentials (select "TVs and Limited Input devices")
4. Add credentials to `.env`:

```env
YTMUSIC_OAUTH_CLIENT_ID=your_youtube_client_id_here
YTMUSIC_OAUTH_SECRET=your_youtube_client_secret_here
```

5. Run automated OAuth setup:
```bash
make ytmusic-setup-oauth
```

This automatically uses your `.env` credentials 🎉

### 4. Validate Setup
```bash
make validate
```

## 🎯 Migration Process

The migrator uses **intelligent chunked processing**:

1. **Fetches** your Spotify playlists and liked songs
2. **Processes in chunks** of 200 tracks at a time
3. **Shows real-time progress**: "Processing tracks 1-200 of 3079 (6.7%)"
4. **Compares with existing** YouTube Music playlist tracks
5. **Only adds missing tracks** - never duplicates
6. **Reports progress**: "Added 45 tracks from this chunk. Total added: 127"
7. **Saves state** after each chunk for resilience

## 📋 Available Commands

### Make Commands (Recommended)
```bash
make migrate              # Run migration
make ytmusic-setup-oauth  # Setup YouTube OAuth (automated)
make setup-oauth          # Setup YouTube OAuth (interactive)
make validate             # Check configuration
make status              # Show migration status
make clean               # Reset migration state
make retry-failed        # Retry failed tracks
```

### Python Commands
```bash
python main.py migrate        # Run migration  
python main.py setup-oauth    # Setup YouTube OAuth
python main.py validate       # Validate setup
```

## 🔄 Key Improvements

### Track-Aware Idempotency
- ✅ Compares existing YouTube playlist tracks vs Spotify tracks
- ✅ Only migrates missing tracks (not entire playlists)
- ✅ Perfect for resuming interrupted large migrations

### Chunked Processing  
- ✅ Processes 200 tracks → writes to YouTube → repeats
- ✅ Real-time progress: "1200 of 3000 tracks migrated (40%)"
- ✅ More resilient to interruptions
- ✅ Tracks appear in YouTube Music every few minutes

### Enhanced Track Status
- ✅ **found** - New track found and added
- 📋 **exists** - Track already in YouTube playlist  
- 🔄 **cached** - Using previously found track
- ⏭️ **skipped** - Previously failed track
- ❌ **not_found** - Track not available on YouTube Music

## 📁 Project Structure

```
music-migrator/
├── .env                    # Your credentials (gitignored)
├── .env.example           # Template  
├── Makefile              # Convenient commands
├── main.py               # CLI entry point
├── src/                  # Source code
└── cache/                # Migration state (gitignored)
    ├── migration_state.json    # Progress tracking
    └── failed_tracks.json      # Failed tracks report
```

## 🔍 Troubleshooting

### Authentication Issues
```bash
make validate  # Check setup
make ytmusic-setup-oauth  # Re-auth YouTube Music
```

### Migration Issues  
```bash
make status        # Check progress
make clean         # Reset state (if needed)
make retry-failed  # Retry failed tracks
```

### Large Playlists
- The chunked processing handles 3000+ track playlists efficiently
- Shows progress: "Processing tracks 1001-1200 of 3079 (39.0%)"
- Interruptions only lose current chunk (max 200 tracks)

## 🎯 Example Output

```
🔐 Setting up YouTube Music OAuth from .env...
✅ OAuth setup complete! oauth.json created successfully.

🚀 Starting migration...
📁 Playlist: Liked Songs - Spot
ℹ️  Processing 3079 tracks in chunks of 200...
ℹ️  Processing tracks 1-200 of 3079 (6.5%)
ℹ️  Found 47 existing tracks in Liked Songs - Spot
  📋 Track Name - Artist (exists)
  ✅ New Track - Artist (found)  
  🔄 Cached Track - Artist (cached)
✅ Added batch of 50 tracks to Liked Songs - Spot
ℹ️  Added 153 tracks from this chunk. Total added: 153

ℹ️  Processing tracks 201-400 of 3079 (13.0%)
...
```

## 📝 Notes

- **Safe for Public Repos**: All sensitive data in gitignored `.env` and `oauth.json`
- **YouTube Quotas**: Respects API limits with 0.1s delays between searches
- **Resume Friendly**: Interrupted migrations resume perfectly
- **No Duplicates**: Track-aware logic prevents duplicate additions
