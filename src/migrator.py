import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Set
from .spotify_client import SpotifyClient
from .youtube_client import YouTubeClient
from .ui import MigratorUI
from .config import config

class MigrationState:
    def __init__(self, cache_file: Path):
        self.cache_file = cache_file
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        
        return {
            'playlists': {},
            'tracks': {},
            'completed_playlists': set(),
            'migration_started': None
        }
    
    def save_state(self):
        config.ensure_cache_dir()
        state_to_save = self.state.copy()
        state_to_save['completed_playlists'] = list(self.state['completed_playlists'])
        
        with open(self.cache_file, 'w') as f:
            json.dump(state_to_save, f, indent=2)
    
    def is_playlist_completed(self, spotify_playlist_id: str) -> bool:
        return spotify_playlist_id in self.state['completed_playlists']
    
    def mark_playlist_completed(self, spotify_playlist_id: str):
        if isinstance(self.state['completed_playlists'], list):
            self.state['completed_playlists'] = set(self.state['completed_playlists'])
        self.state['completed_playlists'].add(spotify_playlist_id)
    
    def get_youtube_playlist_id(self, spotify_playlist_id: str) -> Optional[str]:
        return self.state['playlists'].get(spotify_playlist_id, {}).get('youtube_id')
    
    def set_youtube_playlist_id(self, spotify_playlist_id: str, youtube_playlist_id: str, name: str):
        if spotify_playlist_id not in self.state['playlists']:
            self.state['playlists'][spotify_playlist_id] = {}
        self.state['playlists'][spotify_playlist_id]['youtube_id'] = youtube_playlist_id
        self.state['playlists'][spotify_playlist_id]['name'] = name
    
    def is_track_migrated(self, spotify_track_id: str, playlist_id: str) -> bool:
        key = f"{playlist_id}:{spotify_track_id}"
        return key in self.state['tracks']
    
    def mark_track_migrated(self, spotify_track_id: str, playlist_id: str, status: str, youtube_video_id: str = None):
        key = f"{playlist_id}:{spotify_track_id}"
        self.state['tracks'][key] = {
            'status': status,
            'youtube_video_id': youtube_video_id,
            'timestamp': time.time()
        }
    
    def get_track_status(self, spotify_track_id: str, playlist_id: str) -> Optional[Dict]:
        key = f"{playlist_id}:{spotify_track_id}"
        return self.state['tracks'].get(key)

