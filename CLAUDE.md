# CLAUDE.md - Context for Future Sessions

This document provides essential context for Claude Code sessions working on this Spotify to YouTube Music migrator project.

## 🏗️ Architecture Overview

### Core Components
- **`src/migrator.py`** - Main migration logic with chunked processing
- **`src/spotify_client.py`** - Spotify API wrapper with pagination
- **`src/youtube_client.py`** - YouTube Music API wrapper with authentication
- **`src/config.py`** - Configuration management from `.env`  
- **`src/ui.py`** - Rich console UI with progress tracking
- **`main.py`** - CLI entry point with argument parsing
- **`Makefile`** - Convenient commands for common operations

### Key Design Patterns
- **Chunked Processing**: Processes tracks in batches of 200 for better UX and resilience
- **Track-Aware Caching**: Individual track status tracking, not just playlist-level
- **Idempotent Operations**: Safe to run multiple times, only adds missing tracks
- **State Persistence**: Progress saved after each chunk in `cache/migration_state.json`

## 🔄 Recent Major Changes (January 2025)

### Chunked Processing Implementation
**Problem**: Original design processed all tracks first, then batch-wrote to YouTube Music. Users saw no progress for hours and lost all work if interrupted during search phase.

**Solution**: Implemented chunked processing in `_process_tracks_in_chunks()`:
- Process 200 tracks → search → batch add → save state → repeat
- Real-time progress: "Processing tracks 1-200 of 3079 (6.7%)"
- Resilient interruptions (max 200 tracks lost)
- Tracks appear in YouTube Music every few minutes

### Track-Aware Idempotency  
**Problem**: Cache tracked completed playlists, but not individual tracks. Partial migrations were all-or-nothing.

**Solution**: Enhanced cache logic to compare existing YouTube playlist tracks:
1. Fetch existing YouTube playlist tracks
2. Compare with Spotify tracks  
3. Only migrate missing tracks
4. New track statuses: exists 📋, cached 🔄, skipped ⏭️

### Automated YouTube OAuth Setup
**Problem**: Users had to copy-paste Client ID/Secret every time during `ytmusicapi oauth`.

**Solution**: Added `make ytmusic-setup-oauth` that:
- Reads `YTMUSIC_OAUTH_CLIENT_ID` and `YTMUSIC_OAUTH_SECRET` from `.env`
- Automatically passes them to `ytmusicapi oauth --client-id --client-secret`
- No more copy-pasting!

## 🏃‍♂️ Common Tasks & Commands

### Development Commands
```bash
make validate        # Check setup
make status          # Show migration progress
make clean           # Reset migration state  
make test           # Basic validation tests
```

### Authentication
- **Setup**: `make ytmusic-setup-oauth` (automated)
- **Interactive**: `make setup-oauth` (manual)
- **Files**: `.env` (credentials), `oauth.json` (tokens)

### Testing Migration Logic
- **Test pagination**: `make test-pagination`  
- **Reset liked songs**: `make reset-liked`
- **Retry failed tracks**: `make retry-failed`

## 📊 Cache Structure

### `cache/migration_state.json`
```json
{
  "playlists": {
    "spotify_playlist_id": {
      "youtube_id": "PL-xxx",
      "name": "Spot Playlist Name"  
    }
  },
  "tracks": {
    "playlist_id:track_id": {
      "status": "found|not_found",
      "youtube_video_id": "xxx",
      "timestamp": 1234567890
    }
  },
  "completed_playlists": ["playlist_id1", "playlist_id2"]
}
```

### Key Cache Methods
- `MigrationState.get_track_status(track_id, playlist_id)` - Get cached track
- `MigrationState.mark_track_migrated()` - Cache track result
- `MigrationState.is_playlist_completed()` - Check if playlist done

## 🔧 Environment Variables

### Required in `.env`
```env
# Spotify API
SPOTIFY_CLIENT_ID=xxx
SPOTIFY_CLIENT_SECRET=xxx

# YouTube Music OAuth (new requirement as of Nov 2024)
YTMUSIC_OAUTH_CLIENT_ID=xxx
YTMUSIC_OAUTH_SECRET=xxx
```

### Optional
```env
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback  # Default
YTMUSIC_OAUTH_JSON=oauth.json                        # Default
```

