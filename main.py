#!/usr/bin/env python3

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.migrator import SpotifyToYouTubeMigrator
from src.youtube_client import YouTubeClient
from src.ui import MigratorUI
from src.config import config

def setup_oauth():
    ui = MigratorUI()
    ui.print_info("Setting up YouTube Music OAuth...")
    
    ui.console.print("\n[bold red]⚠️  YouTube Music API has changed as of November 2024![/bold red]")
    ui.console.print("The old browser header method no longer works.")
    ui.console.print("\n[bold cyan]New OAuth Setup Process:[/bold cyan]")
    
    steps_table = ui.console.print("""
[bold yellow]Step 1: Get Google Cloud Console Credentials[/bold yellow]
1. Go to: https://console.cloud.google.com/
2. Create a new project or select existing one
3. Enable "YouTube Data API v3" 
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
5. Select "TVs and Limited Input devices" (not Web application)
6. Copy your Client ID and Client Secret

[bold red]⚠️  OAuth Consent Screen Setup (IMPORTANT):[/bold red]
7. Go to "OAuth consent screen" in Google Cloud Console
8. Select "External" user type (unless you have Google Workspace)
9. Fill in required fields:
   • App name: "Music Migrator" (or whatever you prefer)
   • User support email: your email
   • Developer contact: your email
10. Add your email to "Test users" section
11. [bold green]This allows YOU to use the app during development[/bold green]

[bold yellow]Step 2: Run OAuth Setup[/bold yellow]
Run this command in your terminal:
  [bold green]ytmusicapi oauth[/bold green]

This will:
• Prompt for your Client ID and Secret
• Open a browser for Google OAuth
• Create oauth.json automatically

[bold yellow]Step 3: Bypass "Access blocked" Error[/bold yellow]
If you see "Access blocked: music-migrator has not completed verification":
• Click "Advanced" (or similar link)
• Click "Go to [Your App Name] (unsafe)"
• This is safe for your own personal OAuth app

[bold yellow]Step 4: Run OAuth Setup[/bold yellow]
After setting up the OAuth consent screen and adding yourself as a test user.
""")
    
    ui.console.print("\n[red]Have you completed the OAuth consent screen setup above? (y/N): [/red]", end="")
    response = input().lower()
    
    if response in ['y', 'yes']:
        try:
            oauth_file = YouTubeClient.setup_oauth_interactive()
            ui.print_success("OAuth setup completed!")
            ui.print_info(f"✅ {oauth_file} file created")
            ui.print_info("✅ You can now run: python main.py migrate")
        except Exception as e:
            ui.print_error(f"OAuth setup failed: {e}")
            ui.print_info("Please run 'ytmusicapi oauth' manually")
    else:
        ui.print_info("Please run 'ytmusicapi oauth' manually when ready.")
        ui.print_info("Then run 'python main.py validate' to check setup.")

def validate_setup():
    ui = MigratorUI()
    issues = []
    
    if not config.env_file.exists():
        issues.append("❌ .env file not found")
        ui.print_info("Copy .env.example to .env and fill in your credentials")
    else:
        if not config.validate_spotify_config():
            issues.append("❌ Spotify credentials missing in .env")
        else:
            issues.append("✅ Spotify credentials configured")
    
    if not config.validate_ytmusic_config():
        issues.append("❌ YouTube Music OAuth not configured")
        ui.print_info("Run: python main.py setup-oauth")
    else:
        issues.append("✅ YouTube Music OAuth configured")
    
    for issue in issues:
        if issue.startswith("❌"):
            ui.print_error(issue[2:])
        else:
            ui.print_success(issue[2:])
    
    return all(not issue.startswith("❌") for issue in issues)

def migrate():
    if not validate_setup():
        return
    
    migrator = SpotifyToYouTubeMigrator()
    migrator.run_migration()

