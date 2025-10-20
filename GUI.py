import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import subprocess
from PIL import Image, ImageTk
import glob
import time

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

# Charger les traductions
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

def generate_image_filename(mode, path_type, corner_type=None, drilling_type=None, x_coord=None, y_coord=None, thread_type=None):
    path_type_map = {
        "Opposition": 1, "Avalant": 2, "Alterné": 3, "Droite": 1, "Gauche": 2,
        "Conventional": 1, "Climb": 2, "Alternate": 3, "Right": 1, "Left": 2,
        "Gegenlauffräsen": 1, "Gleichlauffräsen": 2, "Abwechselnd": 3, "Rechts": 1, "Links": 2,
        "Convencional": 1, "Ascendente": 2, "Alternado": 3, "Derecha": 1, "Izquierda": 2
    }
    corner_type_map = {
        "Avant Gauche (AVG)": 1, "Avant Droit (AVD)": 2, "Arrière Droit (ARD)": 3, "Arrière Gauche (ARG)": 4,
        "Front Left (FL)": 1, "Front Right (FR)": 2, "Rear Right (RR)": 3, "Rear Left (RL)": 4,
        "Vorne Links": 1, "Vorne Rechts": 2, "Hinten Rechts": 3, "Hinten Links": 4,
        "Delantero Izquierdo": 1, "Delantero Derecho": 2, "Trasero Derecho": 3, "Trasero Izquierdo": 4
    }
    thread_type_map = {
        "Ecrou (Interne)": 1, "Vis (Externe)": 2,
        "Nut (Internal)": 1, "Screw (External)": 2,
        "Mutter (Innen)": 1, "Schraube (Außen)": 2,
        "Tuerca (Interna)": 1, "Tornillo (Externa)": 2
    }
    drilling_type_map = {
        "Blind": 2, "Contour": 1, "Outer": 3,
        "Trou borgne": 2, "Trou traversant": 1, "Diamètre extérieur": 3,
        "Blindloch": 2, "Durchgangsloch": 1, "Außendurchmesser": 3,
        "Agujero ciego": 2, "Agujero pasante": 1, "Diámetro exterior": 3
    }
    
    filename = f"images\mode{mode}"
    if mode == "1":
        if path_type in ["Opposition", "Conventional", "Gegenlauffräsen", "Convencional"]:
            filename += "10"
        elif path_type in ["Avalant", "Climb", "Gleichlauffräsen", "Ascendente"]:
            filename += "20"
        elif path_type in ["Alterné", "Alternate", "Abwechselnd", "Alternado"]:
            filename += "30"
    elif mode == "2":
        path_index = path_type_map.get(path_type, 1)
        drilling_index = drilling_type_map.get(drilling_type, 1)
        filename += f"{path_index}{drilling_index}"
    elif mode == "6":
        path_index = path_type_map.get(path_type, 1)
        thread_index = thread_type_map.get(thread_type, 1)
        filename += f"{path_index}{thread_index}"
    elif mode == "3":
        filename += "00"
    elif mode == "4":
        if path_type in ["Opposition", "Conventional", "Gegenlauffräsen", "Convencional"]:
            filename += str(corner_type_map.get(corner_type, 1)) + "1"
        elif path_type in ["Avalant", "Climb", "Gleichlauffräsen", "Ascendente"]:
            filename += str(corner_type_map.get(corner_type, 1)) + "2"
    elif mode == "5":
        print(f"Mode 5 conditions: path_type={path_type}, x_coord={x_coord}, y_coord={y_coord}")
        if path_type in ["Opposition", "Conventional", "Gegenlauffräsen", "Convencional"]:
            if x_coord == 0 and y_coord == 0:
                filename += "13"
                print("  -> both 0: 13")
            elif x_coord == 0:
                filename += "11"
                print("  -> x=0: 11")
            elif y_coord == 0:
                filename += "12"
                print("  -> y=0: 12")
            else:
                filename += "14"
                print("  -> both >0: 14")
        elif path_type in ["Avalant", "Climb", "Gleichlauffräsen", "Ascendente"]:
            if x_coord == 0 and y_coord == 0:
                filename += "23"
                print("  -> both 0: 23")
            elif x_coord == 0:
                filename += "21"
                print("  -> x=0: 21")
            elif y_coord == 0:
                filename += "22"
                print("  -> y=0: 22")
            else:
                filename += "24"
                print("  -> both >0: 24")
    
    filename += ".png"
    print(f"Generated image filename: {filename}")
    return filename

