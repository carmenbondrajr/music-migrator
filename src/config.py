import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

class Config:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.env_file = self.project_root / ".env"
        self.cache_dir = self.project_root / "cache"
        self.oauth_file = self.project_root / "oauth.json"
        
        load_dotenv(self.env_file)
        
        self.spotify_client_id = os.getenv("SPOTIFY_CLIENT_ID")
        self.spotify_client_secret = os.getenv("SPOTIFY_CLIENT_SECRET") 
        self.spotify_redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")
        
        self.ytmusic_oauth_json = os.getenv("YTMUSIC_OAUTH_JSON", "oauth.json")
        if not self.ytmusic_oauth_json.startswith("/"):
            self.ytmusic_oauth_json = str(self.project_root / self.ytmusic_oauth_json)
            
        # YouTube OAuth credentials from .env
        self.ytmusic_client_id = os.getenv("YTMUSIC_OAUTH_CLIENT_ID")
        self.ytmusic_client_secret = os.getenv("YTMUSIC_OAUTH_SECRET")
    
    def validate_spotify_config(self) -> bool:
        return bool(self.spotify_client_id and self.spotify_client_secret)
    
    def validate_ytmusic_config(self) -> bool:
        return os.path.exists(self.ytmusic_oauth_json)
    
    def get_cache_file(self, filename: str) -> Path:
        return self.cache_dir / filename
    
    def ensure_cache_dir(self):
        self.cache_dir.mkdir(exist_ok=True)

config = Config()