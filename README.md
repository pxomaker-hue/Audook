# Audook - Audiobook Client for Windows

A modern, feature-rich audiobook player for Windows that supports **Audiobookshelf** and **Plex** servers.

## Features

### Core Features
- ✅ Connect to **Audiobookshelf** servers
- ✅ Connect to **Plex** servers
- ✅ Browse audiobook libraries
- ✅ Play audiobooks with chapter support
- ✅ Modern, dark/light theme UI

### Playback Features
- ✅ Play/Pause/Stop controls
- ✅ Previous/Next chapter navigation
- ✅ **Seek backward/forward by 10s and 30s**
- ✅ Adjustable playback speed (0.5x - 2.0x)
- ✅ Volume control
- ✅ **Remember playback position between sessions**
- ✅ Progress bar with time display

### Library Features
- ✅ Browse audiobooks by library
- ✅ Search audiobooks
- ✅ View audiobook metadata (title, author, narrator, duration)
- ✅ **Bookmarks** for saving positions
- ✅ **Download audiobooks for offline listening**

### Sync Features
- ✅ **Sync playback position with server** (Audiobookshelf & Plex)
- ✅ **Cross-device synchronization** (via server sync)

### Settings
- ✅ Add/Edit/Remove multiple servers
- ✅ Switch between Audiobookshelf and Plex
- ✅ Dark and Light themes
- ✅ Configure default playback settings

## Screenshots

*(Screenshots will be added in future versions)*

## Installation

### Prerequisites
- Windows 10 or 11
- Python 3.10 or higher (for development)

### Quick Install (Using Installer)
1. Download the latest installer from the [Releases](https://github.com/pxomaker-hue/Audook/releases) page
2. Run the installer and follow the prompts
3. Launch Audook from the Start Menu or desktop shortcut

### Development Setup
1. Clone this repository:
 ```bash
 git clone https://github.com/pxomaker-hue/Audook.git
 cd Audook
 ```

2. Create a virtual environment:
 ```bash
 python -m venv venv
 source venv/bin/activate # On Windows: venv\Scripts\activate
 ```

3. Install dependencies:
 ```bash
 pip install -r requirements.txt
 ```

4. Run the application:
 ```bash
 python main.py
 ```

### Building the Executable

To create a standalone Windows executable:

1. Install PyInstaller:
 ```bash
 pip install pyinstaller
 ```

2. Run the build script:
 ```bash
 python build_spec.py
 ```
 or double-click `build.bat`

3. The executable will be created in the `dist/` folder

### Creating an Installer

To create a professional Windows installer:

1. Install [Inno Setup](https://jrsoftware.org/isinfo.php)
2. Run the build script (it will automatically create the installer if Inno Setup is installed)
3. The installer will be in the `dist/` folder as `Audook_Setup.exe`

## Usage

### Adding a Server

1. Click the **Settings** (⚙️) button in the top-right corner
2. Go to the **Servers** tab
3. Click **Add Server**
4. Enter the server details:
 - **Name**: A friendly name for the server
 - **Type**: Audiobookshelf or Plex
 - **URL**: The server URL (e.g., `http://your-nas:13378` for Audiobookshelf)
 - **API Key**: For Audiobookshelf (find in Settings > Users > Your User > API Key)
 - **Username/Password**: For Plex
5. Click **Save**

### Browsing Audiobooks

1. Select a server from the dropdown in the library view
2. Select a library
3. Browse or search for audiobooks
4. Double-click an audiobook to start playing

### Playback Controls

- **Space**: Play/Pause
- **Left Arrow**: Seek backward 10 seconds
- **Right Arrow**: Seek forward 10 seconds
- **Ctrl+Left Arrow**: Seek backward 30 seconds
- **Ctrl+Right Arrow**: Seek forward 30 seconds
- **Up Arrow**: Previous chapter
- **Down Arrow**: Next chapter

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Space | Play/Pause |
| ← | Seek -10s |
| → | Seek +10s |
| Ctrl+← | Seek -30s |
| Ctrl+→ | Seek +30s |
| ↑ | Previous Chapter |
| ↓ | Next Chapter |
| Ctrl+↑ | Increase Volume |
| Ctrl+↓ | Decrease Volume |
| Ctrl+F | Search |
| Ctrl+, | Settings |

## Configuration

All configuration is stored in:
- `%USERPROFILE%\.Audook\config.json` - Main configuration
- `%USERPROFILE%\.Audook\playback_state.json` - Playback state
- `%USERPROFILE%\.Audook\bookmarks.json` - Bookmarks
- `%USERPROFILE%\.Audook\cache\` - Cached audio files

## Troubleshooting

### Connection Issues
- **Audiobookshelf**: Ensure the server URL is correct and the API key is valid
- **Plex**: Ensure the server URL is correct and you have the correct credentials
- Check that your NAS/server is accessible from your Windows machine

### Playback Issues
- Ensure you have an active internet connection (for streaming)
- For offline playback, download the audiobook first
- Check that your audio device is working properly

### Performance Issues
- Reduce the number of audiobooks loaded at once
- Clear the cache if it's taking up too much space
- Use a lower quality setting for downloads

## API References

- [Audiobookshelf API Documentation](https://github.com/advplyr/audiobookshelf/wiki/API-Documentation)
- [Plex API Documentation](https://developer.plex.tv/)

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

### Development Guidelines
- Follow PEP 8 style guide
- Use type hints
- Write docstrings for all public methods
- Keep the code clean and well-organized

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Audiobookshelf](https://github.com/advplyr/audiobookshelf) - The best self-hosted audiobook server
- [Plex](https://www.plex.tv/) - Media server platform
- [PyQt6](https://www.riverbankcomputing.com/static/Docs/PyQt6/) - Python bindings for Qt
- [PyInstaller](https://www.pyinstaller.org/) - Python application packaging

## Support

For support, please open an issue on the [GitHub repository](https://github.com/pxomaker-hue/Audook).

---

**Audook** - Your perfect audiobook companion for Windows! 📚🎧
