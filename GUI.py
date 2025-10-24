import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
import subprocess
from PIL import Image, ImageTk
import glob
import time
import shutil  # Pour créer le dossier profiles si besoin
from datetime import datetime  # Pour trier les profils par date

# Classe ToolTip pour les info-bulles
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 20  # Position relative au widget
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 1
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)  # Pas de bordures
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT, background="#ffffe0", relief=tk.SOLID, borderwidth=1, font=("Arial", 8))
        label.pack(ipadx=1)

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

# Mappage des identifiants fixes
path_type_map = {
    "conventional": {"fr": "Opposition", "en": "Conventional", "de": "Gegenlauffräsen", "es": "Convencional", "index": 1},
    "climb": {"fr": "Avalant", "en": "Climb", "de": "Gleichlauffräsen", "es": "Ascendente", "index": 2},
    "alternate": {"fr": "Alterné", "en": "Alternate", "de": "Abwechselnd", "es": "Alternado", "index": 3},
    "right": {"fr": "Droite", "en": "Right", "de": "Rechts", "es": "Derecha", "index": 1},
    "left": {"fr": "Gauche", "en": "Left", "de": "Links", "es": "Izquierda", "index": 2}
}

drilling_type_map = {
    "contour": {"fr": "Trou traversant", "en": "Contour", "de": "Durchgangsloch", "es": "Agujero pasante", "index": 1},
    "blind": {"fr": "Trou borgne", "en": "Blind", "de": "Blindloch", "es": "Agujero ciego", "index": 2},
    "outer": {"fr": "Diamètre extérieur", "en": "Outer", "de": "Außendurchmesser", "es": "Diámetro exterior", "index": 3}
}

corner_type_map = {
    "front_left": {"fr": "Avant Gauche (AVG)", "en": "Front Left (FL)", "de": "Vorne Links", "es": "Delantero Izquierdo", "index": 1},
    "front_right": {"fr": "Avant Droit (AVD)", "en": "Front Right (FR)", "de": "Vorne Rechts", "es": "Delantero Derecho", "index": 2},
    "rear_right": {"fr": "Arrière Droit (ARD)", "en": "Rear Right (RR)", "de": "Hinten Rechts", "es": "Trasero Derecho", "index": 3},
    "rear_left": {"fr": "Arrière Gauche (ARG)", "en": "Rear Left (RL)", "de": "Hinten Links", "es": "Trasero Izquierdo", "index": 4}
}

thread_type_map = {
    "nut_internal": {"fr": "Ecrou (Interne)", "en": "Nut (Internal)", "de": "Mutter (Innen)", "es": "Tuerca (Interna)", "index": 1},
    "screw_external": {"fr": "Vis (Externe)", "en": "Screw (External)", "de": "Schraube (Außen)", "es": "Tornillo (Externa)", "index": 2}
}

# Dictionnaire pour mapper les codes de langue aux noms affichables
language_display_names = {
    "fr": "Français",
    "en": "English",
    "de": "Deutsch",
    "es": "Español"
}

mode_acronyms = {
    "1": "SRC",
    "2": "CDR",
    "3": "MTX",
    "4": "RDS",
    "5": "OBL",
    "6": "THR"
}

def convert_legacy_to_fixed_id(value, mapping, lang):
    """Convertit une valeur traduite en identifiant fixe."""
    print(f"Débogage: Conversion de la valeur '{value}' pour le mappage {list(mapping.keys())} (langue: {lang})")
    for fixed_id, data in mapping.items():
        if value == fixed_id or value == data.get(lang, "") or value in [data.get(l, "") for l in language_display_names]:
            print(f"Débogage: Valeur '{value}' convertie en identifiant fixe '{fixed_id}'")
            return fixed_id
    print(f"Débogage: Valeur '{value}' non trouvée, retourne 'conventional' par défaut")
    return "conventional"  # Fallback pour éviter les erreurs

def load_translations():
    translations_path = os.path.join(os.path.dirname(__file__), "translations.json")
    if os.path.exists(translations_path):
        with open(translations_path, "r", encoding='utf-8') as f:
            return json.load(f)
    return {"languages": ["fr"], "translations": {"fr": {}}}

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    translations = load_translations()
    valid_languages = translations["languages"]
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = json.load(f)
            if config.get("language", "fr") not in valid_languages:
                config["language"] = "fr"
            lang = config.get("language", "fr")
            for section in ["surfacing", "contour_drilling", "corner_radius", "oblong_hole", "matrix_drilling", "threading"]:
                if section in config:
                    if "path_type" in config[section]:
                        # Forcer conventional pour modes 2, 4, 5 si alternate est détecté
                        if section in ["contour_drilling", "corner_radius", "oblong_hole"] and config[section]["path_type"] == "alternate":
                            config[section]["path_type"] = "conventional"
                            print(f"Débogage: {section} - path_type 'alternate' non autorisé, forcé à 'conventional'")
                        config[section]["path_type"] = convert_legacy_to_fixed_id(config[section]["path_type"], path_type_map, lang)
                    if "drilling_type" in config[section]:
                        config[section]["drilling_type"] = convert_legacy_to_fixed_id(config[section]["drilling_type"], drilling_type_map, lang)
                    if "corner_type" in config[section]:
                        config[section]["corner_type"] = convert_legacy_to_fixed_id(config[section]["corner_type"], corner_type_map, lang)
                    if "thread_type" in config[section]:
                        config[section]["thread_type"] = convert_legacy_to_fixed_id(config[section]["thread_type"], thread_type_map, lang)
            return config
    return {
        "project_name": "test",
        "machine": "CNC_450x800",
        "last_operation": "1",
        "language": "fr",
        "threading": {}
    }