def update_image():
    print("update_image called")
    selected_mode_id = mode_var.get()
    translations = load_translations()
    lang = language_var.get()
    try:
        if selected_mode_id == "1":
            path_type = entry_vars["path_type"].get()
            filename = generate_image_filename(selected_mode_id, path_type)
        elif selected_mode_id == "2":
            path_type = entry_vars["path_type"].get()
            drilling_type = entry_vars["drilling_type"].get()
            print(f"For mode 2 - path_type: {path_type}, drilling_type: {drilling_type}")
            filename = generate_image_filename(selected_mode_id, path_type, drilling_type=drilling_type)
        elif selected_mode_id == "6":
            path_type = entry_vars["path_type"].get()
            thread_type = entry_vars["thread_type"].get()
            print(f"For mode 6 - path_type: {path_type}, thread_type: {thread_type}")
            filename = generate_image_filename(selected_mode_id, path_type, thread_type=thread_type)
        elif selected_mode_id == "3":
            filename = generate_image_filename(selected_mode_id, "Opposition")
        elif selected_mode_id == "4":
            path_type = entry_vars["path_type"].get()
            corner_type = entry_vars["corner_type"].get()
            print(f"For mode 4 - path_type: {path_type}, corner_type: {corner_type}")
            filename = generate_image_filename(selected_mode_id, path_type, corner_type=corner_type)
        elif selected_mode_id == "5":
            path_type = entry_vars["path_type"].get()
            raw_x = entry_vars["length_x"].get()
            raw_y = entry_vars["length_y"].get()
            print(f"For mode 5 - raw length_x: '{raw_x}', length_y: '{raw_y}', path_type: {path_type}")
            x_coord = float(raw_x or 0)
            y_coord = float(raw_y or 0)
            print(f"  parsed x: {x_coord}, y: {y_coord}")
            filename = generate_image_filename(selected_mode_id, path_type, x_coord=x_coord, y_coord=y_coord)
        else:
            raise KeyError("Mode non supporté")
        
        image_path = os.path.join(os.path.dirname(__file__), filename)
        print(f"Attempting to load image from: {image_path}")
        default_path = os.path.join(os.path.dirname(__file__), f"mode{selected_mode_id}.png")
        
        try:
            img = Image.open(image_path)
            print(f"Successfully loaded image: {image_path}")
        except FileNotFoundError:
            print(f"Primary image not found: {image_path}")
            print(f"Falling back to default: {default_path}")
            try:
                img = Image.open(default_path)
                print(f"Successfully loaded default image: {default_path}")
            except FileNotFoundError:
                print(f"Default image also not found: {default_path}")
                image_label.configure(image='')
                image_label.image = None
                messagebox.showwarning(
                    translations["translations"][lang]["error"],
                    translations["translations"][lang]["image_not_found"].format(
                        filename=filename, mode=selected_mode_id, path=os.path.dirname(__file__)
                    )
                )
                return
        
        img = img.resize((200, 150), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        image_label.configure(image=photo)
        image_label.image = photo
    except KeyError as e:
        print(f"KeyError in update_image: {e}")
        image_path = os.path.join(os.path.dirname(__file__), f"mode{selected_mode_id}.png")
        print(f"Fallback attempt: {image_path}")
        try:
            img = Image.open(image_path)
            print(f"Successfully loaded fallback image: {image_path}")
            img = img.resize((200, 150), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            image_label.configure(image=photo)
            image_label.image = photo
        except FileNotFoundError:
            print(f"Fallback image not found: {image_path}")
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

    print(f"Mise à jour des champs pour le mode : {selected_mode_id}")
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
            ("path_type", "path_type", "1")
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
            ("path_type", "path_type", "Opposition"),
            ("drilling_type", "drilling_type", "Contour"),
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
            ("path_type", "path_type", "Opposition"),
            ("corner_type", "corner_type", "1")
        ],
        "5": [
            ("start_x", "start_x", 0.0),
            ("start_y", "start_y", 0.0),
            ("start_z", "start_z", 0.0),
            ("length_x", "length_x", 20.0),
            ("length_y", "length_y", 20.0),
            ("width", "width", 10.0),
            ("tool_diameter", "tool_diameter", 5.0),
            ("path_type", "path_type", "Opposition"),
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
            ("path_type", "path_type", "Droite"),
            ("thread_type", "thread_type", "Ecrou (Interne)"),
            ("overlap_percent", "overlap_percent", 50.0),
            ("thread_pitch", "thread_pitch", 10.0),
            ("thread_number", "thread_number", 6)
        ]
    }

    params = config.get({"1": "surfacing", "2": "contour_drilling", "3": "matrix_drilling", 
                         "4": "corner_radius", "5": "oblong_hole", "6": "threading"}.get(selected_mode_id, "surfacing"), {})
    
    for i, (key, label_key, default) in enumerate(mode_params.get(selected_mode_id, [])):
        var_value = params.get(key, str(default))
        var = tk.StringVar(value=str(var_value))
        label_text = translations["translations"][lang]["fields"].get(label_key, label_key)
        
        if key == "path_type":
            options = translations["translations"][lang]["path_types"].get(selected_mode_id, ["Opposition", "Avalant"])
            var = tk.StringVar(value=var_value if var_value in options else options[0])
            cb = ttk.Combobox(frame, values=options, textvariable=var)
            cb.grid(row=i+1, column=1, padx=5, pady=2, sticky="ew")
            cb.bind("<<ComboboxSelected>>", lambda e: update_image())
        elif key == "corner_type":
            options = translations["translations"][lang]["corner_types"]
            var = tk.StringVar(value=var_value if var_value in options else options[0])
            cb = ttk.Combobox(frame, values=options, textvariable=var)
            cb.grid(row=i+1, column=1, padx=5, pady=2, sticky="ew")
            cb.bind("<<ComboboxSelected>>", lambda e: update_image())
        elif key == "drilling_type":
            options = translations["translations"][lang]["drilling_types"]
            var = tk.StringVar(value=var_value if var_value in options else options[0])
            cb = ttk.Combobox(frame, values=options, textvariable=var)
            cb.grid(row=i+1, column=1, padx=5, pady=2, sticky="ew")
            cb.bind("<<ComboboxSelected>>", lambda e: update_image())
        elif key == "thread_type":
            options = translations["translations"][lang]["thread_types"]
            var = tk.StringVar(value=var_value if var_value in options else options[0])
            cb = ttk.Combobox(frame, values=options, textvariable=var)
            cb.grid(row=i+1, column=1, padx=5, pady=2, sticky="ew")
            cb.bind("<<ComboboxSelected>>", lambda e: update_image())
        else:
            entry = ttk.Entry(frame, textvariable=var)
            entry.grid(row=i+1, column=1, padx=5, pady=2, sticky="ew")
            if key in ["length_x", "length_y"]:
                entry.bind("<KeyRelease>", lambda e: update_image())
        
        ttk.Label(frame, text=label_text).grid(row=i+1, column=0, padx=5, pady=2, sticky="e")
        entry_vars[key] = var

    update_image()

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
    print(f"Mode sélectionné dans on_mode_select : {mode_id}")

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

