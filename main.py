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

def main():
    parser = argparse.ArgumentParser(
        description="Migrate Spotify playlists to YouTube Music",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py migrate        # Run the migration
  python main.py setup-oauth    # Set up YouTube Music OAuth
  python main.py validate       # Check configuration
        """
    )
    
    parser.add_argument(
        'command',
        choices=['migrate', 'setup-oauth', 'validate'],
        help='Command to run'
    )
    
    if len(sys.argv) == 1:
        ui = MigratorUI()
        ui.show_welcome()
        ui.print_info("Usage: python main.py [migrate|setup-oauth|validate]")
        ui.print_info("Run 'python main.py validate' first to check your setup")
        return
    
    args = parser.parse_args()
    
    if args.command == 'migrate':
        migrate()
    elif args.command == 'setup-oauth':
        setup_oauth()
    elif args.command == 'validate':
        validate_setup()

if __name__ == "__main__":
    main()