# PS2 OSD-XMB Art Fetcher
<p align="center"><img width="802" height="632" alt="Captura de tela 2025-09-17 165813" src="https://github.com/user-attachments/assets/b8be29f0-ed7c-404f-ab62-76c8f57a9b00" /></p>


A powerful tool that automatically fetches high-quality artwork (logos and backgrounds) for your PS2 ISO games to use with the OSD-XMB PlayStation 2 homebrew.

# ✨ Features
Automated Artwork Fetching: Downloads ICON0.png (logos) and PIC1.png (hero backgrounds) for all your PS2 ISO games

Smart Game Identification: Extracts GameIDs from ISO files and matches them with official PCSX2 database

Launchbox Games Database and SteamGridDB Integration: Pulls high-quality artwork from the largest game art databases

Multi-Platform: Works on Windows, Linux and macOS systems

Caching System: Avoids redundant API calls for faster subsequent runs

Multi-Language Support: English and Portuguese interfaces

# 🚀 Usage
For Most Users (Recommended) - Using Pre-built Binaries:

1. Go to the Releases section of this repository
2. Download the appropriate executable for your system
3. (Optional) Go to SteamGridDB website, create an account and get your API KEYS
4. Run the Executable:

        Windows: Double-click PS2_OSD-XMB_Art_Fetcher.exe

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
    pip install pyinstaller customtkinter Pillow requests PyYAML pycdlib

# Building executable on Windows
    pyinstaller --onefile --windowed --add-data "logo.png;." --name "PS2_OSD-XMB_Art_Fetcher" PS2_OSD-XMB_Art_Fetcher_GUI.py

# Building executable on macOS or Linux
    pyinstaller --onefile --windowed --add-data "logo.png:." --name "PS2_OSD-XMB_Art_Fetcher" PS2_OSD-XMB_Art_Fetcher_GUI.py

# 🤝 Contributing

Contributions are welcome! Feel free to:

- Report bugs and issues
- Suggest new features
- Submit pull requests
- Improve documentation

# ⚠️ Notes

The first run will take longer as it builds the cache.

Some rare games might not be found in the databases.

Artwork quality and accuracy depends on Launchbox Games Database's files and/or SteamGridDB's community submissions.

# 🔗 Links

Launchbox Games Database: https://gamesdb.launchbox-app.com/

SteamGridDB: https://www.steamgriddb.com/

PCSX2 - PS2 emulator project: https://github.com/PCSX2/pcsx2

OSD-XMB - PS2 XMB: https://github.com/HiroTex/OSD-XMB