def save_config(config):
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)

def get_profiles_dir():
    """Retourne le chemin du dossier profiles, le crée si absent."""
    profiles_dir = os.path.join(os.path.dirname(__file__), "profiles")
    os.makedirs(profiles_dir, exist_ok=True)
    return profiles_dir

def save_profile(mode_id, profile_name, params, general_params=None):
    """Sauvegarde un profil pour un mode donné."""
    profiles_dir = get_profiles_dir()
    filename = f"{mode_id}_{profile_name}.json"
    filepath = os.path.join(profiles_dir, filename)
    
    profile_data = {
        "mode": mode_id,
        "name": profile_name,
        "params": params,
        "general": general_params or {},  # Optionnel : projet, machine
        "saved_at": datetime.now().isoformat()
    }
    
    with open(filepath, "w", encoding='utf-8') as f:
        json.dump(profile_data, f, indent=4)
    
    print(f"Débogage: Profil sauvegardé : {filepath}")
    messagebox.showinfo("Succès", f"Profil '{profile_name}' sauvegardé pour le mode {mode_id}.")

def load_available_profiles(mode_id):
    """Retourne une liste des noms de profils disponibles pour un mode, triés par date récente."""
    profiles_dir = get_profiles_dir()
    pattern = os.path.join(profiles_dir, f"{mode_id}_*.json")
    files = glob.glob(pattern)
    
    profiles = []
    for file in files:
        with open(file, "r", encoding='utf-8') as f:
            data = json.load(f)
            profiles.append((data["name"], os.path.getmtime(file)))  # (nom, timestamp)
    
    # Trier par date descendante (plus récent en premier)
    profiles.sort(key=lambda x: x[1], reverse=True)
    return [name for name, _ in profiles]

def load_profile(mode_id, profile_name):
    """Charge un profil et retourne ses params + généraux."""
    profiles_dir = get_profiles_dir()
    filepath = os.path.join(profiles_dir, f"{mode_id}_{profile_name}.json")
    
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Profil non trouvé : {profile_name}")
    
    with open(filepath, "r", encoding='utf-8') as f:
        data = json.load(f)
    
    # Met à jour les vars globales pour l'UI
    global project_name_var, machine_var, entry_vars
    if data["general"]:
        project_name_var.set(data["general"].get("project_name", project_name_var.get()))
        machine_var.set(data["general"].get("machine", machine_var.get()))
    
    # Met à jour les champs du mode
    for key, value in data["params"].items():
        if key in entry_vars:
            entry_vars[key].set(str(value))
    
    # Met à jour l'image et les champs
    update_image()
    print(f"Débogage: Profil chargé : {profile_name} pour mode {mode_id}")
    messagebox.showinfo("Succès", f"Profil '{profile_name}' chargé pour le mode {mode_id}.")

