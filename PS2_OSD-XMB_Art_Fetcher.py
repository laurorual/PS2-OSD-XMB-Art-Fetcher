import os
import sys
import requests
import pycdlib
import re
import json
import yaml
import xml.etree.ElementTree as ET
import warnings
import zipfile
from pathlib import Path
from io import BytesIO
from difflib import SequenceMatcher

# Suppress the specific deprecation warning
warnings.filterwarnings("ignore", category=DeprecationWarning, message="Testing an element's truth value")

CACHE_FILE = "cache.json"
LOG_FILE = "log.txt"
CONFIG_FILE = "config.json"
METADATA_URL = "https://gamesdb.launchbox-app.com/Metadata.zip"

# Clear screen function
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

# Load config
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

# Save config
def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

# Load cache with new structure
def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
                # Ensure the cache has the proper structure
                if "scanned_files" not in cache_data:
                    cache_data["scanned_files"] = {}
                if "excluded_files" not in cache_data:
                    cache_data["excluded_files"] = []
                return cache_data
        except json.JSONDecodeError:
            # Return empty cache structure if file is corrupted
            return {"scanned_files": {}, "excluded_files": []}
    return {"scanned_files": {}, "excluded_files": []}

# Save cache
def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=4)

# Function to download and extract Metadata.xml
def download_metadata():
    if os.path.exists("Metadata.xml"):
        log("Metadata.xml already exists, skipping download.")
        return True
    
    log("Downloading Metadata.zip...")
    try:
        response = requests.get(METADATA_URL)
        if response.status_code != 200:
            log(f"[ERROR] Failed to download Metadata.zip (status {response.status_code})")
            return False
        
        # Save the zip file
        with open("Metadata.zip", "wb") as f:
            f.write(response.content)
        
        # Extract only Metadata.xml from the zip
        with zipfile.ZipFile("Metadata.zip", 'r') as zip_ref:
            # Look for Metadata.xml in the zip file
            for file_info in zip_ref.infolist():
                if file_info.filename.endswith('Metadata.xml'):
                    # Extract the file
                    zip_ref.extract(file_info)
                    log("Extracted Metadata.xml from zip.")
                    break
            else:
                log("[ERROR] Metadata.xml not found in the downloaded zip file.")
                return False
        
        # Clean up: delete the zip file
        os.remove("Metadata.zip")
        log("Deleted Metadata.zip after extraction.")
        return True
        
    except Exception as e:
        log(f"[ERROR] Failed to download or extract Metadata.zip: {e}")
        # Clean up if possible
        if os.path.exists("Metadata.zip"):
            try:
                os.remove("Metadata.zip")
            except:
                pass
        return False

cache = load_cache()
config = load_config()

