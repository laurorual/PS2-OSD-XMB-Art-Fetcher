# PS2 OSD-XMB Art Fetcher
A powerful CLI tool that automatically fetches high-quality artwork (logos and backgrounds) for your PS2 ISO games to use with the OSD-XMB PlayStation 2 homebrew.

# ✨ Features
Automated Artwork Fetching: Downloads ICON0.png (logos) and PIC1.png (hero backgrounds) for all your PS2 ISO games

Smart Game Identification: Extracts GameIDs from ISO files and matches them with official PCSX2 database

SteamGridDB Integration: Pulls high-quality artwork from the largest game art database

Multi-Platform: Works on both Windows and Linux systems

Caching System: Avoids redundant API calls for faster subsequent runs

Multi-Language Support: English and Portuguese interfaces

# 🚀 Usage
For Most Users (Recommended) - Using Pre-built Binaries:

1. Go to the Releases section of this repository
2. Download the appropriate executable for your system
3. Run the Executable:

        Windows: Double-click PS2_OSD-XMB_Art_Fetcher_Win.exe or run from command prompt

        Linux: Make executable first, then run:
        bash
        chmod +x PS2_OSD-XMB_Art_Fetcher
        ./PS2_OSD-XMB_Art_Fetcher

# 📁 Expected Directory Structure

    your_storage_root/
    ├── OSDXMB/
    │   └── ART/ (artwork will be saved here)
    └── DVD/
        ├── Game1.iso
        ├── Game2.iso
        └── ...

# 🛠️ Building Binaries

# Install PyInstaller and dependencies
    pip install pyinstaller requests pycdlib PyYAML

# Building executable
    pyinstaller --onefile --console --name "PS2_OSD-XMB_Art_Fetcher" --hidden-import=pycdlib --hidden-import=yaml --hidden-import=requests PS2_OSD-XMB_Art_Fetcher.py

# 🤝 Contributing

Contributions are welcome! Feel free to:

- Report bugs and issues
- Suggest new features
- Submit pull requests
- Improve documentation

# ⚠️ Notes

The first run will take longer as it builds the cache.

Some rare games might not be found in the databases.

Artwork quality and accuracy depends on SteamGridDB's community submissions.

# 🔗 Links

SteamGridDB - Game artwork database: https://www.steamgriddb.com/

PCSX2 - PS2 emulator project: https://github.com/PCSX2/pcsx2

OSD-XMB - PS2 XMB: https://github.com/HiroTex/OSD-XMB