class SpotifyToYouTubeMigrator:
    def __init__(self):
        self.ui = MigratorUI()
        self.spotify = None
        self.youtube = None
        self.state = MigrationState(config.get_cache_file("migration_state.json"))
        
        self.summary = {
            'playlists_processed': 0,
            'playlists_created': 0,
            'tracks_found': 0,
            'tracks_migrated': 0,
            'tracks_failed': 0,
            'failed_tracks': [],
            'failed_tracks_file': None
        }
    
    def initialize_clients(self) -> bool:
        try:
            self.ui.print_info("Initializing Spotify client...")
            self.spotify = SpotifyClient()
            self.ui.print_success("Spotify client initialized")
        except ValueError as e:
            self.ui.print_error(f"Spotify setup failed: {e}")
            return False
        
        try:
            self.ui.print_info("Initializing YouTube Music client...")
            self.youtube = YouTubeClient()
            self.ui.print_success("YouTube Music client initialized")
        except ValueError as e:
            self.ui.print_error(f"YouTube Music setup failed: {e}")
            
            if self.ui.ask_for_oauth_setup():
                try:
                    oauth_file = YouTubeClient.setup_oauth()
                    self.ui.print_success(f"OAuth setup complete! Saved to: {oauth_file}")
                    self.youtube = YouTubeClient()
                    self.ui.print_success("YouTube Music client initialized")
                except Exception as setup_error:
                    self.ui.print_error(f"OAuth setup failed: {setup_error}")
                    return False
            else:
                return False
        
        return True
    
    def migrate_playlist(self, spotify_playlist: Dict, is_liked_songs: bool = False, force_reprocess: bool = False) -> bool:
        playlist_name = "Liked Songs - Spot" if is_liked_songs else f"Spot {spotify_playlist['name']}"
        spotify_playlist_id = spotify_playlist['id']
        
        # Handle force reprocess - temporarily remove from completed status
        was_completed = False
        if force_reprocess and self.state.is_playlist_completed(spotify_playlist_id):
            was_completed = True
            # Temporarily remove from completed list to allow reprocessing
            if isinstance(self.state.state['completed_playlists'], set):
                self.state.state['completed_playlists'].discard(spotify_playlist_id)
            elif isinstance(self.state.state['completed_playlists'], list):
                if spotify_playlist_id in self.state.state['completed_playlists']:
                    self.state.state['completed_playlists'].remove(spotify_playlist_id)
        
        if force_reprocess:
            # Force reprocess: ignore all cached data and start fresh
            self.ui.print_info("🔄 Force reprocess: Ignoring cached playlist and starting fresh...")
            
            # Clear ALL cached data for this playlist
            if spotify_playlist_id in self.state.state['playlists']:
                cached_name = self.state.state['playlists'][spotify_playlist_id].get('name', 'Unknown')
                cached_id = self.state.state['playlists'][spotify_playlist_id].get('youtube_id', 'Unknown')
                self.ui.print_info(f"🧹 Clearing cached playlist: {cached_name} (ID: {cached_id})")
                del self.state.state['playlists'][spotify_playlist_id]
            
            # Remove from completed playlists
            if isinstance(self.state.state['completed_playlists'], set):
                self.state.state['completed_playlists'].discard(spotify_playlist_id)
            elif isinstance(self.state.state['completed_playlists'], list):
                if spotify_playlist_id in self.state.state['completed_playlists']:
                    self.state.state['completed_playlists'].remove(spotify_playlist_id)
            
            # Clear track cache for this playlist  
            tracks_to_remove = [key for key in self.state.state['tracks'].keys() if key.startswith(f'{spotify_playlist_id}:')]
            for track_key in tracks_to_remove:
                del self.state.state['tracks'][track_key]
            
            if tracks_to_remove:
                self.ui.print_info(f"🧹 Cleared {len(tracks_to_remove)} cached track entries")
            
            self.state.save_state()  # Save the cleared cache immediately
            
            # Now do a fresh lookup to see if playlist exists in YouTube Music
            self.ui.print_info(f"🔍 Checking if playlist '{playlist_name}' exists in YouTube Music...")
            existing_playlist_id = self.youtube.playlist_exists(playlist_name)
        else:
            # Normal mode: use cached data
            existing_playlist_id = self.state.get_youtube_playlist_id(spotify_playlist_id)
            if not existing_playlist_id:
                existing_playlist_id = self.youtube.playlist_exists(playlist_name)
        
        if existing_playlist_id:
            self.ui.show_playlist_status(playlist_name, 'exists', 'yellow')
            youtube_playlist_id = existing_playlist_id
            
            # Verify the playlist is actually accessible
            if force_reprocess:
                try:
                    test_tracks = self.youtube.get_playlist_tracks(existing_playlist_id)
                    self.ui.print_info(f"✅ Verified playlist is accessible with {len(test_tracks)} existing tracks")
                except Exception as e:
                    self.ui.print_error(f"❌ Playlist exists but is not accessible: {e}")
                    self.ui.print_info("This might be a permissions issue or the playlist was deleted")
                    return False
        else:
            self.ui.show_playlist_status(playlist_name, 'creating', 'blue')
            description = f"Migrated from Spotify {'Liked Songs' if is_liked_songs else 'playlist'}"
            youtube_playlist_id = self.youtube.create_playlist(playlist_name, description)
            
            if not youtube_playlist_id:
                self.ui.show_playlist_status(playlist_name, 'failed', 'red')
                return False
            
            self.ui.show_playlist_status(playlist_name, 'created', 'green')
            self.ui.print_info(f"✅ Created playlist with ID: {youtube_playlist_id}")
            
            # Immediately verify the created playlist is accessible
            import time
            self.ui.print_info("⏳ Waiting 2 seconds for playlist to be fully created...")
            time.sleep(2)
            
            try:
                test_tracks = self.youtube.get_playlist_tracks(youtube_playlist_id)
                self.ui.print_info(f"✅ Verified new playlist is accessible")
            except Exception as e:
                self.ui.print_error(f"❌ Created playlist but it's not accessible: {e}")
                self.ui.print_info("This might be a YouTube Music API issue")
                return False
            
            self.summary['playlists_created'] += 1
        
        self.state.set_youtube_playlist_id(spotify_playlist_id, youtube_playlist_id, playlist_name)
        self.state.save_state()
        
        # Get existing YouTube playlist tracks to avoid duplicates
        existing_youtube_tracks = set()
        try:
            youtube_tracks = self.youtube.get_playlist_tracks(youtube_playlist_id)
            existing_youtube_tracks = {track['videoId'] for track in youtube_tracks if track.get('videoId')}
            if existing_youtube_tracks:
                self.ui.print_info(f"Found {len(existing_youtube_tracks)} existing tracks in {playlist_name}")
        except Exception as e:
            self.ui.print_warning(f"Could not fetch existing tracks for {playlist_name}: {e}")
        
        if is_liked_songs:
            print(f"🎵 Fetching Liked Songs from Spotify...")
            tracks = list(self.spotify.get_saved_tracks())
            print(f"🎵 Loaded {len(tracks)} Liked Songs from Spotify")
        else:
            print(f"🎵 Fetching playlist tracks for '{spotify_playlist['name']}'...")
            tracks = list(self.spotify.get_playlist_tracks(spotify_playlist_id))
            print(f"🎵 Loaded {len(tracks)} tracks from playlist")
        
        self.summary['tracks_found'] += len(tracks)
        
        # Process tracks in chunks for better progress feedback and resilience
        return self._process_tracks_in_chunks(
            tracks, spotify_playlist_id, youtube_playlist_id, 
            playlist_name, existing_youtube_tracks, force_reprocess
        )
        
    def _process_tracks_in_chunks(self, tracks: List[Dict], spotify_playlist_id: str, 
                                 youtube_playlist_id: str, playlist_name: str, 
                                 existing_youtube_tracks: Set[str], force_reprocess: bool = False) -> bool:
        chunk_size = 200
        total_tracks = len(tracks)
        tracks_processed = 0
        total_added = 0
        
        if force_reprocess:
            self.ui.print_info(f"🔄 Force reprocessing {total_tracks} tracks in chunks of {chunk_size}...")
            self.ui.print_info("   Re-searching all tracks but avoiding duplicates")
        else:
            self.ui.print_info(f"Processing {total_tracks} tracks in chunks of {chunk_size}...")
        
        for chunk_start in range(0, total_tracks, chunk_size):
            chunk_end = min(chunk_start + chunk_size, total_tracks)
            chunk = tracks[chunk_start:chunk_end]
            
            self.ui.print_info(f"Processing tracks {chunk_start + 1}-{chunk_end} of {total_tracks} ({((chunk_end / total_tracks) * 100):.1f}%)")
            
            # Search tracks in this chunk
            chunk_video_ids = []
            
            for track in chunk:
                tracks_processed += 1
                
                # Handle cached tracks differently based on force_reprocess
                cached_track = self.state.get_track_status(track['id'], spotify_playlist_id)
                
                if not force_reprocess and cached_track and cached_track.get('status') == 'found':
                    # Normal mode: use cached results
                    cached_video_id = cached_track.get('youtube_video_id')
                    if cached_video_id and cached_video_id in existing_youtube_tracks:
                        self.ui.show_track_status(track['name'], ', '.join(track['artists']), 'exists')
                        continue  # Skip, already exists
                    elif cached_video_id:
                        # Track was found before but not in playlist, add it
                        chunk_video_ids.append(cached_video_id)
                        self.ui.show_track_status(track['name'], ', '.join(track['artists']), 'cached')
                        continue
                
                # Skip tracks previously marked as not found (unless force reprocessing)
                if not force_reprocess and cached_track and cached_track.get('status') == 'not_found':
                    self.ui.show_track_status(track['name'], ', '.join(track['artists']), 'skipped')
                    continue
                
                # Search for new track
                youtube_track = self.youtube.search_track(
                    track['name'], 
                    ', '.join(track['artists']), 
                    track['album']
                )
                
                if youtube_track:
                    video_id = youtube_track['videoId']
                    # Only add if not already in the playlist
                    if video_id not in existing_youtube_tracks:
                        chunk_video_ids.append(video_id)
                        self.summary['tracks_migrated'] += 1
                        self.ui.show_track_status(track['name'], ', '.join(track['artists']), 'found')
                        # Add to existing set to avoid duplicates within this chunk
                        existing_youtube_tracks.add(video_id)
                    else:
                        self.ui.show_track_status(track['name'], ', '.join(track['artists']), 'exists')
                    
                    self.state.mark_track_migrated(
                        track['id'], 
                        spotify_playlist_id, 
                        'found', 
                        video_id
                    )
                else:
                    self.state.mark_track_migrated(track['id'], spotify_playlist_id, 'not_found')
                    self.summary['tracks_failed'] += 1
                    self.summary['failed_tracks'].append({
                        'playlist': playlist_name,
                        'track': track['name'],
                        'artist': ', '.join(track['artists']),
                        'album': track['album']
                    })
                    self.ui.show_track_status(track['name'], ', '.join(track['artists']), 'not_found')
                
                time.sleep(0.1)
            
            # Add this chunk's tracks to playlist in batches of 50
            if chunk_video_ids:
                chunk_added = self._add_tracks_in_batches(youtube_playlist_id, chunk_video_ids, playlist_name)
                total_added += chunk_added
                self.ui.print_info(f"Added {chunk_added} tracks from this chunk. Total added: {total_added}")
            
            # Save progress after each chunk
            self.state.save_state()
        
        # Final summary
        if total_added > 0:
            self.ui.print_info(f"✅ Successfully added {total_added} new tracks to {playlist_name}")
        else:
            self.ui.print_info(f"ℹ️  No new tracks to add to {playlist_name}")
        
        self.state.mark_playlist_completed(spotify_playlist_id)
        self.state.save_state()
        self.summary['playlists_processed'] += 1
        
        return True
    
    def _add_tracks_in_batches(self, youtube_playlist_id: str, video_ids: List[str], playlist_name: str) -> int:
        """Add tracks to YouTube playlist in batches of 50, return number successfully added"""
        batch_size = 50
        total_added = 0
        
        self.ui.print_info(f"🎵 Adding {len(video_ids)} tracks to playlist ID: {youtube_playlist_id}")
        
        for i in range(0, len(video_ids), batch_size):
            batch = video_ids[i:i + batch_size]
            
            # Try adding the batch, with one retry after a delay
            success = self.youtube.add_songs_to_playlist(youtube_playlist_id, batch)
            if not success:
                self.ui.print_warning(f"⚠️  First attempt failed, waiting 3 seconds and retrying...")
                import time
                time.sleep(3)
                success = self.youtube.add_songs_to_playlist(youtube_playlist_id, batch)
            
            if success:
                total_added += len(batch)
                self.ui.print_info(f"✅ Added batch of {len(batch)} tracks to {playlist_name}")
            else:
                self.ui.print_warning(f"❌ Failed to add batch of {len(batch)} tracks to {playlist_name}")
                self.ui.print_warning(f"   Playlist ID: {youtube_playlist_id}")
                self.ui.print_warning(f"   First few video IDs: {batch[:3]}")
                
                # Check if the playlist still exists
                try:
                    self.youtube.get_playlist_tracks(youtube_playlist_id)
                    self.ui.print_warning("   Playlist exists but batch add failed - might be API quota or video ID issue")
                except Exception as e:
                    self.ui.print_warning(f"   Playlist no longer exists: {e}")
                    break  # No point continuing if playlist is gone
        
        return total_added
    
    def run_migration(self):
        self.ui.show_welcome()
        
        if not self.initialize_clients():
            return
        
        try:
            user_info = self.spotify.get_user_info()
            all_playlists = self.spotify.get_user_playlists()
            
            # Filter to only include playlists owned by the user
            owned_playlists = [
                playlist for playlist in all_playlists 
                if playlist['owner'] == user_info['display_name'] or playlist['owner'] == user_info['id']
            ]
            
            # Always add Liked Songs (owned by the user)
            owned_playlists.append({
                'id': 'liked_songs',
                'name': 'Liked Songs',
                'owner': user_info['display_name'],
                'track_count': 'Unknown',
                'public': False
            })
            
            skipped_count = len(all_playlists) - len(owned_playlists) + 1  # +1 because we added Liked Songs
            if skipped_count > 0:
                self.ui.print_info(f"Skipping {skipped_count} playlists not owned by you")
            
            self.ui.show_spotify_playlists(owned_playlists, user_info)
            playlists = owned_playlists
            
            if not self.ui.confirm_migration():
                self.ui.print_info("Migration cancelled.")
                return
            
            with self.ui.create_progress_context() as progress:
                main_task = progress.add_task("Migrating playlists...", total=len(playlists))
                
                for playlist in playlists:
                    is_liked_songs = playlist['id'] == 'liked_songs'
                    playlist_task = progress.add_task(
                        f"Processing: {playlist['name']}", 
                        total=1
                    )
                    
                    success = self.migrate_playlist(playlist, is_liked_songs)
                    
                    progress.update(playlist_task, completed=1)
                    progress.update(main_task, advance=1)
                    
                    if not success:
                        self.ui.print_warning(f"Failed to migrate playlist: {playlist['name']}")
            
            self._save_failed_tracks_report()
            self.ui.show_migration_summary(self.summary)
            
        except KeyboardInterrupt:
            self.ui.print_warning("Migration interrupted by user.")
            self.state.save_state()
        except Exception as e:
            self.ui.print_error(f"Migration failed with error: {e}")
            self.state.save_state()
            raise
    
    def _save_failed_tracks_report(self):
        if self.summary['failed_tracks']:
            report_file = config.get_cache_file("failed_tracks.json")
            config.ensure_cache_dir()
            
            with open(report_file, 'w') as f:
                json.dump(self.summary['failed_tracks'], f, indent=2)
            
            self.summary['failed_tracks_file'] = str(report_file)