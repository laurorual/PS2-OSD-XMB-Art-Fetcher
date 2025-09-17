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
import threading
import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path
from io import BytesIO
from difflib import SequenceMatcher
from PIL import Image

# --- SCRIPT CONFIGURATION & HELPER FUNCTION ---

# Helper function to find bundled assets
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # If not bundled, use the normal path
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# Suppress the specific deprecation warning
warnings.filterwarnings("ignore", category=DeprecationWarning, message="Testing an element's truth value")

CACHE_FILE = "cache.json"
LOG_FILE = "log.txt"
CONFIG_FILE = "config.json"
METADATA_URL = "https://gamesdb.launchbox-app.com/Metadata.zip"

LANGUAGES = {
    "pt": {
        "title": "OSD-XMB Art Fetcher",
        "choose_lang": "Selecione o idioma / Select language:\n1 - Português\n2 - English\nEscolha: ",
        "invalid_lang": "Opção inválida, padrão Português selecionado.",
        "ask_root": "Diretório raiz contendo as pastas 'OSDXMB' e 'DVD':",
        "browse": "Procurar...",
        "missing_folders_title": "Erro de Diretório",
        "missing_folders": "Erro: As pastas 'OSDXMB' e 'DVD' devem existir dentro do diretório fornecido.",
        "ask_api_key": "Sua API Key do SteamGridDB (Opcional):",
        "api_key_optional": "Pressione Enter para pular ou digite sua API e pressione Enter.",
        "process_start": "Iniciar Escaneamento",
        "process_stop": "Parar",
        "process_running": "Escaneando...",
        "process_end": "Processo concluído. Verifique o log para detalhes.",
        "use_saved_config_title": "Configuração Encontrada",
        "use_saved_config": "Deseja usar o diretório e API KEY salvos?\nDiretório: {saved_root}\nAPI Key: {saved_api_key}",
        "config_saved": "Configuração salva para próxima execução.",
        "summary_title": "=== RESUMO DO PROCESSAMENTO ===",
        "successful_games": "Jogos com arte baixada com sucesso:",
        "failed_games": "Jogos sem arte disponível:",
        "total_processed": "Total de ISOs processados: {}",
        "success_count": "Artes baixadas com sucesso: {}",
        "failed_count": "Artes não encontradas: {}",
        "exclude_prompt_title": "Excluir Jogos Falhados?",
        "exclude_prompt": "Deseja adicionar os jogos sem arte à lista de exclusão para não serem escaneados no futuro?",
        "excluded_added": "Jogos adicionados à lista de exclusão.",
        "downloading_metadata": "Baixando Metadata.xml...",
        "metadata_download_failed": "Falha ao baixar Metadata.xml. O aplicativo continuará sem ele.",
        "yes": "Sim",
        "no": "Não",
        "ok": "OK",
    },
    "en": {
        "title": "OSD-XMB Art Fetcher",
        "choose_lang": "Select language:\n1 - Portuguese\n2 - English\nChoice: ",
        "invalid_lang": "Invalid option, defaulting to English.",
        "ask_root": "Root directory containing 'OSDXMB' and 'DVD' folders:",
        "browse": "Browse...",
        "missing_folders_title": "Directory Error",
        "missing_folders": "Error: The 'OSDXMB' and 'DVD' folders must exist inside the provided directory.",
        "ask_api_key": "Your SteamGridDB API Key (Optional):",
        "api_key_optional": "Press Enter to skip or type your API key and press Enter.",
        "process_start": "Start Scan",
        "process_stop": "Stop",
        "process_running": "Scanning...",
        "process_end": "Process finished. Check the log for details.",
        "use_saved_config_title": "Configuration Found",
        "use_saved_config": "Use saved directory and API KEY?\nDirectory: {saved_root}\nAPI Key: {saved_api_key}",
        "config_saved": "Configuration saved for the next execution.",
        "summary_title": "=== PROCESSING SUMMARY ===",
        "successful_games": "Games with art successfully downloaded:",
        "failed_games": "Games without available art:",
        "total_processed": "Total ISOs processed: {}",
        "success_count": "Art successfully downloaded: {}",
        "failed_count": "Art not found: {}",
        "exclude_prompt_title": "Exclude Failed Games?",
        "exclude_prompt": "Do you want to add games without art to the exclusion list to skip them in future scans?",
        "excluded_added": "Games added to the exclusion list.",
        "downloading_metadata": "Downloading Metadata.xml...",
        "metadata_download_failed": "Failed to download Metadata.xml. The app will continue without it.",
        "yes": "Yes",
        "no": "No",
        "ok": "OK",
    }
}

