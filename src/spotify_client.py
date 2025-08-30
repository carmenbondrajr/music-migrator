import spotipy
from spotipy.oauth2 import SpotifyOAuth
from typing import List, Dict, Optional, Generator
from .config import config

class SpotifyClient:
    def __init__(self):
        if not config.validate_spotify_config():
            raise ValueError("Spotify configuration incomplete. Check SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in .env")
        
        self.scope = "user-library-read playlist-read-private playlist-read-collaborative"
        self.sp = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=config.spotify_client_id,
                client_secret=config.spotify_client_secret,
                redirect_uri=config.spotify_redirect_uri,
                scope=self.scope,
                cache_path=str(config.get_cache_file("spotify_token_cache"))
            )
        )
    
    def get_user_playlists(self) -> List[Dict]:
        playlists = []
        results = self.sp.current_user_playlists(limit=50)
        
        while results:
            for playlist in results['items']:
                if playlist is not None:
                    playlists.append({
                        'id': playlist['id'],
                        'name': playlist['name'],
                        'owner': playlist['owner']['display_name'],
                        'track_count': playlist['tracks']['total'],
                        'public': playlist['public']
                    })
            
            if results['next']:
                results = self.sp.next(results)
            else:
                break
        
        return playlists
    
    def get_playlist_tracks(self, playlist_id: str) -> Generator[Dict, None, None]:
        results = self.sp.playlist_tracks(playlist_id, limit=100)
        
        while results:
            for item in results['items']:
                if item['track'] and item['track']['id']:
                    track = item['track']
                    yield {
                        'id': track['id'],
                        'name': track['name'],
                        'artists': [artist['name'] for artist in track['artists']],
                        'album': track['album']['name'],
                        'uri': track['uri']
                    }
            
            if results['next']:
                results = self.sp.next(results)
            else:
                break
    
    def get_saved_tracks(self) -> Generator[Dict, None, None]:
        results = self.sp.current_user_saved_tracks(limit=50)
        page = 1
        total_yielded = 0
        
        while results:
            page_items = len(results['items']) if results['items'] else 0
            print(f"📄 Fetching Liked Songs - Page {page}: {page_items} tracks (Total so far: {total_yielded})")
            
            for item in results['items']:
                if item['track'] and item['track']['id']:
                    track = item['track']
                    total_yielded += 1
                    yield {
                        'id': track['id'],
                        'name': track['name'],
                        'artists': [artist['name'] for artist in track['artists']],
                        'album': track['album']['name'],
                        'uri': track['uri']
                    }
            
            if results['next']:
                results = self.sp.next(results)
                page += 1
            else:
                break
        
        print(f"✅ Finished fetching Liked Songs: {total_yielded} total tracks")
    
    def get_user_info(self) -> Dict:
        user = self.sp.current_user()
        return {
            'id': user['id'],
            'display_name': user['display_name'] or user['id'],
            'followers': user['followers']['total']
        }