def generate_image_filename(mode, path_type, corner_type=None, drilling_type=None, x_coord=None, y_coord=None, thread_type=None):
    filename = f"images/mode{mode}"
    print(f"Débogage: Génération du nom de fichier pour mode={mode}, path_type={path_type}, corner_type={corner_type}, drilling_type={drilling_type}, x_coord={x_coord}, y_coord={y_coord}, thread_type={thread_type}")
    
    if mode == "1":
        path_index = path_type_map.get(path_type, path_type_map["conventional"]).get("index", 1)
        filename += f"{path_index}0"
        print(f"Débogage: Mode 1, path_index={path_index}, filename={filename}")
    elif mode == "2":
        path_index = path_type_map.get(path_type, path_type_map["conventional"]).get("index", 1)
        drilling_index = drilling_type_map.get(drilling_type, drilling_type_map["contour"]).get("index", 1)
        filename += f"{path_index}{drilling_index}"
        print(f"Débogage: Mode 2, path_index={path_index}, drilling_index={drilling_index}, filename={filename}")
    elif mode == "6":
        path_index = path_type_map.get(path_type, path_type_map["right"]).get("index", 1)
        thread_index = thread_type_map.get(thread_type, thread_type_map["nut_internal"]).get("index", 1)
        filename += f"{path_index}{thread_index}"
        print(f"Débogage: Mode 6, path_index={path_index}, thread_index={thread_index}, filename={filename}")
    elif mode == "3":
        filename += "00"
        print(f"Débogage: Mode 3, filename={filename}")
    elif mode == "4":
        path_index = path_type_map.get(path_type, path_type_map["conventional"]).get("index", 1)
        corner_index = corner_type_map.get(corner_type, corner_type_map["front_left"]).get("index", 1)
        filename += f"{corner_index}{path_index}"
        print(f"Débogage: Mode 4, path_index={path_index}, corner_index={corner_index}, filename={filename}")
    elif mode == "5":
        path_index = path_type_map.get(path_type, path_type_map["conventional"]).get("index", 1)
        print(f"Débogage: Mode 5, path_type={path_type}, path_index={path_index}, x_coord={x_coord}, y_coord={y_coord}")
        if path_type in ["conventional", "climb"]:
            if x_coord == 0 and y_coord == 0:
                filename += f"{path_index}3"
                print("Débogage: Mode 5 -> both 0: 13 or 23")
            elif x_coord == 0:
                filename += f"{path_index}1"
                print("Débogage: Mode 5 -> x=0: 11 or 21")
            elif y_coord == 0:
                filename += f"{path_index}2"
                print("Débogage: Mode 5 -> y=0: 12 or 22")
            else:
                filename += f"{path_index}4"
                print("Débogage: Mode 5 -> both >0: 14 or 24")
        else:
            filename += f"14"
            print("Débogage: Mode 5 -> path_type non valide, fallback: 14")
    
    filename += ".png"
    print(f"Débogage: Nom de fichier final : {filename}")
    return filename