def migrate_playlist():
    """Interactive single playlist migration"""
    if not validate_setup():
        return
    
    ui = MigratorUI()
    ui.show_welcome()
    
    migrator = SpotifyToYouTubeMigrator()
    
    # Initialize clients
    if not migrator.initialize_clients():
        return
    
    try:
        # Get all playlists including liked songs
        user_info = migrator.spotify.get_user_info()
        all_playlists = migrator.spotify.get_user_playlists()
        
        # Filter to owned playlists
        owned_playlists = [
            playlist for playlist in all_playlists 
            if playlist['owner'] == user_info['display_name'] or playlist['owner'] == user_info['id']
        ]
        
        # Add Liked Songs
        owned_playlists.append({
            'id': 'liked_songs',
            'name': 'Liked Songs',
            'owner': user_info['display_name'],
            'track_count': 'Unknown',
            'public': False
        })
        
        # Show playlist selection
        ui.print_info(f"Found {len(owned_playlists)} playlists owned by you:")
        ui.console.print()
        
        # Create numbered list
        for i, playlist in enumerate(owned_playlists, 1):
            status_icon = "✅" if migrator.state.is_playlist_completed(playlist['id']) else "📝"
            track_info = f" ({playlist['track_count']} tracks)" if playlist['track_count'] != 'Unknown' else ""
            ui.console.print(f"  {i:2}. {status_icon} {playlist['name']}{track_info}")
        
        ui.console.print()
        ui.console.print("[dim]✅ = Previously migrated, 📝 = Not migrated[/dim]")
        ui.console.print()
        
        # Get user selection
        while True:
            try:
                choice = ui.console.input("[yellow]Enter playlist number (1-{}) or 'q' to quit: [/yellow]".format(len(owned_playlists)))
                if choice.lower() == 'q':
                    ui.print_info("Migration cancelled.")
                    return
                
                playlist_idx = int(choice) - 1
                if 0 <= playlist_idx < len(owned_playlists):
                    break
                else:
                    ui.print_error(f"Please enter a number between 1 and {len(owned_playlists)}")
            except ValueError:
                ui.print_error("Please enter a valid number or 'q' to quit")
        
        selected_playlist = owned_playlists[playlist_idx]
        is_liked_songs = selected_playlist['id'] == 'liked_songs'
        
        ui.print_info(f"Selected: {selected_playlist['name']}")
        
        # Check if already migrated
        if migrator.state.is_playlist_completed(selected_playlist['id']):
            ui.print_warning(f"This playlist was previously migrated.")
            response = ui.console.input("[yellow]Re-process anyway? This will add any missing tracks (y/N): [/yellow]").lower()
            if response not in ['y', 'yes']:
                ui.print_info("Migration cancelled.")
                return
        
        ui.console.print()
        response = ui.console.input(f"[yellow]Start migration of '{selected_playlist['name']}'? (y/N): [/yellow]").lower()
        if response not in ['y', 'yes']:
            ui.print_info("Migration cancelled.")
            return
        
        ui.print_info(f"🚀 Starting migration of '{selected_playlist['name']}'...")
        
        # Migrate the selected playlist (force re-process by not checking completed status)
        success = migrator.migrate_playlist(selected_playlist, is_liked_songs, force_reprocess=True)
        
        if success:
            ui.print_success(f"✅ Successfully migrated '{selected_playlist['name']}'!")
        else:
            ui.print_error(f"❌ Failed to migrate '{selected_playlist['name']}'")
            
    except KeyboardInterrupt:
        ui.print_warning("Migration interrupted by user.")
    except Exception as e:
        ui.print_error(f"Migration failed: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(
        description="Migrate Spotify playlists to YouTube Music",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py migrate           # Run full migration
  python main.py migrate-playlist  # Migrate a single playlist (interactive)
  python main.py setup-oauth       # Set up YouTube Music OAuth
  python main.py validate          # Check configuration
        """
    )
    
    parser.add_argument(
        'command',
        choices=['migrate', 'migrate-playlist', 'setup-oauth', 'validate'],
        help='Command to run'
    )
    
    if len(sys.argv) == 1:
        ui = MigratorUI()
        ui.show_welcome()
        ui.print_info("Usage: python main.py [migrate|migrate-playlist|setup-oauth|validate]")
        ui.print_info("Run 'python main.py validate' first to check your setup")
        return
    
    args = parser.parse_args()
    
    if args.command == 'migrate':
        migrate()
    elif args.command == 'migrate-playlist':
        migrate_playlist()
    elif args.command == 'setup-oauth':
        setup_oauth()
    elif args.command == 'validate':
        validate_setup()

if __name__ == "__main__":
    main()