# Language setup
LANGUAGES = {
    "pt": {
        "choose_lang": "Selecione o idioma / Select language:\n1 - Português\n2 - English\nEscolha: ",
        "invalid_lang": "Opção inválida, padrão Português selecionado.",
        "ask_root": "Digite o diretório raiz que contém as pastas 'OSDXMB' e 'DVD': ",
        "missing_folders": "Erro: As pastas 'OSDXMB' y 'DVD' devem existir dentro do diretório fornecido.",
        "ask_api_key": ("Digite sua SteamGridDB API Key: ",
                         "Este aplicativo utiliza a API do SteamGridDB para obter as artes caso não consiga obter de outras formas. Você pode obter sua API Key gratuitamente em https://www.steamgriddb.com/profile/preferences na seção 'API Key'."),
        "api_key_optional": "A API Key é OPCIONAL. Pressione Enter para pular ou digite sua API e pressione Enter: ",
        "process_start": "Iniciando escaneamento...",
        "process_end": "Processo concluído. Verifique o arquivo log.txt para detalhes.",
        "use_saved_config": "Deseja usar o diretório e API KEY salvos?\nDiretório salvo: {saved_root}\nAPI Key salva: {saved_api_key}\n1 - Sim\n2 - Não, usar novos\nEscolha: ",
        "no_saved_config": "Nenhuma configuração salva encontrada.",
        "config_saved": "Configuração salva para próxima execução.",
        "summary_title": "=== RESUMO DO PROCESSAMENTO ===",
        "successful_games": "Jogos com arte baixada com sucesso:",
        "failed_games": "Jogos sem arte disponível:",
        "press_any_key": "Pressione qualquer tecla para sair...",
        "total_processed": "Total de ISOs processados: {}",
        "success_count": "Artes baixadas com sucesso: {}",
        "failed_count": "Artes não encontradas: {}",
        "exclude_prompt": "\nDeseja adicionar os jogos sem arte à lista de exclusão?\n1 - Sim\n2 - Não\nEscolha: ",
        "excluded_added": "Jogos adicionados à lista de exclusão.",
        "downloading_metadata": "Baixando Metadata.xml...",
        "metadata_download_failed": "Falha ao baixar Metadata.xml. O aplicativo continuará sem ele."
    },
    "en": {
        "choose_lang": "Select language:\n1 - Portuguese\n2 - English\nChoice: ",
        "invalid_lang": "Invalid option, defaulting to English.",
        "ask_root": "Enter the root directory containing 'OSDXMB' and 'DVD' folders: ",
        "missing_folders": "Error: The 'OSDXMB' and 'DVD' folders must exist inside the provided directory.",
        "ask_api_key": ("Enter your SteamGridDB API Key: ",
                         "This app uses the SteamGridDB API to fetch artwork if it cannot be obtained through other means. You can get your API Key for free at https://www.steamgriddb.com/profile/preferences under the 'API Key' section."),
        "api_key_optional": "API Key is OPTIONAL. Press Enter to skip or type your API key and press Enter: ",
        "process_start": "Starting scan...",
        "process_end": "Process finished. Check log.txt for details.",
        "use_saved_config": "Use saved directory and API KEY?\nSaved directory: {saved_root}\nSaved API Key: {saved_api_key}\n1 - Yes\n2 - No, use new ones\nChoice: ",
        "no_saved_config": "No saved configuration found.",
        "config_saved": "Configuration saved for next execution.",
        "summary_title": "=== PROCESSING SUMMARY ===",
        "successful_games": "Games with art successfully downloaded:",
        "failed_games": "Games without available art:",
        "press_any_key": "Press any key to exit...",
        "total_processed": "Total ISOs processed: {}",
        "success_count": "Art successfully downloaded: {}",
        "failed_count": "Art not found: {}",
        "exclude_prompt": "\nDo you want to add games without art to the exclusion list?\n1 - Yes\n2 - No\nChoice: ",
        "excluded_added": "Games added to exclusion list.",
        "downloading_metadata": "Downloading Metadata.xml...",
        "metadata_download_failed": "Failed to download Metadata.xml. The app will continue without it."
    }
}

# Clear screen at start
clear_screen()

# Choose language
choice = input(LANGUAGES["pt"]["choose_lang"])
clear_screen()

if choice.strip() == "2":
    lang = "en"
elif choice.strip() == "1":
    lang = "pt"
else:
    print(LANGUAGES["en"]["invalid_lang"])
    lang = "en"

L = LANGUAGES[lang]

# Logger (always English)
def log(message):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(message + "\n")
    print(message)

# Function to calculate string similarity
def string_similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

# Function to parse Metadata.xml and find matching game
def find_game_in_metadata(game_name):
    if not os.path.exists("Metadata.xml"):
        log(f"[INFO] Metadata.xml not found, skipping local lookup for {game_name}")
        return None
    
    try:
        tree = ET.parse("Metadata.xml")
        root = tree.getroot()
        
        best_match = None
        highest_similarity = 0
        
        for game in root.findall(".//Game"):
            name_elem = game.find("Name")
            if name_elem is not None and name_elem.text is not None:
                similarity = string_similarity(game_name, name_elem.text)
                if similarity > highest_similarity and similarity > 0.7:  # 70% similarity threshold
                    highest_similarity = similarity
                    best_match = game
        
        if best_match:
            database_id_elem = best_match.find("DatabaseID")
            if database_id_elem is not None and database_id_elem.text is not None:
                matched_name = best_match.find("Name")
                matched_name_text = matched_name.text if matched_name is not None and matched_name.text is not None else "Unknown"
                log(f"Found match in Metadata.xml: {game_name} -> {matched_name_text} (similarity: {highest_similarity:.2f})")
                return database_id_elem.text
        
        log(f"[INFO] No match found in Metadata.xml for {game_name}")
        return None
    except Exception as e:
        log(f"[ERROR] Failed to parse Metadata.xml: {e}")
        return None

