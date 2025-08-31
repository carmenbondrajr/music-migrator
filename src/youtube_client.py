import os
import json
from ytmusicapi import YTMusic
from typing import List, Dict, Optional
from .config import config

class YouTubeClient:
    def __init__(self):
        if not config.validate_ytmusic_config():
            raise ValueError(f"YouTube Music OAuth file not found at {config.ytmusic_oauth_json}. Run 'make setup-oauth' first.")
        
        # Try to initialize YTMusic client with different approaches
        try:
            # Method 1: Try with just oauth.json (modern ytmusicapi should work)
            self.yt = YTMusic(config.ytmusic_oauth_json)
            
        except Exception as e:
            # Method 2: Try with explicit OAuth credentials if available
            try:
                from ytmusicapi import OAuthCredentials
                
                # Check if OAuth credentials are in config
                if hasattr(config, 'ytmusic_client_id') and hasattr(config, 'ytmusic_client_secret'):
                    oauth_creds = OAuthCredentials(
                        client_id=config.ytmusic_client_id,
                        client_secret=config.ytmusic_client_secret
                    )
                    self.yt = YTMusic(config.ytmusic_oauth_json, oauth_credentials=oauth_creds)
                else:
                    # Fall back to method 1 error
                    raise e
                    
            except (ImportError, AttributeError):
                # OAuthCredentials not available or config missing, show helpful error
                raise ValueError(
                    f"Failed to initialize YouTube Music client.\n"
                    f"Error: {e}\n\n"
                    f"Solutions:\n"
                    f"1. Make sure you ran 'ytmusicapi oauth' successfully\n"
                    f"2. Check that oauth.json file exists and is valid\n"
                    f"3. Try running 'make setup-oauth' again\n"
                    f"4. Update ytmusicapi: pip install ytmusicapi --upgrade"
                )
        
        self._cached_playlists = None
        self._auth_failed = False
    
    def _is_auth_error(self, exception: Exception) -> bool:
        """Check if the exception indicates an authentication failure"""
        error_str = str(exception).lower()
        return any(keyword in error_str for keyword in [
            'access_token', 'unauthorized', '401', 'authentication', 'expired'
        ])
    
    def _handle_auth_error(self, operation: str):
        """Handle authentication errors by setting flag and showing message"""
        if not self._auth_failed:  # Only show message once
            self._auth_failed = True
            print(f"\n⚠️  YouTube Music authentication expired during {operation}")
            print(f"   Run 'ytmusicapi oauth' to refresh your tokens")
            print(f"   Then restart the migration - it will resume where it left off!")
        return None
    
    @classmethod
    def setup_oauth_interactive(cls) -> str:
        """
        Automated OAuth setup using credentials from .env file.
        """
        from rich.console import Console
        import subprocess
        import os
        
        console = Console()
        
        # Check if we have the required environment variables
        client_id = config.ytmusic_client_id
        client_secret = config.ytmusic_client_secret
        
        if not client_id or not client_secret:
            console.print("\n[bold red]⚠️  Missing YouTube OAuth Credentials![/bold red]")
            console.print("Please add these to your .env file:")
            console.print("[yellow]YTMUSIC_OAUTH_CLIENT_ID=your_client_id")
            console.print("YTMUSIC_OAUTH_SECRET=your_client_secret[/yellow]")
            console.print("\n[bold cyan]To get these credentials:[/bold cyan]")
            console.print("1. Go to Google Cloud Console: https://console.cloud.google.com/")
            console.print("2. Create a project or select existing one") 
            console.print("3. Enable YouTube Data API v3")
            console.print("4. Create OAuth 2.0 credentials (select 'TVs and Limited Input devices')")
            raise ValueError("YouTube OAuth credentials not found in .env file")
        
        console.print("\n[bold green]🔑 Using OAuth credentials from .env file[/bold green]")
        console.print(f"Client ID: {client_id[:20]}...")
        
        # Set environment variables for ytmusicapi oauth command
        env = os.environ.copy()
        env['YTMUSIC_CLIENT_ID'] = client_id
        env['YTMUSIC_CLIENT_SECRET'] = client_secret
        
        try:
            console.print("\n[bold cyan]Running automated OAuth setup...[/bold cyan]")
            console.print("This will open your browser for authentication.")
            
            # Run ytmusicapi oauth with credentials piped as input
            oauth_input = f"{client_id}\n{client_secret}\n"
            result = subprocess.run([
                'ytmusicapi', 'oauth', 
                '--file', config.ytmusic_oauth_json
            ], input=oauth_input, text=True, cwd=config.project_root)
            
            if result.returncode == 0:
                console.print(f"[bold green]✅ OAuth setup successful![/bold green]")
                console.print(f"Saved to: {config.ytmusic_oauth_json}")
                return config.ytmusic_oauth_json
            else:
                console.print(f"[bold red]❌ OAuth setup failed![/bold red]")
                console.print(f"Error: {result.stderr}")
                console.print("\n[yellow]Fallback: Run this manually:[/yellow]")
                console.print(f"[bold]ytmusicapi oauth --file {config.ytmusic_oauth_json} --client-id {client_id} --client-secret {client_secret}[/bold]")
                raise ValueError(f"ytmusicapi oauth failed: {result.stderr}")
                
        except FileNotFoundError:
            console.print("\n[bold red]❌ ytmusicapi command not found![/bold red]")
            console.print("Please install it: [bold]pip install ytmusicapi[/bold]")
            raise ValueError("ytmusicapi not installed")
    
    @classmethod  
    def setup_oauth(cls, headers_file: Optional[str] = None) -> str:
        """
        Legacy OAuth setup method - may not work with current ytmusicapi versions.
        """
        # Try the command-line approach first
        return cls.setup_oauth_interactive()
    
    def search_track(self, track_name: str, artist_name: str, album_name: Optional[str] = None) -> Optional[Dict]:
        query = f"{track_name} {artist_name}"
        if album_name:
            query += f" {album_name}"
        
        try:
            results = self.yt.search(query, filter="songs", limit=5)
            
            if not results:
                return None
            
            for result in results:
                if result.get('videoId'):
                    return {
                        'videoId': result['videoId'],
                        'title': result.get('title', ''),
                        'artists': [artist.get('name', '') for artist in result.get('artists', [])],
                        'album': result.get('album', {}).get('name', '') if result.get('album') else '',
                        'duration': result.get('duration', ''),
                        'thumbnails': result.get('thumbnails', [])
                    }
            
            return None
        except Exception as e:
            if self._is_auth_error(e):
                return self._handle_auth_error("search")
            else:
                print(f"Search error for '{query}': {e}")
            return None
    
    def create_playlist(self, title: str, description: str = "", privacy_status: str = "PRIVATE") -> Optional[str]:
        try:
            # Check what account we're authenticated as
            try:
                account_info = self.yt.get_account_info()
                print(f"🔐 Authenticated as: {account_info.get('name', 'Unknown')} ({account_info.get('accountName', 'Unknown')})")
            except Exception as auth_check_e:
                print(f"⚠️  Could not verify account info: {auth_check_e}")
            
            print(f"🎵 Attempting to create playlist: '{title}'")
            print(f"   Description: '{description}'")
            print(f"   Privacy: {privacy_status}")
            
            playlist_id = self.yt.create_playlist(title, description, privacy_status)
            print(f"✅ ytmusicapi returned playlist ID: {playlist_id}")
            
            # Immediately try to verify the playlist was actually created
            try:
                import time
                time.sleep(1)  # Brief wait
                test_playlist = self.yt.get_playlist(playlist_id)
                print(f"✅ Verified playlist creation: {test_playlist.get('title', 'Unknown')} with {len(test_playlist.get('tracks', []))} tracks")
                
                # Skip the add test - empty list doesn't work and we don't want to add random songs
                print("✅ Playlist creation verified successfully")
                
            except Exception as verify_e:
                print(f"❌ Playlist creation verification failed: {verify_e}")
                print(f"   Error type: {type(verify_e).__name__}")
                print(f"   This suggests the playlist wasn't actually created despite getting an ID")
                return None
            
            self._cached_playlists = None
            return playlist_id
        except Exception as e:
            if self._is_auth_error(e):
                return self._handle_auth_error("playlist creation")
            else:
                print(f"Error creating playlist '{title}': {e}")
                print(f"Error type: {type(e).__name__}")
                print(f"Full error: {str(e)}")
            return None
    
    def add_songs_to_playlist(self, playlist_id: str, video_ids: List[str]) -> bool:
        try:
            if not video_ids:
                return True
            
            self.yt.add_playlist_items(playlist_id, video_ids)
            return True
        except Exception as e:
            if self._is_auth_error(e):
                self._handle_auth_error("adding songs to playlist")
                return False
            else:
                print(f"Error adding {len(video_ids)} songs to playlist: {e}")
            return False
    
    def get_playlists(self) -> List[Dict]:
        if self._cached_playlists is None:
            try:
                playlists = self.yt.get_library_playlists(limit=None)
                self._cached_playlists = [
                    {
                        'id': playlist['playlistId'],
                        'title': playlist['title'],
                        'count': playlist.get('count', 0)
                    }
                    for playlist in playlists
                ]
            except Exception:
                self._cached_playlists = []
        
        return self._cached_playlists
    
    def playlist_exists(self, title: str) -> Optional[str]:
        playlists = self.get_playlists()
        for playlist in playlists:
            if playlist['title'] == title:
                return playlist['id']
        return None
    
    def get_playlist_tracks(self, playlist_id: str) -> List[Dict]:
        try:
            playlist = self.yt.get_playlist(playlist_id)
            tracks = playlist.get('tracks', [])
            
            return [
                {
                    'videoId': track['videoId'],
                    'title': track.get('title', ''),
                    'artists': [artist.get('name', '') for artist in track.get('artists', [])],
                }
                for track in tracks
                if track.get('videoId')
            ]
        except Exception:
            return []