def update_image():
    print("Débogage: update_image called")
    selected_mode_id = mode_var.get()
    translations = load_translations()
    lang = language_var.get()
    try:
        print(f"Débogage: Valeurs brutes des combobox : {{ {', '.join(f'{k}: {v.get()}' for k, v in entry_vars.items())} }}")
        if selected_mode_id == "1":
            path_type = convert_legacy_to_fixed_id(entry_vars["path_type"].get(), path_type_map, lang)
            filename = generate_image_filename(selected_mode_id, path_type)
        elif selected_mode_id == "2":
            path_type = convert_legacy_to_fixed_id(entry_vars["path_type"].get(), path_type_map, lang)
            drilling_type = convert_legacy_to_fixed_id(entry_vars["drilling_type"].get(), drilling_type_map, lang)
            print(f"Débogage: Mode 2 - path_type={path_type}, drilling_type={drilling_type}")
            filename = generate_image_filename(selected_mode_id, path_type, drilling_type=drilling_type)
        elif selected_mode_id == "6":
            path_type = convert_legacy_to_fixed_id(entry_vars["path_type"].get(), path_type_map, lang)
            thread_type = convert_legacy_to_fixed_id(entry_vars["thread_type"].get(), thread_type_map, lang)
            print(f"Débogage: Mode 6 - path_type={path_type}, thread_type={thread_type}")
            filename = generate_image_filename(selected_mode_id, path_type, thread_type=thread_type)
        elif selected_mode_id == "3":
            filename = generate_image_filename(selected_mode_id, "conventional")
        elif selected_mode_id == "4":
            path_type = convert_legacy_to_fixed_id(entry_vars["path_type"].get(), path_type_map, lang)
            corner_type = convert_legacy_to_fixed_id(entry_vars["corner_type"].get(), corner_type_map, lang)
            print(f"Débogage: Mode 4 - path_type={path_type}, corner_type={corner_type}")
            filename = generate_image_filename(selected_mode_id, path_type, corner_type=corner_type)
        elif selected_mode_id == "5":
            path_type = convert_legacy_to_fixed_id(entry_vars["path_type"].get(), path_type_map, lang)
            raw_x = entry_vars["length_x"].get()
            raw_y = entry_vars["length_y"].get()
            print(f"Débogage: Mode 5 - raw length_x='{raw_x}', length_y='{raw_y}', path_type={path_type}")
            try:
                x_coord = float(raw_x or 0)
                y_coord = float(raw_y or 0)
            except ValueError:
                x_coord = y_coord = 0
                print(f"Débogage: Mode 5 - Conversion échouée, x_coord={x_coord}, y_coord={y_coord}")
            print(f"Débogage: Mode 5 - parsed x_coord={x_coord}, y_coord={y_coord}")
            filename = generate_image_filename(selected_mode_id, path_type, x_coord=x_coord, y_coord=y_coord)
        else:
            raise KeyError("Mode non supporté")
        
        image_path = os.path.join(os.path.dirname(__file__), filename)
        print(f"Débogage: Tentative de chargement de l'image : {image_path}")
        default_path = os.path.join(os.path.dirname(__file__), f"images/mode{selected_mode_id}.png")
        
        try:
            img = Image.open(image_path)
            print(f"Débogage: Image chargée avec succès : {image_path}")
        except FileNotFoundError:
            print(f"Débogage: Image principale non trouvée : {image_path}")
            print(f"Débogage: Tentative de chargement de l'image par défaut : {default_path}")
            try:
                img = Image.open(default_path)
                print(f"Débogage: Image par défaut chargée avec succès : {default_path}")
            except FileNotFoundError:
                print(f"Débogage: Image par défaut non trouvée : {default_path}")
                image_label.configure(image='')
                image_label.image = None
                messagebox.showwarning(
                    translations["translations"][lang]["error"],
                    translations["translations"][lang]["image_not_found"].format(
                        filename=filename, mode=selected_mode_id, path=os.path.dirname(__file__)
                    )
                )
                return
        
        img = img.resize((400, 300), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        image_label.configure(image=photo)
        image_label.image = photo
    except KeyError as e:
        print(f"Débogage: KeyError dans update_image : {e}")
        image_path = os.path.join(os.path.dirname(__file__), f"images/mode{selected_mode_id}.png")
        print(f"Débogage: Tentative de chargement de l'image de secours : {image_path}")
        try:
            img = Image.open(image_path)
            print(f"Débogage: Image de secours chargée avec succès : {image_path}")
            img = img.resize((200, 150), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            image_label.configure(image=photo)
            image_label.image = photo
        except FileNotFoundError:
            print(f"Débogage: Image de secours non trouvée : {image_path}")
            image_label.configure(image='')
            image_label.image = None
            messagebox.showwarning(
                translations["translations"][lang]["error"],
                translations["translations"][lang]["image_not_found"].format(
                    filename=f"mode{selected_mode_id}.png", mode=selected_mode_id, path=os.path.dirname(__file__)
                )
            )

def update_fields(event=None):
    selected_mode_id = mode_var.get()
    config = load_config()
    translations = load_translations()
    lang = language_var.get()
    clear_fields()

    print(f"Débogage: Mise à jour des champs pour le mode : {selected_mode_id}")
    mode_params = {
        "1": [
            ("start_x", "start_x", 0.0),
            ("start_y", "start_y", 0.0),
            ("start_z", "start_z", 10.0),
            ("clearance_height", "clearance_height", 5.0),
            ("tool_diameter", "tool_diameter", 10.0),
            ("overlap_percent", "overlap_percent", 50.0),
            ("width_x", "width_x", 100.0),
            ("length_y", "length_y", 100.0),
            ("total_depth", "total_depth", 1.0),
            ("depth_per_pass", "depth_per_pass", 1.0),
            ("feed_rate", "feed_rate", 1800),
            ("spindle_speed", "spindle_speed", 1000),
            ("path_type", "path_type", "conventional")
        ],
        "2": [
            ("start_x", "start_x", 0.0),
            ("start_y", "start_y", 0.0),
            ("start_z", "start_z", 0.0),
            ("clearance_height", "clearance_height", 5.0),
            ("tool_diameter", "tool_diameter", 10.0),
            ("hole_diameter", "hole_diameter", 30.0),
            ("total_depth", "total_depth", 2.0),
            ("depth_per_pass", "depth_per_pass", 1.0),
            ("feed_rate", "feed_rate", 1800),
            ("spindle_speed", "spindle_speed", 24000),
            ("path_type", "path_type", "conventional"),
            ("drilling_type", "drilling_type", "contour"),
            ("overlap_percent", "overlap_percent", 50.0)
        ],
        "3": [
            ("start_x", "start_x", 0.0),
            ("start_y", "start_y", 0.0),
            ("start_z", "start_z", 0.0),
            ("clearance_height", "clearance_height", 5.0),
            ("spacing_x", "spacing_x", 20.0),
            ("spacing_y", "spacing_y", 20.0),
            ("num_rows", "num_rows", 5),
            ("num_cols", "num_cols", 5),
            ("total_depth", "total_depth", 10.0),
            ("depth_per_pass", "depth_per_pass", 1.0),
            ("feed_rate", "feed_rate", 1800),
            ("spindle_speed", "spindle_speed", 1000)
        ],
        "4": [
            ("start_z", "start_z", 0.0),
            ("clearance_height", "clearance_height", 5.0),
            ("radius", "radius", 10.0),
            ("tool_diameter", "tool_diameter", 10.0),
            ("total_depth", "total_depth", 2.0),
            ("depth_per_pass", "depth_per_pass", 0.5),
            ("feed_rate", "feed_rate", 1800),
            ("spindle_speed", "spindle_speed", 24000),
            ("path_type", "path_type", "conventional"),
            ("corner_type", "corner_type", "front_left")
        ],
        "5": [
            ("start_x", "start_x", 0.0),
            ("start_y", "start_y", 0.0),
            ("start_z", "start_z", 0.0),
            ("length_x", "length_x", 20.0),
            ("length_y", "length_y", 20.0),
            ("width", "width", 10.0),
            ("tool_diameter", "tool_diameter", 5.0),
            ("path_type", "path_type", "conventional"),
            ("total_depth", "total_depth", 2.0),
            ("depth_per_pass", "depth_per_pass", 0.5),
            ("feed_rate", "feed_rate", 1800),
            ("spindle_speed", "spindle_speed", 24000)
        ],
        "6": [
            ("start_x", "start_x", 0.0),
            ("start_y", "start_y", 0.0),
            ("start_z", "start_z", 0.0),
            ("clearance_height", "clearance_height", 5.0),
            ("tool_diameter", "tool_diameter", 10.0),
            ("hole_diameter", "hole_diameter", 30.0),
            ("total_depth", "total_depth", 2.0),
            ("depth_per_pass", "depth_per_pass", 0.5),
            ("feed_rate", "feed_rate", 1800),
            ("spindle_speed", "spindle_speed", 24000),
            ("path_type", "path_type", "right"),
            ("thread_type", "thread_type", "nut_internal"),
            ("overlap_percent", "overlap_percent", 50.0),
            ("thread_pitch", "thread_pitch", 10.0),
            ("thread_number", "thread_number", 6)
        ]
    }

    params = config.get({"1": "surfacing", "2": "contour_drilling", "3": "matrix_drilling", 
                         "4": "corner_radius", "5": "oblong_hole", "6": "threading"}.get(selected_mode_id, "surfacing"), {})
    
    for i, (key, label_key, default) in enumerate(mode_params.get(selected_mode_id, [])):
        var_value = params.get(key, str(default))
        label_text = translations["translations"][lang]["fields"].get(label_key, label_key)
        
        tooltip_text = translations["translations"][lang]["tooltips"].get(label_key, f"Description pour {label_key}")
        
        if key == "path_type":
            if selected_mode_id == "6":
                options = [path_type_map[id][lang] for id in ["right", "left"]]
                default_value = path_type_map.get(var_value, path_type_map["right"]).get(lang, "Droite")
            elif selected_mode_id == "1":
                options = [path_type_map[id][lang] for id in ["conventional", "climb", "alternate"]]
                default_value = path_type_map.get(var_value, path_type_map["conventional"]).get(lang, "Opposition")
            else:  # Modes 2, 3, 4, 5 : limiter à conventional et climb
                options = [path_type_map[id][lang] for id in ["conventional", "climb"]]
                # Si var_value est "alternate", forcer conventional comme valeur par défaut
                default_value = path_type_map.get(var_value if var_value in ["conventional", "climb"] else "conventional", path_type_map["conventional"]).get(lang, "Opposition")
            var = tk.StringVar(value=default_value)
            cb = ttk.Combobox(frame, values=options, textvariable=var, state="readonly", style="TCombobox", width=30)
            cb.grid(row=i, column=1, padx=5, pady=2, sticky="ew")
            cb.bind("<<ComboboxSelected>>", lambda e: update_image())
            # Ajout de l'info-bulle sur le combobox
            ToolTip(cb, tooltip_text)
        elif key == "corner_type":
            options = [corner_type_map[id][lang] for id in corner_type_map]
            var = tk.StringVar(value=corner_type_map.get(var_value, corner_type_map["front_left"]).get(lang, "Avant Gauche (AVG)"))
            cb = ttk.Combobox(frame, values=options, textvariable=var, state="readonly", style="TCombobox", width=30)
            cb.grid(row=i, column=1, padx=5, pady=2, sticky="ew")
            cb.bind("<<ComboboxSelected>>", lambda e: update_image())
            # Ajout de l'info-bulle sur le combobox
            ToolTip(cb, tooltip_text)
        elif key == "drilling_type":
            options = [drilling_type_map[id][lang] for id in drilling_type_map]
            var = tk.StringVar(value=drilling_type_map.get(var_value, drilling_type_map["contour"]).get(lang, "Trou traversant"))
            cb = ttk.Combobox(frame, values=options, textvariable=var, state="readonly", style="TCombobox", width=30)
            cb.grid(row=i, column=1, padx=5, pady=2, sticky="ew")
            cb.bind("<<ComboboxSelected>>", lambda e: update_image())
            # Ajout de l'info-bulle sur le combobox
            ToolTip(cb, tooltip_text)
        elif key == "thread_type":
            options = [thread_type_map[id][lang] for id in thread_type_map]
            var = tk.StringVar(value=thread_type_map.get(var_value, thread_type_map["nut_internal"]).get(lang, "Ecrou (Interne)"))
            cb = ttk.Combobox(frame, values=options, textvariable=var, state="readonly", style="TCombobox", width=30)
            cb.grid(row=i, column=1, padx=5, pady=2, sticky="ew")
            cb.bind("<<ComboboxSelected>>", lambda e: update_image())
            # Ajout de l'info-bulle sur le combobox
            ToolTip(cb, tooltip_text)
        else:
            var = tk.StringVar(value=str(var_value))
            entry = ttk.Entry(frame, textvariable=var, style="TEntry", width=30)
            entry.grid(row=i, column=1, padx=5, pady=2, sticky="ew")
            if key in ["length_x", "length_y"]:
                entry.bind("<KeyRelease>", lambda e: update_image())
            # Ajout de l'info-bulle sur l'entry
            ToolTip(entry, tooltip_text)
        
        ttk.Label(frame, text=label_text, style="TLabel").grid(row=i, column=0, padx=5, pady=2, sticky="e")
        entry_vars[key] = var

    update_image()

# ... (le reste du code reste inchangé, à partir de def clear_fields(): jusqu'à root.mainloop())
# ... (le reste du code reste inchangé, à partir de def clear_fields(): jusqu'à root.mainloop())

def clear_fields():
    for widget in frame.winfo_children():
        widget.destroy()
    entry_vars.clear()

def on_mode_select(event):
    selected_name = combo.get()
    translations = load_translations()
    lang = language_var.get()
    mode_id = next((id for id, name in mode_options[lang] if name == selected_name), "1")
    mode_var.set(mode_id)
    print(f"Débogage: Mode sélectionné dans on_mode_select : {mode_id}")

    current_project_name = project_name_var.get()
    acronym = mode_acronyms.get(mode_id, "TST")
    if len(current_project_name) >= 3:
        new_project_name = acronym + current_project_name[3:]
    else:
        new_project_name = acronym + current_project_name
    project_name_var.set(new_project_name)

    update_fields()

def on_language_select(event):
    config = load_config()
    selected_display_name = language_combo.get()
    lang_code = next((code for code, name in language_display_names.items() if name == selected_display_name), "fr")
    config["language"] = lang_code
    language_var.set(lang_code)
    save_config(config)
    update_ui_language()

def update_ui_language():
    translations = load_translations()
    lang = language_var.get()
    
    root.title(translations["translations"][lang]["title"])
    general_frame.configure(text=translations["translations"][lang].get("general_settings", "General Settings"))
    language_label.configure(text=translations["translations"][lang]["language_label"])
    mode_label.configure(text=translations["translations"][lang]["select_mode"])
    project_label.configure(text=translations["translations"][lang]["project_name"])
    machine_label.configure(text=translations["translations"][lang]["machine"])
    generate_button.configure(text=translations["translations"][lang]["generate_button"])
    
    combo['values'] = [name for _, name in mode_options[lang]]
    current_mode_id = mode_var.get()
    current_mode_name = next((name for id, name in mode_options[lang] if id == current_mode_id), mode_options[lang][0][1])
    combo.set(current_mode_name)
    
    update_fields()

def on_closing():
    print("Débogage: Tentative de fermeture de GUI.py")
    if messagebox.askokcancel("Quitter", "Voulez-vous quitter l'application ?"):
        print("Débogage: Fermeture confirmée")
        try:
            root.destroy()
            print("Débogage: root.destroy() exécuté")
        except Exception as e:
            print(f"Débogage: Erreur lors de root.destroy() : {str(e)}")
            
def save_and_generate():
    config = load_config()
    translations = load_translations()
    lang = language_var.get()
    mode = mode_var.get()
    print(f"Débogage: Mode à générer dans save_and_generate : {mode}")
    config["last_operation"] = mode
    config["project_name"] = project_name_var.get()
    config["machine"] = machine_var.get()
    config["language"] = lang

    print(f"Débogage: Paramètres enregistrés : {entry_vars.keys()}")
    params = {}
    for k, v in entry_vars.items():
        if k == "path_type":
            params[k] = convert_legacy_to_fixed_id(v.get(), path_type_map, lang)
            # Forcer conventional pour modes 2, 4, 5 si alternate est détecté
            if mode in ["2", "4", "5"] and params[k] == "alternate":
                params[k] = "conventional"
                print(f"Débogage: Mode {mode} - path_type 'alternate' non autorisé, forcé à 'conventional'")
        elif k == "drilling_type":
            params[k] = convert_legacy_to_fixed_id(v.get(), drilling_type_map, lang)
        elif k == "corner_type":
            params[k] = convert_legacy_to_fixed_id(v.get(), corner_type_map, lang)
        elif k == "thread_type":
            params[k] = convert_legacy_to_fixed_id(v.get(), thread_type_map, lang)
        else:
            try:
                params[k] = float(v.get()) if k not in ["path_type", "drilling_type", "corner_type", "thread_type"] else v.get()
            except ValueError:
                params[k] = v.get()

    if mode == "1":
        config["surfacing"] = params
    elif mode == "2":
        config["contour_drilling"] = params
        config["contour_drilling"]["is_blind_hole"] = params["drilling_type"] == "blind"
    elif mode == "6":
        config["threading"] = params
    elif mode == "3":
        config["matrix_drilling"] = params
    elif mode == "4":
        config["corner_radius"] = params
    elif mode == "5":
        config["oblong_hole"] = params

    save_config(config)
    try:
        main_script_path = os.path.join(os.path.dirname(__file__), "main_tkinter.py")
        if os.path.exists(main_script_path):
            subprocess.run(["python", main_script_path], check=True, cwd=os.path.dirname(__file__))
            project_name = project_name_var.get()
            gcode_pattern = os.path.join(os.path.dirname(__file__), f"NC/{mode}_{project_name}_*.nc")
            gcode_files = glob.glob(gcode_pattern)
            if gcode_files:
                latest_file = max(gcode_files, key=os.path.getmtime)
                gcode_filename = os.path.basename(latest_file)
                #messagebox.showinfo(
                #    translations["translations"][lang]["success"],
                #    translations["translations"][lang]["success_with_file"].format(filename=gcode_filename)
                #)
            else:
                messagebox.showinfo(
                    translations["translations"][lang]["success"],
                    translations["translations"][lang]["success"]
                )
        else:
            messagebox.showerror(
                translations["translations"][lang]["error"],
                translations["translations"][lang]["script_not_found"].format(path=main_script_path)
            )
    except subprocess.CalledProcessError as e:
        messagebox.showerror(
            translations["translations"][lang]["error"],
            translations["translations"][lang]["generation_failed"].format(error=str(e))
        )
    except Exception as e:
        messagebox.showerror(
            translations["translations"][lang]["error"],
            translations["translations"][lang]["generic_error"].format(error=str(e))
        )

# Fonctions pour les profils
def on_save_profile():
    mode_id = mode_var.get()
    lang = language_var.get()
    translations = load_translations()
    profile_name = simpledialog.askstring("Sauvegarder Profil", "Nom du profil :")
    if not profile_name:
        return  # Annulé
    
    # Récupère les params actuels (comme dans save_and_generate)
    params = {}
    for k, v in entry_vars.items():
        if k == "path_type":
            params[k] = convert_legacy_to_fixed_id(v.get(), path_type_map, lang)
            if mode_id in ["2", "4", "5"] and params[k] == "alternate":
                params[k] = "conventional"
        elif k == "drilling_type":
            params[k] = convert_legacy_to_fixed_id(v.get(), drilling_type_map, lang)
        elif k == "corner_type":
            params[k] = convert_legacy_to_fixed_id(v.get(), corner_type_map, lang)
        elif k == "thread_type":
            params[k] = convert_legacy_to_fixed_id(v.get(), thread_type_map, lang)
        else:
            try:
                params[k] = float(v.get())
            except ValueError:
                params[k] = v.get()
    
    general_params = {
        "project_name": project_name_var.get(),
        "machine": machine_var.get()
    }
    
    save_profile(mode_id, profile_name, params, general_params)

def on_load_profile():
    mode_id = mode_var.get()
    available = load_available_profiles(mode_id)
    if not available:
        messagebox.showwarning("Aucun Profil", f"Aucun profil disponible pour le mode {mode_id}.")
        return
    
    # Fenêtre simple pour sélection (ou utilisez un Combobox dans la frame)
    profile_window = tk.Toplevel(root)
    profile_window.title("Charger Profil")
    profile_window.geometry("300x150")
    
    ttk.Label(profile_window, text=f"Profils pour mode {mode_id} :").pack(pady=5)
    profile_var = tk.StringVar()
    profile_combo = ttk.Combobox(profile_window, values=available, textvariable=profile_var, state="readonly")
    profile_combo.pack(pady=5)
    profile_combo.set(available[0])  # Premier par défaut
    
    def confirm_load():
        selected = profile_var.get()
        try:
            load_profile(mode_id, selected)
        except Exception as e:
            messagebox.showerror("Erreur", f"Échec du chargement : {str(e)}")
        profile_window.destroy()
    
    ttk.Button(profile_window, text="Charger", command=confirm_load).pack(pady=10)

# Initialisation de la fenêtre
root = tk.Tk()
translations = load_translations()
config = load_config()
language_var = tk.StringVar(value=config.get("language", "fr"))

root.title(translations["translations"][language_var.get()]["title"])
root.geometry("850x700+100+100")

# Style
style = ttk.Style()
style.configure("TFrame", borderwidth=2, relief="groove")
style.configure("TLabel", borderwidth=1, relief="flat")
style.configure("TEntry", borderwidth=1, relief="solid")
style.configure("TCombobox", borderwidth=1, relief="solid")

# Variables
entry_vars = {}
mode_options = {
    "fr": [
        ("1", "Surfaçage"),
        ("2", "Perçages par détourage"),
        ("3", "Matrice perçages"),
        ("4", "Rayon sur 90°"),
        ("5", "Trou oblong"),
        ("6", "Filetage")
    ],
    "en": [
        ("1", "Surfacing"),
        ("2", "Contour drilling"),
        ("3", "Matrix drilling"),
        ("4", "90° corner radius"),
        ("5", "Oblong hole"),
        ("6", "Threading")
    ],
    "de": [
        ("1", "Flächenbearbeitung"),
        ("2", "Konturbohren"),
        ("3", "Matrixbohren"),
        ("4", "90°-Eckenradius"),
        ("5", "Langloch"),
        ("6", "Gewinde")
    ],
    "es": [
        ("1", "Alisado de superficie"),
        ("2", "Taladrado de contorno"),
        ("3", "Taladrado matricial"),
        ("4", "Radio de esquina de 90°"),
        ("5", "Agujero oblongo"),
        ("6", "Rosca")
    ]
}
mode_var = tk.StringVar(value=config.get("last_operation", "1"))
project_name_var = tk.StringVar(value=config.get("project_name", "test"))
machine_var = tk.StringVar(value=config.get("machine", "CNC_450x800"))

# Frame pour les champs généraux
general_frame = ttk.LabelFrame(
    root,
    text=translations["translations"][language_var.get()].get("general_settings", "General Settings"),
    style="TFrame"
)
general_frame.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
general_frame.grid_columnconfigure(1, minsize=250)

# Sélection de la langue
language_label = ttk.Label(general_frame, text=translations["translations"][language_var.get()]["language_label"], style="TLabel")
language_label.grid(row=0, column=0, padx=5, pady=5, sticky="e")
language_combo = ttk.Combobox(general_frame, values=list(language_display_names.values()), state="readonly", style="TCombobox", width=30)
language_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
language_combo.set(language_display_names.get(language_var.get(), "Français"))
language_combo.bind("<<ComboboxSelected>>", on_language_select)

# Mode sélection
mode_label = ttk.Label(general_frame, text=translations["translations"][language_var.get()]["select_mode"], style="TLabel")
mode_label.grid(row=1, column=0, padx=5, pady=5, sticky="e")
combo = ttk.Combobox(general_frame, values=[name for _, name in mode_options[language_var.get()]], state="readonly", style="TCombobox", width=30)
combo.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
initial_mode = next((name for id, name in mode_options[language_var.get()] if id == mode_var.get()), mode_options[language_var.get()][0][1])
combo.set(initial_mode)
combo.bind("<<ComboboxSelected>>", on_mode_select)

# Champs projet et machine
project_label = ttk.Label(general_frame, text=translations["translations"][language_var.get()]["project_name"], style="TLabel")
project_label.grid(row=2, column=0, padx=5, pady=5, sticky="e")
ttk.Entry(general_frame, textvariable=project_name_var, style="TEntry", width=30).grid(row=2, column=1, padx=5, pady=5, sticky="ew")
machine_label = ttk.Label(general_frame, text=translations["translations"][language_var.get()]["machine"], style="TLabel")
machine_label.grid(row=3, column=0, padx=5, pady=5, sticky="e")
ttk.Entry(general_frame, textvariable=machine_var, style="TEntry", width=30).grid(row=3, column=1, padx=5, pady=5, sticky="ew")

# Frame pour les champs contextuels
frame = ttk.Frame(root, style="TFrame")
frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
frame.grid_columnconfigure(1, minsize=250)

# Label pour l'image
image_label = tk.Label(root, borderwidth=2, relief="groove")
image_label.grid(row=0, column=2, rowspan=2, padx=5, pady=5, sticky="nsew")

# Bouton de génération
generate_button = ttk.Button(root, text=translations["translations"][language_var.get()]["generate_button"], command=save_and_generate)
generate_button.grid(row=2, column=0, columnspan=3, pady=10)

# Frame pour les boutons de profils
profile_frame = ttk.Frame(root, style="TFrame")
profile_frame.grid(row=3, column=0, columnspan=3, pady=5, sticky="ew")

ttk.Button(profile_frame, text="Sauvegarder Profil", command=on_save_profile).grid(row=0, column=0, padx=5)
ttk.Button(profile_frame, text="Charger Profil", command=on_load_profile).grid(row=0, column=1, padx=5)

# Configurer la grille
root.grid_columnconfigure(0, minsize=150, weight=1)
root.grid_columnconfigure(1, minsize=150, weight=1)
root.grid_columnconfigure(2, weight=1)
root.grid_rowconfigure(1, weight=1)

# Initialisation
update_fields()

root.mainloop()