# Function to find images in Metadata.xml by database ID
def find_images_in_metadata(database_id):
    if not os.path.exists("Metadata.xml"):
        return None, None
    
    try:
        tree = ET.parse("Metadata.xml")
        root = tree.getroot()
        
        logo_url = None
        hero_url = None
        
        # Find logo (Clear Logo)
        for game_image in root.findall(".//GameImage"):
            db_id_elem = game_image.find("DatabaseID")
            type_elem = game_image.find("Type")
            file_elem = game_image.find("FileName")
            
            if (db_id_elem is not None and db_id_elem.text is not None and db_id_elem.text == database_id and
                type_elem is not None and type_elem.text is not None and type_elem.text == "Clear Logo" and
                file_elem is not None and file_elem.text is not None and not logo_url):
                logo_url = f"https://images.launchbox-app.com//{file_elem.text}"
        
        # Find hero (Fanart - Background)
        for game_image in root.findall(".//GameImage"):
            db_id_elem = game_image.find("DatabaseID")
            type_elem = game_image.find("Type")
            file_elem = game_image.find("FileName")
            
            if (db_id_elem is not None and db_id_elem.text is not None and db_id_elem.text == database_id and
                type_elem is not None and type_elem.text is not None and type_elem.text == "Fanart - Background" and
                file_elem is not None and file_elem.text is not None and not hero_url):
                hero_url = f"https://images.launchbox-app.com//{file_elem.text}"
        
        # If no hero found, look for any screenshot
        if not hero_url:
            for game_image in root.findall(".//GameImage"):
                db_id_elem = game_image.find("DatabaseID")
                type_elem = game_image.find("Type")
                file_elem = game_image.find("FileName")
                
                if (db_id_elem is not None and db_id_elem.text is not None and db_id_elem.text == database_id and
                    type_elem is not None and type_elem.text is not None and "Screenshot" in type_elem.text and
                    file_elem is not None and file_elem.text is not None and not hero_url):
                    hero_url = f"https://images.launchbox-app.com//{file_elem.text}"
        
        return logo_url, hero_url
    except Exception as e:
        log(f"[ERROR] Failed to search for images in Metadata.xml: {e}")
        return None, None

# New implementation of fetch_sgdb_image with fallback
def fetch_sgdb_images(game_name, api_key):
    # Try to find the game in Metadata.xml first
    database_id = find_game_in_metadata(game_name)
    logo_url, hero_url = None, None
    
    if database_id:
        # Try to find both images in Metadata.xml
        logo_url, hero_url = find_images_in_metadata(database_id)
        
        if logo_url:
            log(f"Found logo for {game_name} in Metadata.xml: {logo_url}")
        if hero_url:
            log(f"Found hero for {game_name} in Metadata.xml: {hero_url}")
    
    # Fallback to SteamGridDB API if available and needed
    if api_key and (not logo_url or not hero_url):
        log(f"Falling back to SteamGridDB API for {game_name}")
        if not logo_url:
            logo_url = fetch_sgdb_image_api(game_name, "logos", api_key)
        if not hero_url:
            hero_url = fetch_sgdb_image_api(game_name, "heroes", api_key)
    
    if not logo_url:
        log(f"[WARN] No logo found for {game_name}")
    if not hero_url:
        log(f"[WARN] No hero found for {game_name}")
    
    return logo_url, hero_url

# Original implementation as fallback
def fetch_sgdb_image_api(game_name, category, api_key):
    url = f"https://www.steamgriddb.com/api/v2/search/autocomplete/{game_name}"
    headers = {"Authorization": f"Bearer {api_key}"}
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        log(f"[ERROR] SteamGridDB search failed for {game_name} (status {r.status_code})")
        return None

    data = r.json()
    if not data.get("data"):
        log(f"[WARN] No SteamGridDB results found for {game_name}")
        return None

    game_id = data["data"][0]["id"]
    url = f"https://www.steamgriddb.com/api/v2/{category}/game/{game_id}"
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        log(f"[ERROR] Failed to fetch {category} for {game_name} (status {r.status_code})")
        return None

    images = r.json().get("data")
    if not images:
        log(f"[WARN] No {category} images found for {game_name}")
        return None

    log(f"Fetched {category} for {game_name} from SteamGridDB: {images[0]['url']}")
    return images[0]["url"]