## 🎯 Migration Flow

### High-Level Process
1. **Initialize clients** - Spotify + YouTube Music authentication
2. **Fetch playlists** - Get user's Spotify playlists + liked songs  
3. **For each playlist**:
   - Create/find YouTube Music playlist
   - Fetch existing YouTube tracks (for deduplication)
   - Process Spotify tracks in chunks of 200:
     - Search on YouTube Music
     - Batch add found tracks (50 at a time)
     - Save progress after each chunk
   - Mark playlist completed

### Error Handling
- **Authentication expiry**: Graceful handling with re-auth instructions
- **API failures**: Detailed error messages, resume capability  
- **Track not found**: Logged to `failed_tracks.json` report
- **Interruptions**: State saved after each chunk

## 🚨 Important Implementation Details

### Playlist Naming Convention
- **Liked Songs**: "Liked Songs - Spot" (changed from "Spot Liked Songs")
- **Regular playlists**: "Spot {original_name}"

### Track Status Icons & Colors
```python
# In src/ui.py
'found': '✅',      # dim green
'not_found': '❌',  # dim red  
'exists': '📋',     # dim yellow
'cached': '🔄',     # dim cyan
'skipped': '⏭️'     # dim magenta
```

### YouTube Music API Quirks  
- **November 2024 change**: Now requires Google Cloud Console OAuth credentials
- **Batch limits**: Add songs in batches of 50 max
- **Rate limiting**: 0.1s delay between searches
- **Authentication**: Uses `ytmusicapi` with OAuth flow

### Cache Clearing for Liked Songs
When users want fresh start for Liked Songs:
```python
# Remove liked_songs entries from all cache sections
if 'liked_songs' in cache.get('playlists', {}):
    del cache['playlists']['liked_songs']
# Remove completed status  
if 'liked_songs' in cache.get('completed_playlists', []):
    cache['completed_playlists'].remove('liked_songs')
# Remove all track cache entries
tracks_to_remove = [key for key in cache.get('tracks', {}).keys() 
                   if key.startswith('liked_songs:')]
for track_key in tracks_to_remove:
    del cache['tracks'][track_key]
```

## 🔒 Security & Public Repository

### Gitignored Files
- `.env` - All credentials
- `oauth.json` - OAuth tokens  
- `cache/` - Migration state (may contain personal data)

### Clean for Public
- ✅ No hardcoded secrets or API keys
- ✅ No personal information in code
- ✅ All sensitive data via environment variables
- ✅ Debug code is intentional user feedback, not leftover debug prints

## 🧪 Testing & Validation

### Before Major Changes
1. `python -m py_compile src/*.py` - Syntax check
2. `make test` - Basic imports and initialization  
3. `make validate` - Check configuration
4. Test with small playlist first

### Common Issues
- **Import errors**: Check Python path in modules
- **OAuth expiry**: Clear tokens and re-authenticate
- **Large playlists**: Chunked processing handles 3000+ tracks well
- **API quotas**: Built-in rate limiting with 0.1s delays

## 📝 Code Style & Patterns

### Consistent with Existing Code
- Use existing `self.ui.print_*()` methods for output
- Follow existing error handling patterns
- Cache operations use `self.state.*()` methods
- Progress tracking via Rich console library

### Avoid
- Direct print() statements (use UI methods)
- Hardcoded credentials or personal data
- Breaking existing API contracts
- Complex state mutations without persistence

## 🎯 Future Enhancement Areas

### Potential Improvements  
- **Parallel processing** - Multiple API calls concurrently
- **Smart retry logic** - Exponential backoff for failed tracks
- **Playlist organization** - Folder support if YouTube Music adds it
- **Advanced matching** - Fuzzy search, alternative versions
- **Incremental sync** - Detect new Spotify additions

### Architecture Considerations
- Keep chunked processing pattern
- Maintain track-level granularity in cache
- Preserve idempotent behavior
- Consider API quota implications

---

## 💡 Quick References

**Lint & Type Check**: `npm run lint`, `npm run typecheck` (if available)
**Reset Everything**: `make clean` 
**Check Migration Status**: `make status`
**Most Common Debug**: Check `.env` file and `make validate`

This context should help you quickly understand the project structure, recent changes, and common patterns when working on future enhancements or bug fixes.