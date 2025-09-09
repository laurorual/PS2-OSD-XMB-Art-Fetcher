import os
import sys
import requests
import pycdlib
import re
import json
import yaml
from pathlib import Path
from io import BytesIO

CACHE_FILE = "cache.json"
LOG_FILE = "log.txt"
CONFIG_FILE = "config.json"

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

cache = load_cache()
config = load_config()

# Language setup
LANGUAGES = {
    "pt": {
        "choose_lang": "Selecione o idioma / Select language:\n1 - Português\n2 - English\nEscolha: ",
        "invalid_lang": "Opção inválida, padrão Português selecionado.",
        "ask_root": "Digite o diretório raiz que contém as pastas 'OSDXMB' e 'DVD': ",
        "missing_folders": "Erro: As pastas 'OSDXMB' e 'DVD' devem existir dentro do diretório fornecido.",
        "ask_api_key": ("Digite sua SteamGridDB API Key: ",
                         "Você pode obter sua API Key gratuitamente em https://www.steamgriddb.com/profile/preferences na seção 'API Key'."),
        "process_start": "Iniciando escaneamento...",
        "process_end": "Processo concluído. Verifique o arquivo log.txt para detalhes.",
        "use_saved_config": "Deseja usar o diretório e API KEY salvos?\nDiretório salvo: {saved_root}\n1 - Sim\n2 - Não, usar novos\nEscolha: ",        "no_saved_config": "Nenhuma configuração salva encontrada.",
        "config_saved": "Configuração salva para próxima execução.",
        "summary_title": "=== RESUMO DO PROCESSAMENTO ===",
        "successful_games": "Jogos com arte baixada com sucesso:",
        "failed_games": "Jogos sem arte disponível:",
        "press_any_key": "Pressione qualquer tecla para sair...",
        "total_processed": "Total de ISOs processados: {}",
        "success_count": "Artes baixadas com sucesso: {}",
        "failed_count": "Artes não encontradas: {}",
        "exclude_prompt": "\nDeseja adicionar os jogos sem arte à lista de exclusão?\n1 - Sim\n2 - Não\nEscolha: ",
        "excluded_added": "Jogos adicionados à lista de exclusão."
    },
    "en": {
        "choose_lang": "Select language:\n1 - Portuguese\n2 - English\nChoice: ",
        "invalid_lang": "Invalid option, defaulting to English.",
        "ask_root": "Enter the root directory containing 'OSDXMB' and 'DVD' folders: ",
        "missing_folders": "Error: The 'OSDXMB' and 'DVD' folders must exist inside the provided directory.",
        "ask_api_key": ("Enter your SteamGridDB API Key: ",
                         "You can get your API Key for free at https://www.steamgriddb.com/profile/preferences under the 'API Key' section."),
        "process_start": "Starting scan...",
        "process_end": "Process finished. Check log.txt for details.",
        "use_saved_config": "Use saved directory and API KEY?\nSaved directory: {saved_root}\n1 - Yes\n2 - No, use new ones\nChoice: ",
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
        "excluded_added": "Games added to exclusion list."
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

# Function to fetch SteamGridDB images (without caching)
def fetch_sgdb_image(game_name, category, api_key):
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

    log(f"Fetched {category} for {game_name}: {images[0]['url']}")
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
                gameid = line.strip().split("cdrom0:\\")[-1].replace(";1", "").replace('.', '').replace('_', '-')
                log(f"Extracted GameID {gameid} from {iso_path.name}")
                return gameid
    except Exception as e:
        log(f"[ERROR] Could not extract GameID from {iso_path.name}: {e}")
    finally:
        try:
            iso.close()
        except:
            pass
    return None

# Lookup game name from GameIndex.yaml
def lookup_game_name(gameid):
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
        if gameid in data:
            name = data[gameid].get('name')
            if name:
                log(f"Found game name for {gameid}: {name}")
                return name
        
        log(f"[WARN] GameID {gameid} not found in GameIndex.yaml")
        return None

    except Exception as e:
        log(f"[ERROR] Exception while looking up game name for {gameid}: {e}")
        return None

# Main flow
if __name__ == "__main__":
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)

    # Lists to track successful and failed games
    successful_games = []
    failed_games = []

    # Check if we have saved config and ask user if they want to use it
    saved_root = config.get('root_directory')
    saved_api_key = config.get('api_key')
    
    use_saved = False
    
    if saved_root and saved_api_key:
        try:
            choice = input(L["use_saved_config"].format(saved_root=saved_root))
            clear_screen()
            if choice == "1":
                use_saved = True
                root = saved_root
                api_key = saved_api_key
        except:
            use_saved = False
    
    if not use_saved:
        if not saved_root and not saved_api_key:
            print(L["no_saved_config"])
        
        root = input(L["ask_root"])
        clear_screen()
        api_key = os.getenv("STEAMGRIDDB_API_KEY")
        if not api_key:
            print(L["ask_api_key"][1])
            api_key = input(L["ask_api_key"][0])
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
        gameid = extract_gameid_from_iso(iso_file)
        if not gameid:
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
        
        name = lookup_game_name(gameid)
        if not name:
            log(f"GameID {gameid} not found in GameIndex for {filename}")
            # Update cache with BAD status
            cache["scanned_files"][filename] = {
                "status": "BAD",
                "gameid": gameid,
                "reason": "GameID not found in GameIndex"
            }
            save_cache(cache)
            failed_games.append(f"{filename} (GameID: {gameid} - Not found in GameIndex)")
            continue

        art_path = root_path / "OSDXMB" / "ART" / gameid
        art_path.mkdir(parents=True, exist_ok=True)

        logo_success = False
        hero_success = False

        logo_url = fetch_sgdb_image(name, "logos", api_key)
        if logo_url:
            try:
                r = requests.get(logo_url)
                with open(art_path / "ICON0.png", "wb") as f:
                    f.write(r.content)
                log(f"Saved ICON0.png for {name} [{gameid}]")
                logo_success = True
            except Exception as e:
                log(f"[ERROR] Failed to save ICON0.png for {name}: {e}")

        hero_url = fetch_sgdb_image(name, "heroes", api_key)
        if hero_url:
            try:
                r = requests.get(hero_url)
                with open(art_path / "PIC1.png", "wb") as f:
                    f.write(r.content)
                log(f"Saved PIC1.png for {name} [{gameid}]")
                hero_success = True
            except Exception as e:
                log(f"[ERROR] Failed to save PIC1.png for {name}: {e}")

        if logo_success or hero_success:
            # Update cache with OK status
            cache["scanned_files"][filename] = {
                "status": "OK",
                "gameid": gameid,
                "game_name": name
            }
            save_cache(cache)
            successful_games.append(f"{name} (GameID: {gameid})")
        else:
            # Update cache with BAD status
            cache["scanned_files"][filename] = {
                "status": "BAD",
                "gameid": gameid,
                "game_name": name,
                "reason": "No art found"
            }
            save_cache(cache)
            failed_games.append(f"{name} (GameID: {gameid} - No art found)")

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