# Extract GameID from ISO
def extract_gameid_from_iso(iso_path):
    iso = pycdlib.PyCdlib()
    try:
        iso.open(str(iso_path))
        buf = BytesIO()
        iso.get_file_from_iso_fp(buf, iso_path="/SYSTEM.CNF;1")
        buf.seek(0)
        text = buf.read().decode("utf-8", errors="ignore")
        for line in text.splitlines():
            if "BOOT2 = cdrom0:" in line:
                # Extract the original GameID with dots and underscores
                original_gameid = line.strip().split("cdrom0:\\")[-1].replace(";1", "")
                log(f"Extracted GameID {original_gameid} from {iso_path.name}")
                return original_gameid
    except Exception as e:
        log(f"[ERROR] Could not extract GameID from {iso_path.name}: {e}")
    finally:
        try:
            iso.close()
        except:
            pass
    return None

# Create a clean GameID for GameIndex.yaml lookup
def clean_gameid_for_lookup(gameid):
    # Remove dots and replace underscores with hyphens for GameIndex.yaml lookup
    return gameid.replace('.', '').replace('_', '-')

# Lookup game name from GameIndex.yaml
def lookup_game_name(gameid):
    # Clean the GameID for lookup in GameIndex.yaml
    clean_gameid = clean_gameid_for_lookup(gameid)
    
    url = "https://raw.githubusercontent.com/PCSX2/pcsx2/refs/heads/master/bin/resources/GameIndex.yaml"
    try:
        r = requests.get(url)
        if r.status_code != 200:
            log(f"[ERROR] Failed to fetch GameIndex.yaml (status {r.status_code})")
            return None

        # Load the YAML content
        data = yaml.safe_load(r.text)
        
        # The YAML structure is a dictionary where keys are GameIDs
        # and values contain game information including the name
        if clean_gameid in data:
            name = data[clean_gameid].get('name')
            if name:
                log(f"Found game name for {clean_gameid}: {name}")
                return name
        
        log(f"[WARN] GameID {clean_gameid} not found in GameIndex.yaml")
        return None

    except Exception as e:
        log(f"[ERROR] Exception while looking up game name for {clean_gameid}: {e}")
        return None

