.PHONY: help install setup validate migrate setup-oauth ytmusic-setup-oauth clean status deps-check retry-failed

# Default target
help:
	@echo "🎵 Spotify to YouTube Music Migrator"
	@echo ""
	@echo "Available targets:"
	@echo "  make install            - Install Python dependencies"
	@echo "  make setup              - Complete setup (install + copy .env + validate)"
	@echo "  make setup-oauth        - Setup YouTube Music OAuth authentication (interactive)"
	@echo "  make ytmusic-setup-oauth - Setup YouTube Music OAuth using .env credentials"
	@echo "  make validate           - Check configuration and credentials"
	@echo "  make migrate      - Run the migration process"
	@echo "  make retry-failed - Retry tracks that failed during migration"
	@echo "  make test-pagination - Test Spotify Liked Songs pagination"
	@echo "  make reset-liked     - Reset Liked Songs migration state for re-processing"
	@echo "  make status       - Show migration status and cached state"
	@echo "  make clean        - Clean cache and reset migration state"
	@echo "  make deps-check   - Check if Python dependencies are installed"
	@echo ""
	@echo "Quick start:"
	@echo "  1. make setup"
	@echo "  2. Edit .env with your Spotify credentials"
	@echo "  3. make ytmusic-setup-oauth"
	@echo "  4. make migrate"
	@echo "  5. make retry-failed  (if some tracks failed)"

# Install Python dependencies
install:
	@echo "📦 Installing Python dependencies..."
	pip install -r requirements.txt
	@echo "✅ Dependencies installed!"

# Check if dependencies are installed
deps-check:
	@echo "🔍 Checking Python dependencies..."
	@python -c "import spotipy, ytmusicapi, rich, dotenv; print('✅ All dependencies are installed!')" 2>/dev/null || \
	(echo "❌ Missing dependencies. Run 'make install' first." && exit 1)

# Complete setup process
setup: install
	@echo "⚙️  Setting up project..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "📝 Created .env file from template"; \
		echo "⚠️  Please edit .env and add your Spotify credentials!"; \
	else \
		echo "📝 .env file already exists"; \
	fi
	@echo ""
	@echo "✅ Setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Edit .env with your Spotify API credentials"
	@echo "  2. Run 'make setup-oauth' to configure YouTube Music"
	@echo "  3. Run 'make validate' to check everything is working"
	@echo "  4. Run 'make migrate' to start the migration"

# Setup YouTube Music OAuth
setup-oauth: deps-check
	@echo "🔐 Setting up YouTube Music OAuth..."
	@echo "⚠️  Note: YouTube Music API changed in November 2024"
	@echo "    You now need Google Cloud Console OAuth credentials"
	python main.py setup-oauth

# Setup YouTube Music OAuth using .env credentials
ytmusic-setup-oauth: deps-check
	@echo "🔐 Setting up YouTube Music OAuth from .env..."
	@if [ ! -f .env ]; then \
		echo "❌ .env file not found"; \
		exit 1; \
	fi
	@export $$(grep -v '^#' .env | xargs) && \
	if [ -z "$$YTMUSIC_OAUTH_CLIENT_ID" ] || [ -z "$$YTMUSIC_OAUTH_SECRET" ]; then \
		echo "❌ Missing YTMUSIC_OAUTH_CLIENT_ID or YTMUSIC_OAUTH_SECRET in .env"; \
		echo "   Please add these to your .env file first"; \
		exit 1; \
	else \
		ytmusicapi oauth --file oauth.json --client-id "$$YTMUSIC_OAUTH_CLIENT_ID" --client-secret "$$YTMUSIC_OAUTH_SECRET" 2>/dev/null || true; \
	fi
	@if [ -f oauth.json ]; then \
		echo "✅ OAuth setup complete! oauth.json created successfully."; \
	else \
		echo "❌ OAuth setup failed - oauth.json was not created"; \
		exit 1; \
	fi

# Validate configuration
validate: deps-check
	@echo "✅ Validating configuration..."
	python main.py validate

# Run migration
migrate: deps-check
	@echo "🚀 Starting migration..."
	python main.py migrate

# Show migration status
status:
	@echo "📊 Migration Status"
	@echo "=================="
	@if [ -f .env ]; then \
		echo "✅ .env file exists"; \
	else \
		echo "❌ .env file missing"; \
	fi
	@if [ -f oauth.json ]; then \
		echo "✅ YouTube Music OAuth configured"; \
	else \
		echo "❌ YouTube Music OAuth not configured"; \
	fi
	@if [ -f cache/migration_state.json ]; then \
		echo "📁 Migration state file exists"; \
		@python -c "import json; data=json.load(open('cache/migration_state.json')); print(f'   Completed playlists: {len(data.get(\"completed_playlists\", []))}'); print(f'   Migrated tracks: {len(data.get(\"tracks\", {}))}')" 2>/dev/null || echo "   (Unable to read state file)"; \
	else \
		echo "📁 No migration state found (fresh start)"; \
	fi
	@if [ -f cache/failed_tracks.json ]; then \
		echo "⚠️  Failed tracks report exists"; \
		@python -c "import json; data=json.load(open('cache/failed_tracks.json')); print(f'   Failed tracks: {len(data)}')" 2>/dev/null || echo "   (Unable to read failed tracks)"; \
	fi

# Clean cache and reset migration state
clean:
	@echo "🧹 Cleaning cache and migration state..."
	@if [ -d cache ]; then \
		rm -f cache/migration_state.json; \
		rm -f cache/failed_tracks.json; \
		rm -f cache/spotify_token_cache; \
		echo "✅ Cache cleaned!"; \
	else \
		echo "📁 Cache directory doesn't exist"; \
	fi
	@echo ""
	@echo "⚠️  Note: This will reset your migration progress."
	@echo "   Next migration will start from the beginning."

# Development targets
dev-install: install
	@echo "🛠️  Installing development dependencies..."
	pip install pytest black flake8 mypy
	@echo "✅ Development environment ready!"

# Quick validation for CI/development
test:
	@echo "🧪 Running basic validation tests..."
	python -c "from src.config import config; print('✅ Config module works')"
	python -c "from src.ui import MigratorUI; ui = MigratorUI(); print('✅ UI module works')"
	python -c "import sys; sys.path.insert(0, '.'); from main import main; print('✅ Main module works')"
	@echo "✅ All basic tests passed!"

# Show project info
info:
	@echo "📋 Project Information"
	@echo "====================="
	@echo "Project: Spotify to YouTube Music Migrator"
	@echo "Language: Python 3"
	@echo "Dependencies: spotipy, ytmusicapi, rich, python-dotenv"
	@echo ""
	@echo "📁 Project Structure:"
	@find . -name "*.py" -not -path "./cache/*" | head -10
	@echo ""
	@echo "📊 Line count:"
	@find . -name "*.py" -not -path "./cache/*" -exec wc -l {} + | tail -1