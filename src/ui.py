from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich import box
from typing import List, Dict, Optional
import time

class MigratorUI:
    def __init__(self):
        self.console = Console()
        self.progress = None
    
    def show_welcome(self):
        logo = """
  ♪ ♫ ♪ ♫ ♪ ♫ ♪ ♫ ♪ ♫ ♪ ♫ ♪ ♫ ♪ ♫
  
      SPOTIFY → YOUTUBE MUSIC 
           MIGRATION TOOL
           
  ♪ ♫ ♪ ♫ ♪ ♫ ♪ ♫ ♪ ♫ ♪ ♫ ♪ ♫ ♪ ♫
        """
        
        welcome_panel = Panel(
            Align.center(Text(logo.strip(), style="bold cyan")),
            box=box.DOUBLE,
            border_style="bright_blue"
        )
        
        self.console.print()
        self.console.print(welcome_panel)
        self.console.print()
    
    def print_success(self, message: str):
        self.console.print(f"✅ {message}", style="green")
    
    def print_warning(self, message: str):
        self.console.print(f"⚠️  {message}", style="yellow")
    
    def print_error(self, message: str):
        self.console.print(f"❌ {message}", style="red")
    
    def print_info(self, message: str):
        self.console.print(f"ℹ️  {message}", style="blue")
    
    def show_spotify_playlists(self, playlists: List[Dict], user_info: Dict):
        self.console.print(f"\n[bold]Found {len(playlists)} playlists owned by you: {user_info['display_name']}[/bold]")
        
        table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
        table.add_column("Playlist", style="cyan", no_wrap=True)
        table.add_column("Owner", style="dim")
        table.add_column("Tracks", justify="right", style="green")
        table.add_column("Public", justify="center")
        
        for playlist in playlists:
            public_icon = "🌐" if playlist['public'] else "🔒"
            owner_style = "bold green" if (playlist['owner'] == user_info['display_name'] or playlist['owner'] == user_info['id']) else "dim"
            table.add_row(
                playlist['name'],
                playlist['owner'],
                str(playlist['track_count']),
                public_icon
            )
        
        self.console.print(table)
        self.console.print()
    
    def confirm_migration(self) -> bool:
        response = self.console.input("[yellow]Start migration? (y/N): [/yellow]").lower()
        return response in ['y', 'yes']
    
    def create_progress_context(self):
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=self.console,
            transient=True
        )
        return self.progress
    
    def show_migration_summary(self, summary: Dict):
        self.console.print("\n[bold green]Migration Summary[/bold green]")
        
        summary_table = Table(box=box.SIMPLE_HEAD)
        summary_table.add_column("Metric", style="cyan", no_wrap=True)
        summary_table.add_column("Count", justify="right", style="magenta")
        
        summary_table.add_row("Playlists Processed", str(summary['playlists_processed']))
        summary_table.add_row("Playlists Created", str(summary['playlists_created']))
        summary_table.add_row("Tracks Found", str(summary['tracks_found']))
        summary_table.add_row("Tracks Migrated", str(summary['tracks_migrated']))
        summary_table.add_row("Tracks Failed", str(summary['tracks_failed']))
        
        if summary['tracks_found'] > 0:
            success_rate = (summary['tracks_migrated'] / summary['tracks_found']) * 100
            summary_table.add_row("Success Rate", f"{success_rate:.1f}%")
        
        self.console.print(summary_table)
        
        if summary.get('failed_tracks'):
            self.console.print(f"\n[yellow]Failed tracks saved to: {summary['failed_tracks_file']}[/yellow]")
        
        self.console.print()
    
    def show_playlist_status(self, playlist_name: str, status: str, style: str = ""):
        status_icons = {
            'creating': '🔄',
            'exists': '📁',
            'created': '✅',
            'failed': '❌'
        }
        
        icon = status_icons.get(status, '•')
        message = f"{icon} Playlist: {playlist_name}"
        
        if style:
            self.console.print(message, style=style)
        else:
            self.console.print(message)
    
    def show_track_status(self, track_name: str, artist: str, status: str):
        status_icons = {
            'found': '✅',
            'not_found': '❌',
            'skipped': '⏭️',
            'exists': '📋',
            'cached': '🔄'
        }
        
        icon = status_icons.get(status, '•')
        track_info = f"{track_name} - {artist}"
        
        if len(track_info) > 60:
            track_info = track_info[:57] + "..."
        
        if status == 'found':
            self.console.print(f"  {icon} {track_info}", style="dim green")
        elif status == 'not_found':
            self.console.print(f"  {icon} {track_info}", style="dim red")
        elif status == 'exists':
            self.console.print(f"  {icon} {track_info}", style="dim yellow")
        elif status == 'cached':
            self.console.print(f"  {icon} {track_info}", style="dim cyan")
        elif status == 'skipped':
            self.console.print(f"  {icon} {track_info}", style="dim magenta")
        else:
            self.console.print(f"  {icon} {track_info}", style="dim")
    
    def ask_for_oauth_setup(self) -> bool:
        self.print_warning("YouTube Music OAuth not configured.")
        self.console.print("You need to set up YouTube Music authentication.")
        self.show_detailed_oauth_instructions()
        
        response = self.console.input("\n[yellow]Would you like to set up OAuth now? (y/N): [/yellow]").lower()
        return response in ['y', 'yes']
    
    def show_detailed_oauth_instructions(self):
        self.console.print("\n[bold cyan]📋 Detailed YouTube Music OAuth Setup:[/bold cyan]")
        
        steps_table = Table(box=box.ROUNDED, show_header=False, padding=(0, 1))
        steps_table.add_column("Step", style="bold blue", width=6)
        steps_table.add_column("Action", style="white")
        
        steps = [
            ("1.", "Open YouTube Music in your browser: https://music.youtube.com"),
            ("2.", "Log in to your Google account if not already logged in"),
            ("3.", "Open Developer Tools:"),
            ("", "  • Chrome/Edge: Press F12 or Ctrl+Shift+I"),
            ("", "  • Firefox: Press F12 or Ctrl+Shift+I"),
            ("", "  • Safari: Cmd+Option+I (enable Developer menu first)"),
            ("4.", "Click on the 'Network' tab in Developer Tools"),
            ("5.", "Clear the network log (trash can icon or Ctrl+L)"),
            ("6.", "In YouTube Music, perform ANY action:"),
            ("", "  • Search for a song"),
            ("", "  • Click on a playlist"),
            ("", "  • Navigate to your library"),
            ("7.", "In Network tab, look for requests to 'music.youtube.com'"),
            ("8.", "Find a request with method 'POST' (usually 'browse' or 'search')"),
            ("9.", "Click on the request → Headers tab → Request Headers"),
            ("10.", "Copy ALL the request headers (see example below)")
        ]
        
        for step, action in steps:
            steps_table.add_row(step, action)
        
        self.console.print(steps_table)
        
        self.console.print("\n[bold yellow]🔍 What Headers to Copy:[/bold yellow]")
        
        headers_example = """
[dim]Example request headers you need to copy:[/dim]

[green]accept: */*
accept-encoding: gzip, deflate, br
accept-language: en-US,en;q=0.9
authorization: SAPISIDHASH sha256_hash_here
content-type: application/json
cookie: VISITOR_INFO1_LIVE=abc123; YSC=def456; ...
origin: https://music.youtube.com
referer: https://music.youtube.com/
user-agent: Mozilla/5.0 (compatible browser string)
x-client-data: base64data
x-goog-api-key: AIzaSy...
x-origin: https://music.youtube.com[/green]

[bold red]⚠️  IMPORTANT:[/bold red]
• Copy [bold]ALL[/bold] headers from the request (not response)
• Include the full 'cookie' header with all values
• Make sure 'authorization' header is included
• Don't modify or truncate any values
        """
        
        self.console.print(Panel(headers_example.strip(), title="Headers Example", border_style="yellow"))
        
        self.console.print("\n[bold cyan]💡 Tips:[/bold cyan]")
        tips = [
            "• If you don't see 'authorization' header, try refreshing YouTube Music and trying again",
            "• The cookie header is usually very long - make sure you copy it completely",
            "• You can right-click on the headers section and 'Copy All' or 'Copy as cURL'",
            "• If setup fails, try using a different request (browse, search, etc.)"
        ]
        
        for tip in tips:
            self.console.print(f"  {tip}")
    
    def show_oauth_paste_instructions(self):
        self.console.print("\n[bold green]📝 Ready to Paste Headers:[/bold green]")
        self.console.print("When prompted by ytmusicapi setup:")
        self.console.print("1. Paste the headers you copied from Developer Tools")
        self.console.print("2. Press Enter twice (empty line) to finish")
        self.console.print("3. The oauth.json file will be created automatically")
        self.console.print("\n[yellow]Paste your headers now...[/yellow]")