# Main flow
if __name__ == "__main__":
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)

    # Download Metadata.xml if it doesn't exist
    print(L["downloading_metadata"])
    if not download_metadata():
        print(L["metadata_download_failed"])
    clear_screen()  # Clear screen after metadata download

    # Lists to track successful and failed games
    successful_games = []
    failed_games = []

    # Check if we have saved config and ask user if they want to use it
    saved_root = config.get('root_directory')
    saved_api_key = config.get('api_key')
    
    use_saved = False
    
    # Modified condition to only require root directory (API key is optional)
    if saved_root and os.path.exists(saved_root):
        try:
            # Show masked API key for privacy
            masked_api_key = saved_api_key if saved_api_key and len(saved_api_key) <= 5 else (saved_api_key[:5] + '...' if saved_api_key else 'None')
            choice = input(L["use_saved_config"].format(saved_root=saved_root, saved_api_key=masked_api_key))
            clear_screen()
            if choice == "1":
                use_saved = True
                root = saved_root
                api_key = saved_api_key
        except:
            use_saved = False
    
    if not use_saved:
        if not saved_root:
            print(L["no_saved_config"])
        
        root = input(L["ask_root"])
        clear_screen()
        
        # API key is now optional
        api_key = os.getenv("STEAMGRIDDB_API_KEY")
        if not api_key:
            print(L["ask_api_key"][1])
            api_key_input = input(L["api_key_optional"])
            api_key = api_key_input if api_key_input.strip() else None
            clear_screen()
        
        # Save the new configuration
        config['root_directory'] = root
        config['api_key'] = api_key
        save_config(config)
        print(L["config_saved"])

    root_path = Path(root)

    if not (root_path / "OSDXMB").exists() or not (root_path / "DVD").exists():
        print(L["missing_folders"])
        sys.exit(1)

    print(L["process_start"])
    log("=== PS2 ISO Scan Started ===")

    dvd_path = root_path / "DVD"
    
    # Get all ISO files and filter out excluded ones
    iso_files = [iso_file for iso_file in dvd_path.glob("*.iso") 
                if iso_file.name not in cache["excluded_files"]]
    
    total_isos = len(iso_files)
    
    for iso_file in iso_files:
        filename = iso_file.name
        
        # Check if file is already in cache
        if filename in cache["scanned_files"]:
            cache_entry = cache["scanned_files"][filename]
            
            if cache_entry["status"] == "OK":
                log(f"Skipping {filename} - already processed successfully")
                successful_games.append(f"{cache_entry.get('game_name', 'Unknown')} (GameID: {cache_entry['gameid']})")
                continue
            elif cache_entry["status"] == "BAD":
                log(f"Retrying {filename} - previous attempt failed")
                # Continue with processing
            else:
                log(f"Unknown status for {filename} in cache, reprocessing")
        
        log(f"Processing ISO: {filename}")
        original_gameid = extract_gameid_from_iso(iso_file)
        if not original_gameid:
            log(f"Failed to extract GameID from {filename}")
            # Update cache with BAD status
            cache["scanned_files"][filename] = {
                "status": "BAD",
                "gameid": "UNKNOWN",
                "reason": "Failed to extract GameID"
            }
            save_cache(cache)
            failed_games.append(f"{filename} (Failed to extract GameID)")
            continue
        
        name = lookup_game_name(original_gameid)
        if not name:
            log(f"GameID {original_gameid} not found in GameIndex for {filename}")
            # Update cache with BAD status
            cache["scanned_files"][filename] = {
                "status": "BAD",
                "gameid": original_gameid,
                "reason": "GameID not found in GameIndex"
            }
            save_cache(cache)
            failed_games.append(f"{filename} (GameID: {original_gameid} - Not found in GameIndex)")
            continue

        # Use the original GameID (with dots and underscores) for the folder name
        art_path = root_path / "OSDXMB" / "ART" / original_gameid
        art_path.mkdir(parents=True, exist_ok=True)

        # Get both logo and hero URLs at once
        logo_url, hero_url = fetch_sgdb_images(name, api_key)

        logo_success = False
        hero_success = False

        if logo_url:
            try:
                r = requests.get(logo_url)
                with open(art_path / "ICON0.png", "wb") as f:
                    f.write(r.content)
                log(f"Saved ICON0.png for {name} [{original_gameid}]")
                logo_success = True
            except Exception as e:
                log(f"[ERROR] Failed to save ICON0.png for {name}: {e}")

        if hero_url:
            try:
                r = requests.get(hero_url)
                with open(art_path / "PIC1.png", "wb") as f:
                    f.write(r.content)
                log(f"Saved PIC1.png for {name} [{original_gameid}]")
                hero_success = True
            except Exception as e:
                log(f"[ERROR] Failed to save PIC1.png for {name}: {e}")

        if logo_success or hero_success:
            # Update cache with OK status
            cache["scanned_files"][filename] = {
                "status": "OK",
                "gameid": original_gameid,
                "game_name": name
            }
            save_cache(cache)
            successful_games.append(f"{name} (GameID: {original_gameid})")
        else:
            # Update cache with BAD status
            cache["scanned_files"][filename] = {
                "status": "BAD",
                "gameid": original_gameid,
                "game_name": name,
                "reason": "No art found"
            }
            save_cache(cache)
            failed_games.append(f"{name} (GameID: {original_gameid} - No art found)")

    log("=== PS2 ISO Scan Finished ===")
    print(L["process_end"])
    
    # Ask user if they want to add failed games to exclusion list
    if failed_games:
        choice = input(L["exclude_prompt"])
        if choice.strip() == "1":
            for game_info in failed_games:
                # Extract filename from the game info string
                filename_match = re.search(r'^(.*?)\s*\(', game_info)
                if filename_match:
                    filename = filename_match.group(1).strip()
                    if filename not in cache["excluded_files"]:
                        cache["excluded_files"].append(filename)
            
            save_cache(cache)
            print(L["excluded_added"])
    
    # Display summary
    clear_screen()
    print(L["summary_title"])
    print()
    print(L["total_processed"].format(total_isos))
    print(L["success_count"].format(len(successful_games)))
    print(L["failed_count"].format(len(failed_games)))
    print()
    
    if successful_games:
        print(L["successful_games"])
        for game in successful_games:
            print(f"  ✓ {game}")
        print()
    
    if failed_games:
        print(L["failed_games"])
        for game in failed_games:
            print(f"  ✗ {game}")
        print()
    
    # Wait for user input before closing
    input(L["press_any_key"])
    clear_screen()