class ToplevelDialog(ctk.CTkToplevel):
    """A generic dialog window for pop-ups."""
    def __init__(self, parent, title, message, buttons):
        super().__init__(parent)
        self.transient(parent)
        self.title(title)
        self.geometry("400x150")
        self.result = None
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        main_frame = ctk.CTkFrame(self)
        main_frame.pack(expand=True, fill="both", padx=10, pady=10)

        label = ctk.CTkLabel(main_frame, text=message, wraplength=380)
        label.pack(expand=True, fill="both", padx=10, pady=10)

        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(pady=(0, 10))

        for text, value in buttons.items():
            button = ctk.CTkButton(button_frame, text=text, command=lambda v=value: self._set_result(v))
            button.pack(side="left", padx=5)
        
        self.grab_set() # Make the dialog modal
        self.wait_window()

    def _set_result(self, result):
        self.result = result
        self.destroy()

    def _on_closing(self):
        self.result = None # Default result if window is closed
        self.destroy()

class App(ctk.CTk):
    
    def __init__(self):
        super().__init__()
        
        self.title("PS2 OSD-XMB Art Fetcher")
        self.geometry("800x600")
        ctk.set_appearance_mode("System")
        
        self.L = LANGUAGES["en"] # Default language
        self.scan_thread = None
        self.stop_scan = threading.Event()

        # --- Main Layout ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1) # Log text area row

        # 1. Logo
        try:
            # Use the helper function to find the logo
            logo_path = resource_path("logo.png")
            logo_image = ctk.CTkImage(light_image=Image.open(logo_path),
                                    dark_image=Image.open(logo_path),
                                    size=(348, 150))
            self.logo_label = ctk.CTkLabel(self, image=logo_image, text="")
            self.logo_label.grid(row=0, column=0, pady=10)
        except FileNotFoundError:
            self.logo_label = ctk.CTkLabel(self, text="[Logo Image Not Found: logo.png]", height=150)
            self.logo_label.grid(row=0, column=0, pady=10)

        # --- Input Frame ---
        input_frame = ctk.CTkFrame(self)
        input_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        input_frame.grid_columnconfigure(1, weight=1)

        # 2. Root Directory
        self.root_label = ctk.CTkLabel(input_frame, text=self.L["ask_root"])
        self.root_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.root_entry = ctk.CTkEntry(input_frame)
        self.root_entry.grid(row=0, column=1, padx=(0, 10), pady=5, sticky="ew")

        self.browse_button = ctk.CTkButton(input_frame, text=self.L["browse"], width=100, command=self._browse_directory)
        self.browse_button.grid(row=0, column=2, padx=(0, 10), pady=5)
        
        # 3. API Key
        self.api_key_label = ctk.CTkLabel(input_frame, text=self.L["ask_api_key"])
        self.api_key_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        self.api_key_entry = ctk.CTkEntry(input_frame)
        self.api_key_entry.grid(row=1, column=1, columnspan=2, padx=(0, 10), pady=5, sticky="ew")

        # --- Control Frame (Start Button & Language) ---
        control_frame = ctk.CTkFrame(self)
        control_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        control_frame.grid_columnconfigure(0, weight=1)
        control_frame.grid_columnconfigure(1, weight=1)

        self.start_button = ctk.CTkButton(control_frame, text=self.L["process_start"], command=self._start_scan_thread)
        self.start_button.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        # 5. Language Dropdown
        self.lang_menu = ctk.CTkOptionMenu(control_frame, values=["English", "Português"], command=self._change_language)
        self.lang_menu.set("English")
        self.lang_menu.grid(row=0, column=1, padx=10, pady=10, sticky="e")

        # 4. Progress Text Field
        self.log_textbox = ctk.CTkTextbox(self, state="disabled")
        self.log_textbox.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="nsew")

        # Initial configuration check after the main window is created
        self.after(100, self._check_initial_config)
    
    # --- GUI Interaction Methods ---
    
    def _browse_directory(self):
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.root_entry.delete(0, "end")
            self.root_entry.insert(0, dir_path)

    def _change_language(self, choice):
        lang_code = "pt" if choice == "Português" else "en"
        self.L = LANGUAGES[lang_code]
        self._update_ui_text()

    def _update_ui_text(self):
        """Updates all text elements in the GUI to the current language."""
        self.title(self.L["title"])
        self.root_label.configure(text=self.L["ask_root"])
        self.api_key_label.configure(text=self.L["ask_api_key"])
        self.browse_button.configure(text=self.L["browse"])
        # Update start button text based on its state
        if self.scan_thread and self.scan_thread.is_alive():
             self.start_button.configure(text=self.L["process_running"])
        else:
             self.start_button.configure(text=self.L["process_start"])


    def _log_message(self, message):
        """Appends a message to the log textbox in a thread-safe way."""
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message + "\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")
        # Also write to the log file
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(message + "\n")

    def _show_popup(self, title_key, message_key, buttons, format_vars=None):
        """Helper to show a ToplevelDialog."""
        title = self.L[title_key]
        message = self.L[message_key]
        if format_vars:
            message = message.format(**format_vars)
        
        dialog_buttons = {self.L.get(k, k): v for k, v in buttons.items()}
        
        dialog = ToplevelDialog(self, title, message, dialog_buttons)
        return dialog.result

    # --- Threading and Scan Logic ---

    def _start_scan_thread(self):
        if self.scan_thread and self.scan_thread.is_alive():
            return # Don't start a new scan if one is running

        self.stop_scan.clear()
        self.scan_thread = threading.Thread(target=self._run_scan_logic, daemon=True)
        self.scan_thread.start()
        
        self.start_button.configure(text=self.L["process_running"], state="disabled")

    def _check_initial_config(self):
        config = self._load_config()
        saved_root = config.get('root_directory')
        saved_api_key = config.get('api_key')

        if saved_root and os.path.exists(saved_root):
            masked_key = (saved_api_key[:5] + '...') if saved_api_key and len(saved_api_key) > 5 else (saved_api_key or "None")
            format_vars = {"saved_root": saved_root, "saved_api_key": masked_key}
            
            result = self._show_popup("use_saved_config_title", "use_saved_config", {"yes": True, "no": False}, format_vars)

            if result:
                self.root_entry.insert(0, saved_root)
                if saved_api_key:
                    self.api_key_entry.insert(0, saved_api_key)

    def _run_scan_logic(self):
        """This is the main logic from your original script, adapted for the GUI."""
        
        # Clear log file and textbox for new scan
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")

        # --- Get inputs from GUI ---
        root = self.root_entry.get()
        api_key = self.api_key_entry.get().strip() or None
        
        # --- Save config ---
        config = {'root_directory': root, 'api_key': api_key}
        self._save_config(config)
        self.after(0, self._log_message, self.L["config_saved"])

        root_path = Path(root)
        if not (root_path / "OSDXMB").exists() or not (root_path / "DVD").exists():
            self.after(0, self._show_popup, "missing_folders_title", "missing_folders", {"ok": True})
            self.after(0, lambda: self.start_button.configure(text=self.L["process_start"], state="normal"))
            return

        self.after(0, self._log_message, self.L["process_start"])
        self.after(0, self._log_message, "=== PS2 ISO Scan Started ===")
        
        # --- Metadata Download ---
        self.after(0, self._log_message, self.L["downloading_metadata"])
        if not self._download_metadata():
            self.after(0, self._log_message, self.L["metadata_download_failed"])

        # --- Main processing loop ---
        cache = self._load_cache()
        successful_games = []
        failed_games_info = [] # Store tuple of (display_name, iso_filename)

        dvd_path = root_path / "DVD"
        iso_files = [f for f in dvd_path.glob("*.iso") if f.name not in cache.get("excluded_files", [])]
        total_isos = len(iso_files)

        for iso_file in iso_files:
            filename = iso_file.name
            
            # Check cache
            if filename in cache.get("scanned_files", {}):
                entry = cache["scanned_files"][filename]
                if entry["status"] == "OK":
                    self.after(0, self._log_message, f"Skipping {filename} - already processed successfully")
                    successful_games.append(f"{entry.get('game_name', 'Unknown')} (GameID: {entry['gameid']})")
                    continue

            self.after(0, self._log_message, f"Processing ISO: {filename}")
            original_gameid = self._extract_gameid_from_iso(iso_file)
            if not original_gameid:
                self.after(0, self._log_message, f"Failed to extract GameID from {filename}")
                failed_games_info.append((f"{filename} (Failed to extract GameID)", filename))
                cache["scanned_files"][filename] = {"status": "BAD", "gameid": "UNKNOWN", "reason": "Failed to extract GameID"}
                self._save_cache(cache)
                continue

            name = self._lookup_game_name(original_gameid)
            if not name:
                self.after(0, self._log_message, f"GameID {original_gameid} not found in GameIndex for {filename}")
                failed_games_info.append((f"{filename} (GameID: {original_gameid} - Not found in GameIndex)", filename))
                cache["scanned_files"][filename] = {"status": "BAD", "gameid": original_gameid, "reason": "GameID not found"}
                self._save_cache(cache)
                continue
            
            art_path = root_path / "OSDXMB" / "ART" / original_gameid
            art_path.mkdir(parents=True, exist_ok=True)

            logo_url, hero_url = self._fetch_sgdb_images(name, api_key)
            logo_success, hero_success = False, False

            if logo_url:
                try:
                    r = requests.get(logo_url)
                    with open(art_path / "ICON0.png", "wb") as f: f.write(r.content)
                    self.after(0, self._log_message, f"Saved ICON0.png for {name} [{original_gameid}]")
                    logo_success = True
                except Exception as e:
                    self.after(0, self._log_message, f"[ERROR] Failed to save ICON0.png for {name}: {e}")
            
            if hero_url:
                try:
                    r = requests.get(hero_url)
                    with open(art_path / "PIC1.png", "wb") as f: f.write(r.content)
                    self.after(0, self._log_message, f"Saved PIC1.png for {name} [{original_gameid}]")
                    hero_success = True
                except Exception as e:
                    self.after(0, self._log_message, f"[ERROR] Failed to save PIC1.png for {name}: {e}")

            if logo_success or hero_success:
                successful_games.append(f"{name} (GameID: {original_gameid})")
                cache["scanned_files"][filename] = {"status": "OK", "gameid": original_gameid, "game_name": name}
            else:
                failed_games_info.append((f"{name} (GameID: {original_gameid} - No art found)", filename))
                cache["scanned_files"][filename] = {"status": "BAD", "gameid": original_gameid, "game_name": name, "reason": "No art found"}
            
            self._save_cache(cache)

        self.after(0, self._log_message, "=== PS2 ISO Scan Finished ===")
        self.after(0, self._log_message, self.L["process_end"])

        # --- Final Summary & Exclude Prompt ---
        self.after(0, self._display_summary_and_finish, total_isos, successful_games, failed_games_info)

    def _display_summary_and_finish(self, total_isos, successful_games, failed_games_info):
        """Displays the final summary and handles the exclude prompt."""
        # Handle exclusion prompt
        if failed_games_info:
            result = self._show_popup("exclude_prompt_title", "exclude_prompt", {"yes": True, "no": False})
            if result:
                cache = self._load_cache()
                for _, iso_filename in failed_games_info:
                    if iso_filename not in cache["excluded_files"]:
                        cache["excluded_files"].append(iso_filename)
                self._save_cache(cache)
                self._log_message(self.L["excluded_added"])
        
        # Display summary in log
        self._log_message("\n" + self.L["summary_title"])
        self._log_message(self.L["total_processed"].format(total_isos))
        self._log_message(self.L["success_count"].format(len(successful_games)))
        self._log_message(self.L["failed_count"].format(len(failed_games_info)))

        if successful_games:
            self._log_message("\n" + self.L["successful_games"])
            for game in successful_games:
                self._log_message(f"  ✓ {game}")
        
        if failed_games_info:
            self._log_message("\n" + self.L["failed_games"])
            for game_display, _ in failed_games_info:
                self._log_message(f"  ✗ {game_display}")
        
        self.start_button.configure(text=self.L["process_start"], state="normal")


    # --- BACKEND LOGIC (from original script, as methods of the class) ---
    
    def _log(self, message):
        self.after(0, self._log_message, message)

    def _load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f: return json.load(f)
            except json.JSONDecodeError: return {}
        return {}

    def _save_config(self, config):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
    
    def _load_cache(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                    if "scanned_files" not in cache_data: cache_data["scanned_files"] = {}
                    if "excluded_files" not in cache_data: cache_data["excluded_files"] = []
                    return cache_data
            except json.JSONDecodeError: return {"scanned_files": {}, "excluded_files": []}
        return {"scanned_files": {}, "excluded_files": []}

    def _save_cache(self, cache):
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=4)

    def _download_metadata(self):
        if os.path.exists("Metadata.xml"):
            self._log("Metadata.xml already exists, skipping download.")
            return True
        self._log("Downloading Metadata.zip...")
        try:
            response = requests.get(METADATA_URL)
            if response.status_code != 200:
                self._log(f"[ERROR] Failed to download Metadata.zip (status {response.status_code})")
                return False
            with zipfile.ZipFile(BytesIO(response.content)) as zip_ref:
                for file_info in zip_ref.infolist():
                    if file_info.filename.endswith('Metadata.xml'):
                        zip_ref.extract(file_info)
                        self._log("Extracted Metadata.xml from zip.")
                        return True
                self._log("[ERROR] Metadata.xml not found in the downloaded zip file.")
                return False
        except Exception as e:
            self._log(f"[ERROR] Failed to download or extract Metadata.zip: {e}")
            return False

    def _string_similarity(self, a, b):
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def _find_game_in_metadata(self, game_name):
        if not os.path.exists("Metadata.xml"):
            return None
        try:
            tree = ET.parse("Metadata.xml")
            root = tree.getroot()
            best_match, highest_similarity = None, 0
            for game in root.findall(".//Game"):
                name_elem = game.find("Name")
                if name_elem is not None and name_elem.text is not None:
                    similarity = self._string_similarity(game_name, name_elem.text)
                    if similarity > highest_similarity and similarity > 0.7:
                        highest_similarity, best_match = similarity, game
            if best_match:
                db_id_elem = best_match.find("DatabaseID")
                if db_id_elem is not None and db_id_elem.text is not None:
                    matched_name = best_match.find("Name").text
                    self._log(f"Found match in Metadata.xml: {game_name} -> {matched_name} (similarity: {highest_similarity:.2f})")
                    return db_id_elem.text
            return None
        except Exception as e:
            self._log(f"[ERROR] Failed to parse Metadata.xml: {e}")
            return None

    def _find_images_in_metadata(self, database_id):
        if not os.path.exists("Metadata.xml"): return None, None
        try:
            tree = ET.parse("Metadata.xml")
            root = tree.getroot()
            logo_url, hero_url = None, None
            base_url = "https://images.launchbox-app.com//"
            
            for img_type, desired_text in [("logo", "Clear Logo"), ("hero", "Fanart - Background"), ("hero_fallback", "Screenshot")]:
                for game_image in root.findall(".//GameImage"):
                    if (game_image.find("DatabaseID").text == database_id and 
                        game_image.find("Type").text == desired_text and 
                        not (img_type == "logo" and logo_url) and 
                        not (img_type.startswith("hero") and hero_url)):
                        
                        url = base_url + game_image.find("FileName").text
                        if img_type == "logo": logo_url = url
                        else: hero_url = url
                        break # Found one of this type, move on
            return logo_url, hero_url
        except Exception as e:
            self._log(f"[ERROR] Failed to search images in Metadata.xml: {e}")
            return None, None

    def _fetch_sgdb_images(self, game_name, api_key):
        database_id = self._find_game_in_metadata(game_name)
        logo_url, hero_url = None, None
        if database_id:
            logo_url, hero_url = self._find_images_in_metadata(database_id)
        if api_key:
            if not logo_url: logo_url = self._fetch_sgdb_image_api(game_name, "logos", api_key)
            if not hero_url: hero_url = self._fetch_sgdb_image_api(game_name, "heroes", api_key)
        if not logo_url: self._log(f"[WARN] No logo found for {game_name}")
        if not hero_url: self._log(f"[WARN] No hero found for {game_name}")
        return logo_url, hero_url

    def _fetch_sgdb_image_api(self, game_name, category, api_key):
        try:
            headers = {"Authorization": f"Bearer {api_key}"}
            search_url = f"https://www.steamgriddb.com/api/v2/search/autocomplete/{game_name}"
            r_search = requests.get(search_url, headers=headers)
            if r_search.status_code != 200: return None
            data = r_search.json().get("data")
            if not data: return None
            
            game_id = data[0]["id"]
            img_url = f"https://www.steamgriddb.com/api/v2/{category}/game/{game_id}"
            r_img = requests.get(img_url, headers=headers)
            if r_img.status_code != 200: return None
            images = r_img.json().get("data")
            if not images: return None
            
            self._log(f"Fetched {category} for {game_name} from SteamGridDB.")
            return images[0]["url"]
        except Exception:
            return None

    def _extract_gameid_from_iso(self, iso_path):
        iso = pycdlib.PyCdlib()
        try:
            iso.open(str(iso_path))
            buf = BytesIO()
            iso.get_file_from_iso_fp(buf, iso_path="/SYSTEM.CNF;1")
            text = buf.getvalue().decode("utf-8", errors="ignore")
            for line in text.splitlines():
                if "BOOT2 = cdrom0:" in line:
                    gameid = line.strip().split("cdrom0:\\")[-1].replace(";1", "")
                    self._log(f"Extracted GameID {gameid} from {iso_path.name}")
                    return gameid
        except Exception as e:
            self._log(f"[ERROR] Could not extract GameID from {iso_path.name}: {e}")
        finally:
            iso.close()
        return None

    def _lookup_game_name(self, gameid):
        clean_gameid = gameid.replace('.', '').replace('_', '-')
        url = "https://raw.githubusercontent.com/PCSX2/pcsx2/refs/heads/master/bin/resources/GameIndex.yaml"
        try:
            r = requests.get(url)
            if r.status_code != 200: return None
            data = yaml.safe_load(r.text)
            if clean_gameid in data:
                name = data[clean_gameid].get('name')
                self._log(f"Found game name for {clean_gameid}: {name}")
                return name
            self._log(f"[WARN] GameID {clean_gameid} not found in GameIndex.yaml")
            return None
        except Exception as e:
            self._log(f"[ERROR] Exception while looking up game name for {clean_gameid}: {e}")
            return None


if __name__ == "__main__":
    app = App()
    app.mainloop()