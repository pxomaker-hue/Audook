# Audook - Audiobook Client for Windows

A modern audiobook player supporting Audiobookshelf and Plex.

## Features

- **Multi-Server Support**: Connect to both Audiobookshelf and Plex servers
- **Library Management**: Browse your audiobook libraries
- **Playback Controls**: Play, pause, seek, skip chapters
- **Queue System**: Manage your playback queue with repeat and shuffle
- **Bookmarks**: Save your progress and bookmark positions
- **Offline Mode**: Download audiobooks for offline listening
- **Modern UI**: Clean, intuitive interface with dark/light themes

## Installation

```bash
# Clone the repository
git clone https://github.com/pxomaker-hue/Audook.git
cd Audook

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## Configuration

The application will create a configuration directory at `~/.Audook/` containing:
- `config.json` - Application settings
- `cache/` - Downloaded audio files
- `bookmarks.json` - Saved bookmarks
- `playback_state.json` - Current playback state

## Project Structure

```
audook/
├── app/
│   ├── __init__.py          # Application constants and paths
│   ├── models/
│   │   └── __init__.py      # Data models (Audiobook, Chapter, Library, etc.)
│   ├── audiobookshelf/
│   │   └── client.py        # Audiobookshelf API client
│   ├── plex/
│   │   └── client.py        # Plex API client
│   ├── player/
│   │   ├── __init__.py
│   │   ├── player.py        # Audio playback with pygame
│   │   └── queue.py         # Playback queue management
│   └── utils/
│       ├── __init__.py      # Utility functions
│       └── config_manager.py # Configuration management
├── assets/
│   └── icons/               # Application icons
├── requirements.txt         # Python dependencies
└── README.md
```

## Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

## License

MIT License