# Ajouter ce mappage au début de GUI.py, après les autres mappages
drilling_type_map = {
    "Trou borgne": "Blind",
    "Trou traversant": "Contour",
    "Diamètre extérieur": "Outer",
    "Blind": "Blind",
    "Contour": "Contour",
    "Outer": "Outer",
    "Blindloch": "Blind",
    "Durchgangsloch": "Contour",
    "Außendurchmesser": "Outer",
    "Agujero ciego": "Blind",
    "Agujero pasante": "Contour",
    "Diámetro exterior": "Outer"
}

def save_and_generate():
    config = load_config()
    translations = load_translations()
    lang = language_var.get()
    mode = mode_var.get()
    print(f"Mode à générer dans save_and_generate : {mode}")
    config["last_operation"] = mode
    config["project_name"] = project_name_var.get()
    config["machine"] = machine_var.get()
    config["language"] = lang

    print(f"Paramètres enregistrés : {entry_vars.keys()}")
    if mode == "1":
        config["surfacing"] = {k: float(v.get()) if k not in ["path_type"] else v.get() for k, v in entry_vars.items()}
    elif mode == "2":
        config["contour_drilling"] = {
            k: float(v.get()) if k not in ["path_type", "drilling_type", "is_blind_hole"] else drilling_type_map.get(v.get(), v.get()) if k == "drilling_type" else v.get()
            for k, v in entry_vars.items()
        }
        config["contour_drilling"]["is_blind_hole"] = config["contour_drilling"]["drilling_type"] == "Blind"
    elif mode == "6":
        config["threading"] = {k: float(v.get()) if k not in ["path_type", "thread_type"] else v.get() for k, v in entry_vars.items()}
    elif mode == "3":
        config["matrix_drilling"] = {k: float(v.get()) for k, v in entry_vars.items()}
    elif mode == "4":
        config["corner_radius"] = {k: float(v.get()) if k not in ["path_type", "corner_type"] else v.get() for k, v in entry_vars.items()}
    elif mode == "5":
        config["oblong_hole"] = {k: float(v.get()) if k not in ["path_type"] else v.get() for k, v in entry_vars.items()}

    save_config(config)
    # ... (reste de la fonction inchangé)

    save_config(config)
    try:
        main_script_path = os.path.join(os.path.dirname(__file__), "main_tkinter.py")
        if os.path.exists(main_script_path):
            subprocess.run(["python", main_script_path], check=True, cwd=os.path.dirname(__file__))
            project_name = project_name_var.get()
            gcode_pattern = os.path.join(os.path.dirname(__file__), f"NC\\{mode}_{project_name}_*.nc")
            gcode_files = glob.glob(gcode_pattern)
            if gcode_files:
                latest_file = max(gcode_files, key=os.path.getmtime)
                gcode_filename = os.path.basename(latest_file)
                messagebox.showinfo(
                    translations["translations"][lang]["success"],
                    translations["translations"][lang]["success_with_file"].format(filename=gcode_filename)
                )
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

# Initialisation de la fenêtre
root = tk.Tk()
translations = load_translations()
config = load_config()
language_var = tk.StringVar(value=config.get("language", "fr"))

root.title(translations["translations"][language_var.get()]["title"])
root.geometry("800x600")

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

# Sélection de la langue
language_label = ttk.Label(root, text=translations["translations"][language_var.get()]["language_label"])
language_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
language_combo = ttk.Combobox(root, values=list(language_display_names.values()))
language_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")
language_combo.set(language_display_names.get(language_var.get(), "Français"))
language_combo.bind("<<ComboboxSelected>>", on_language_select)

# Mode sélection
mode_label = ttk.Label(root, text=translations["translations"][language_var.get()]["select_mode"])
mode_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
combo = ttk.Combobox(root, values=[name for _, name in mode_options[language_var.get()]], style="TCombobox")
combo.grid(row=1, column=1, padx=5, pady=5, sticky="w")
initial_mode = next((name for id, name in mode_options[language_var.get()] if id == mode_var.get()), mode_options[language_var.get()][0][1])
combo.set(initial_mode)
combo.bind("<<ComboboxSelected>>", on_mode_select)

# Champs projet et machine
project_label = ttk.Label(root, text=translations["translations"][language_var.get()]["project_name"])
project_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")
ttk.Entry(root, textvariable=project_name_var).grid(row=2, column=1, padx=5, pady=5, sticky="w")
machine_label = ttk.Label(root, text=translations["translations"][language_var.get()]["machine"])
machine_label.grid(row=3, column=0, padx=5, pady=5, sticky="w")
ttk.Entry(root, textvariable=machine_var).grid(row=3, column=1, padx=5, pady=5, sticky="w")

# Frame pour les champs contextuels
frame = ttk.Frame(root, style="TFrame")
frame.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky="nsw")

# Label pour l'image
image_label = tk.Label(root, borderwidth=2, relief="groove")
image_label.grid(row=0, column=2, rowspan=5, padx=5, pady=5, sticky="nsew")

# Bouton de génération
generate_button = ttk.Button(root, text=translations["translations"][language_var.get()]["generate_button"], command=save_and_generate)
generate_button.grid(row=5, column=0, columnspan=3, pady=10)

# Initialisation
update_fields()

# Configurer la grille
root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)
root.grid_columnconfigure(2, weight=1)
root.grid_rowconfigure(4, weight=1)

root.mainloop()