import sys
import json
import os
from datetime import datetime
# Imports au début du fichier (ajoutez si manquants)
import subprocess
import tkinter as tk
from tkinter import messagebox


# Mappage des identifiants fixes (identique à GUI.py pour cohérence)
path_type_map = {
    "conventional": {"fr": "Opposition", "en": "Conventional", "de": "Gegenlauffräsen", "es": "Convencional", "index": 1, "code": "1"},
    "climb": {"fr": "Avalant", "en": "Climb", "de": "Gleichlauffräsen", "es": "Ascendente", "index": 2, "code": "2"},
    "alternate": {"fr": "Alterné", "en": "Alternate", "de": "Abwechselnd", "es": "Alternado", "index": 3, "code": "3"},
    "right": {"fr": "Droite", "en": "Right", "de": "Rechts", "es": "Derecha", "index": 1, "code": "G02"},
    "left": {"fr": "Gauche", "en": "Left", "de": "Links", "es": "Izquierda", "index": 2, "code": "G03"}
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


def convert_legacy_to_fixed_id(value, mapping, lang="fr"):
    """Convertit une valeur traduite ou un code en identifiant fixe."""
    for fixed_id, data in mapping.items():
        if value == fixed_id or value == data.get(lang, "") or value == data.get("code", "") or value in [data.get(l, "") for l in ["fr", "en", "de", "es"]]:
            return fixed_id
    return value

def load_config():
    """Charge les derniers paramètres depuis config.json, s'il existe."""
    config_path = "config.json"
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = json.load(f)
            # Convertir les anciennes valeurs traduites ou codes en identifiants fixes
            lang = config.get("language", "fr")
            for section in ["surfacing", "contour_drilling", "corner_radius", "oblong_hole", "matrix_drilling", "threading"]:
                if section in config:
                    if "path_type" in config[section]:
                        config[section]["path_type"] = convert_legacy_to_fixed_id(config[section]["path_type"], path_type_map, lang)
                    if "drilling_type" in config[section]:
                        config[section]["drilling_type"] = convert_legacy_to_fixed_id(config[section]["drilling_type"], drilling_type_map, lang)
                    if "corner_type" in config[section]:
                        config[section]["corner_type"] = convert_legacy_to_fixed_id(config[section]["corner_type"], corner_type_map, lang)
                    if "thread_type" in config[section]:
                        config[section]["thread_type"] = convert_legacy_to_fixed_id(config[section]["thread_type"], thread_type_map, lang)
            return config
    return {}

def save_config(config):
    """Sauvegarde les paramètres dans config.json."""
    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)

# Charger des paramètres globaux au niveau module pour que les fonctions
# utilisent un coefficient de plongée (percent) même si `main()` n'a pas
# encore été exécuté. Les clés prises en charge (priorité) :
# - global_feed_rate_base
# - global_feed_rate_percent
# Compatibilité : on retombe sur les clés historiques si nécessaire.
_imported_config = load_config()
#_global_feed_rate_base = _imported_config.get("global_feed_rate_base", _imported_config.get("global_feed_rate_drill", 1800))
_percent_raw = _imported_config.get("global_feed_rate_percent", _imported_config.get("global_feed_rate_drill_percent", "50%"))
try:
    percent = int(str(_percent_raw).strip().strip("%"))
except Exception:
    percent = 100
#global_feed_rate_base = _global_feed_rate_base

def generate_header(project_name, machine_name, stock_x, stock_y, stock_z, global_units="mm"):  # MODIFIÉ: Ajout paramètre global_units avec défaut "mm"
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # MODIFIÉ: Choix conditionnel G20/G21
    units_code = "G21" if global_units == "mm" else "G20"
    header = f"""; NC file from Picture_CNC
; {project_name}
; {current_time}
; {machine_name}
; ({stock_x:.3f}, {stock_y:.3f}, {stock_z:.3f} {global_units})
{units_code} ;({global_units})
G90
M3 S1000
G04 P5
"""
    return header

def calculate_stock_dimensions(operations):
    # Charger la configuration pour accéder aux paramètres spécifiques
    config = load_config()
    operation = config.get("last_operation", "1")
    # CORRECTION: Définition de global_units (manquante dans main())
    global_units = config.get("global_units", "mm")
    if global_units not in ["mm", "in"]:
        print(f"AVERTISSEMENT: Unités invalides '{global_units}', fallback à 'mm'")
        global_units = "mm"

    # Mode 1 : Surfaçage
    if operation == "1":
        defaults = config.get("surfacing", {})
        width_x = defaults.get("width_x", 100.0)
        length_y = defaults.get("length_y", 100.0)
        tool_diameter = defaults.get("tool_diameter", 10.0)
        total_depth = defaults.get("total_depth", 1.0)
        clearance_height = defaults.get("clearance_height", 5.0)
        stock_x = width_x + tool_diameter
        stock_y = length_y + tool_diameter
        stock_z = total_depth + clearance_height
        return stock_x, stock_y, stock_z

    # Mode 2 : Perçages par détourage
    elif operation == "2":
        defaults = config.get("contour_drilling", {})
        hole_diameter = defaults.get("hole_diameter", 30.0)
        tool_diameter = defaults.get("tool_diameter", 10.0)
        total_depth = defaults.get("total_depth", 2.0)
        clearance_height = defaults.get("clearance_height", 5.0)
        drilling_type = defaults.get("drilling_type", "contour")

        if drilling_type == "outer":
            # Usinage extérieur : chemin à hole_radius + tool_radius
            stock_x = hole_diameter + 2 * tool_diameter
            stock_y = hole_diameter + 2 * tool_diameter
        else:
            # Blind ou Contour : usinage intérieur
            stock_x = hole_diameter + tool_diameter
            stock_y = hole_diameter + tool_diameter
        stock_z = total_depth + clearance_height
        return stock_x, stock_y, stock_z

    # Mode 3 : Perçages verticaux (matrice)
    elif operation == "3":
        defaults = config.get("matrix_drilling", {})
        num_cols = int(float(defaults.get("num_cols", 1)))
        num_rows = int(float(defaults.get("num_rows", 1)))
        spacing_x = float(defaults.get("spacing_x", 10.0))
        spacing_y = float(defaults.get("spacing_y", 10.0))
        total_depth = float(defaults.get("total_depth", 2.0))
        clearance_height = float(defaults.get("clearance_height", 5.0))
        stock_x = (num_cols - 1) * spacing_x if num_cols > 1 else 10.0  # Valeur minimale si un seul trou
        stock_y = (num_rows - 1) * spacing_y if num_rows > 1 else 10.0  # Valeur minimale si un seul trou
        stock_z = total_depth + clearance_height
        return stock_x, stock_y, stock_z

    # Mode 4 : Rayon sur 90°
    elif operation == "4":
        defaults = config.get("corner_radius", {})
        radius = defaults.get("radius", 10.0)
        tool_diameter = defaults.get("tool_diameter", 10.0)
        total_depth = defaults.get("total_depth", 2.0)
        clearance_height = defaults.get("clearance_height", 5.0)
        arc_radius = radius + tool_diameter / 2
        stock_x = 2 * arc_radius
        stock_y = 2 * arc_radius
        stock_z = total_depth + clearance_height
        return stock_x, stock_y, stock_z

    # Mode 5 : Trou oblong
    elif operation == "5":
        defaults = config.get("oblong_hole", {})
        length_x = defaults.get("length_x", 20.0)
        length_y = defaults.get("length_y", 20.0)
        tool_diameter = defaults.get("tool_diameter", 5.0)
        total_depth = defaults.get("total_depth", 2.0)
        clearance_height = defaults.get("clearance_height", 5.0)
        stock_x = length_x + tool_diameter
        stock_y = length_y + tool_diameter
        stock_z = total_depth + clearance_height
        return stock_x, stock_y, stock_z

    # Mode 6 : Filetage
    elif operation == "6":
        defaults = config.get("threading", {})
        hole_diameter = defaults.get("hole_diameter", 30.0)
        tool_diameter = defaults.get("tool_diameter", 10.0)
        total_depth = defaults.get("total_depth", 2.0)
        clearance_height = defaults.get("clearance_height", 5.0)
        stock_x = hole_diameter + tool_diameter
        stock_y = hole_diameter + tool_diameter
        stock_z = total_depth + clearance_height
        return stock_x, stock_y, stock_z

    # Cas par défaut : retourner 0 si aucune opération valide
    return 0, 0, 0

def surfacing(config):
    defaults = config.get("surfacing", {})
    start_x = defaults.get("start_x", 0.0)
    start_y = defaults.get("start_y", 0.0)
    start_z = defaults.get("start_z", 10.0)
    clearance_height = defaults.get("clearance_height", 5.0)
    tool_diameter = defaults.get("tool_diameter", 10.0)
    overlap_percent = defaults.get("overlap_percent", 50.0)
    width_x = defaults.get("width_x", 100.0)
    length_y = defaults.get("length_y", 100.0)
    total_depth = defaults.get("total_depth", 1.0)
    depth_per_pass = defaults.get("depth_per_pass", 1.0)
    feed_rate = defaults.get("feed_rate", 1800)
    spindle_speed = defaults.get("spindle_speed", 1000)
    path_type = defaults.get("path_type", "conventional")

    # Obtenir le code pour path_type
    path_type_code = path_type_map.get(path_type, {}).get("code", "1")
    path_type_label = path_type_map.get(path_type, {}).get("fr", "Opposition")
    print(f"Débogage: path_type lu = {path_type} (code = {path_type_code}, label = {path_type_label})")

    # Validation des paramètres
    if total_depth <= 0 or depth_per_pass <= 0 or tool_diameter <= 0 or width_x <= 0 or length_y <= 0:
        raise ValueError("Les dimensions et profondeurs doivent être positives.")
    if overlap_percent < 0 or overlap_percent >= 100:
        raise ValueError("Le chevauchement doit être entre 0 et 99%.")
    if clearance_height <= 0:
        raise ValueError("La hauteur de dégagement doit être positive.")
    if depth_per_pass > total_depth:
        raise ValueError("La profondeur par passe ne peut pas dépasser la profondeur totale.")

    step_over = tool_diameter * (1 - overlap_percent / 100)
    num_passes_z = int(total_depth / depth_per_pass) + (1 if total_depth % depth_per_pass != 0 else 0)
    num_passes_y = int(length_y / step_over) + (1 if length_y % step_over != 0 else 0)
    offset = tool_diameter / 2
    initial_x = start_x - offset
    initial_y = start_y - offset
    end_x = start_x + width_x
    end_y = start_y + length_y

    gcode = f"\n; Surfacing operation ({path_type_label})\n"
    gcode += f"G0 S{spindle_speed:.0f}  F{feed_rate:.0f}\n"
    gcode += f"G00 Z{clearance_height:.3f}  F{feed_rate:.0f}\n"

    if path_type_code == "2":  # En avalant (climb)
        gcode += f"G00 X{initial_x:.3f} Y{end_y:.3f}\n"
    elif path_type_code == "3":  # En alternance (alternate)
        gcode += f"G00 X{initial_x:.3f} Y{initial_y:.3f}\n"
    else:  # En opposition (conventional)
        gcode += f"G00 X{initial_x:.3f} Y{initial_y:.3f}\n"

    current_z = start_z
    for i in range(num_passes_z):
        current_z -= min(depth_per_pass, total_depth - i * depth_per_pass)
        gcode += f"; Pass {i+1} at Z={current_z:.3f}\n"
        gcode += f"G01 Z{current_z:.3f} F{feed_rate * percent / 100:.3f}\n"
        current_y = initial_y
        for j in range(num_passes_y):
            if current_y > start_y + length_y:
                continue
            if path_type_code == "3":  # En alternance
                gcode += f"G01 Y{current_y:.3f}  F{feed_rate:.0f}\n"
                if j % 2 == 0:
                    gcode += f"G01 X{end_x:.3f}  F{feed_rate:.0f}\n"
                else:
                    gcode += f"G01 X{start_x:.3f}  F{feed_rate:.0f}\n"
            else:  # En opposition ou En avalant
                if path_type_code == "2":  # En avalant
                    gcode += f"G01 Y{current_y:.3f}  F{feed_rate:.0f}\n"
                    gcode += f"G01 X{start_x:.3f}  F{feed_rate:.0f}\n"
                    if current_y + step_over <= start_y + length_y:
                        gcode += f"G00 X{end_x:.3f}\n"
                else:  # En opposition
                    gcode += f"G01 Y{current_y:.3f}  F{feed_rate:.0f}\n"
                    gcode += f"G01 X{end_x:.3f}  F{feed_rate:.0f}\n"
                    if current_y + step_over <= start_y + length_y:
                        gcode += f"G00 X{start_x:.3f}\n"
            current_y += step_over
        if current_y <= start_y + length_y:
            gcode += f"G01 Y{current_y:.3f}  F{feed_rate:.0f}\n"
    gcode += f"G00 Z{clearance_height:.3f}\n"

    return gcode, start_x, start_y, start_z, current_z, end_x, end_y, clearance_height

def contour_drilling(config):
    defaults = config.get("contour_drilling", {})
    start_x = defaults.get("start_x", 0.0)
    start_y = defaults.get("start_y", 0.0)
    start_z = defaults.get("start_z", 0.0)
    clearance_height = defaults.get("clearance_height", 5.0)
    tool_diameter = defaults.get("tool_diameter", 10.0)
    hole_diameter = defaults.get("hole_diameter", 30.0)
    total_depth = defaults.get("total_depth", 2.0)
    depth_per_pass = defaults.get("depth_per_pass", 1.0)
    feed_rate = defaults.get("feed_rate", 1800)
    spindle_speed = defaults.get("spindle_speed", 1000)
    path_type = defaults.get("path_type", "conventional")
    drilling_type = defaults.get("drilling_type", "contour")
    is_blind_hole = drilling_type == "blind"
    overlap_percent = defaults.get("overlap_percent", 50.0) if is_blind_hole else 0.0

    # Obtenir le label pour affichage
    path_type_label = path_type_map.get(path_type, {}).get("fr", "Opposition")
    drilling_type_label = drilling_type_map.get(drilling_type, {}).get("fr", "Trou traversant")

    # Validation des paramètres
    if total_depth <= 0 or depth_per_pass <= 0 or tool_diameter <= 0 or hole_diameter <= 0:
        raise ValueError("Les dimensions et profondeurs doivent être positives.")
    if hole_diameter <= tool_diameter:
        raise ValueError("Le diamètre du perçage doit être supérieur au diamètre de la fraise.")
    if is_blind_hole and (overlap_percent < 0 or overlap_percent >= 100):
        raise ValueError("Le chevauchement doit être entre 0 et 99%.")
    if clearance_height <= 0:
        raise ValueError("La hauteur de dégagement doit être positive.")
    if depth_per_pass > total_depth:
        raise ValueError("La profondeur par passe ne peut pas dépasser la profondeur totale.")

    num_passes_z = int(total_depth / depth_per_pass) + (1 if total_depth % depth_per_pass != 0 else 0)
    initial_x = start_x
    initial_y = start_y

    gcode = f"\n; Contour drilling operation\n"
    gcode += f"; ({path_type_label}, {drilling_type_label})\n"
    gcode += f"; D={hole_diameter:.1f} H={total_depth:.1f} Bit={tool_diameter}\n"
    gcode += f"; P={total_depth/depth_per_pass:.2f} x {depth_per_pass}mm\n"
    gcode += f"; (X,Y,Z = {start_x}, {start_y}, {start_z})\n\n"
    gcode += f"G0 S{spindle_speed:.0f}  F{feed_rate:.0f}\n"
    gcode += f"G00 Z{clearance_height:.3f}  F{feed_rate:.0f}\n"
    gcode += f"G00 X{initial_x:.3f} Y{initial_y:.3f}\n"

    hole_radius = hole_diameter / 2
    tool_radius = tool_diameter / 2
    if drilling_type == "outer":
        circle_radius = hole_radius + tool_radius  # Chemin extérieur
        num_circles = 1  # Un seul cercle pour Outer
    else:  # Contour ou Blind
        circle_radius = hole_radius - tool_radius  # Chemin intérieur
        if is_blind_hole:
            step_over = tool_diameter * (1 - overlap_percent / 100)
            num_circles = int((hole_radius - tool_radius) / step_over) + 1
        else:
            num_circles = 1  # Un seul cercle pour Contour

    current_z = start_z
    for i in range(num_passes_z):
        current_z -= min(depth_per_pass, total_depth - i * depth_per_pass)
        gcode += f"; Pass {i+1} at Z={current_z:.3f}\n"
        for j in range(num_circles):
            current_radius = circle_radius - j * step_over if is_blind_hole else circle_radius
            if is_blind_hole and current_radius < tool_radius:
                current_radius = tool_radius  # Limiter au rayon minimum de l'outil
            tangent_x = start_x + current_radius
            gcode += f"G00 X{tangent_x:.3f} Y{initial_y:.3f}\n"
            gcode += f"G01 Z{current_z:.3f} F{feed_rate * percent / 100:.3f}\n"
            if path_type == "conventional":
                gcode += f"G02 X{tangent_x:.3f} Y{initial_y:.3f} I{-current_radius:.3f} J0.000  F{feed_rate:.0f}\n"
            else:
                gcode += f"G03 X{tangent_x:.3f} Y{initial_y:.3f} I{-current_radius:.3f} J0.000  F{feed_rate:.0f}\n"

    gcode += f"G00 Z{clearance_height:.3f}\n"
    gcode += f"G00 X{initial_x:.3f} Y{initial_y:.3f}\n"

    return gcode, start_x, start_y, start_z, current_z, start_x + hole_diameter, start_y + hole_diameter, clearance_height

def threading(config):
    defaults = config.get("threading", {})
    start_x = defaults.get("start_x", 0.0)
    start_y = defaults.get("start_y", 0.0)
    start_z = defaults.get("start_z", 0.0)
    clearance_height = defaults.get("clearance_height", 5.0)
    tool_diameter = defaults.get("tool_diameter", 10.0)
    hole_diameter = defaults.get("hole_diameter", 30.0)
    total_depth = defaults.get("total_depth", 2.0)
    depth_per_pass = defaults.get("depth_per_pass", 0.5)
    feed_rate = defaults.get("feed_rate", 1800)
    spindle_speed = defaults.get("spindle_speed", 1000)
    path_type = defaults.get("path_type", "right")
    thread_pitch = defaults.get("thread_pitch", 10.0)
    thread_number = int(defaults.get("thread_number", 6))
    thread_type = defaults.get("thread_type", "nut_internal")
    overlap_percent = defaults.get("overlap_percent", 50.0)  # Not used in this implementation

    # Obtenir le code et le label pour path_type
    path_type_code = path_type_map.get(path_type, {}).get("code", "G02")
    path_type_label = path_type_map.get(path_type, {}).get("fr", "Droite")
    thread_type_label = thread_type_map.get(thread_type, {}).get("fr", "Ecrou (Interne)")

    # Validation des paramètres
    if hole_diameter <= tool_diameter:
        raise ValueError("Le diamètre du perçage doit être supérieur au diamètre de la fraise.")
    if thread_pitch <= 0 or thread_number <= 0:
        raise ValueError("Le pas et le nombre de filets doivent être positifs.")
    if total_depth <= 0 or depth_per_pass <= 0:
        raise ValueError("Les profondeurs doivent être positives.")
    if clearance_height <= 0:
        raise ValueError("La hauteur de dégagement doit être positive.")

    # Calcul du nombre de passes radiales (total_depth / depth_per_pass)
    num_radial_passes = int(total_depth / depth_per_pass)
    if total_depth % depth_per_pass != 0:
        num_radial_passes += 1

    # Rayon du trou et de la fraise
    hole_radius = hole_diameter / 2
    tool_radius = tool_diameter / 2

    # Bloc conditionnel pour Ecrou (Interne) ou Vis (Externe)
    if thread_type == "nut_internal":
        # Bloc pour filetage interne (Ecrou)
        base_x = hole_radius - depth_per_pass - tool_radius - total_depth
        i_value = -base_x

        gcode = f"\n; Threading operation\n"
        gcode += f"; ({thread_type_label}, {path_type_label})\n"
        gcode += f"; D={hole_diameter:.1f} H={thread_number*thread_pitch:.1f} P={thread_pitch:.1f}\n"
        gcode += f"; (X,Y,Z = {start_x}, {start_y}, {start_z})\n\n"
        gcode += f"G00 Z{clearance_height} S{spindle_speed:.0f}\n"
        gcode += f"G00 X{start_x:.3f} Y{start_y:.3f} Z{start_z:.3f}  F{feed_rate:.0f} S{spindle_speed:.0f}\n"

        for pass_num in range(1, num_radial_passes + 1):
            current_x = base_x + (pass_num + 1) * depth_per_pass
            gcode += f"G01 X{start_x + current_x:.3f} Y{start_y:.3f}\n"
            for turn in range(1, thread_number + 1):
                next_z = start_z - thread_pitch * turn
                gcode += f"{path_type_code} X{start_x + current_x:.3f} Y{start_y:.3f} I{-start_x - current_x + start_x:.3f} J0.000 Z{next_z:.3f}\n"
            gcode += f"{path_type_code} X{start_x + current_x:.3f} Y{start_y:.3f} I{-start_x - current_x + start_x:.3f} J0.000\n"
            gcode += f"G00 X{start_x:.3f} Y{start_y:.3f}\n"
            if pass_num < num_radial_passes:
                gcode += f"G00 Z{start_z:.3f}\n\n"
    else:  # screw_external
        # Bloc pour filetage externe (Vis)
        base_x = hole_radius - depth_per_pass + tool_radius
        i_value = -base_x

        gcode = f"\n; Threading operation\n"
        gcode += f"; ({thread_type_label}, {path_type_label})\n"
        gcode += f"; D={hole_diameter:.1f} H={thread_number*thread_pitch:.1f} P={thread_pitch:.1f}\n"
        gcode += f"; (X,Y,Z = {start_x}, {start_y}, {start_z})\n\n"
        gcode += f"G00 Z{clearance_height} S{spindle_speed:.0f}\n"
        gcode += f"G00 X{start_x + hole_radius + tool_radius + total_depth:.3f} Y{start_y:.3f} Z{start_z:.3f}  F{feed_rate:.0f}\n"

        for pass_num in range(1, num_radial_passes + 1):
            current_x = base_x - (pass_num) * depth_per_pass + depth_per_pass
            gcode += f"G01 X{start_x + current_x:.3f} Y{start_y:.3f}\n"
            for turn in range(1, thread_number + 1):
                next_z = start_z - thread_pitch * turn
                gcode += f"{path_type_code} X{start_x + current_x:.3f} Y{start_y:.3f} I{-start_x - current_x + start_x:.3f} J0.000 Z{next_z:.3f}\n"
            gcode += f"{path_type_code} X{start_x + current_x:.3f} Y{start_y:.3f} I{-start_x - current_x + start_x:.3f} J0.000\n"
            gcode += f"G00 X{start_x + hole_radius + tool_radius + total_depth:.3f} Y{start_y:.3f}\n"
            if pass_num < num_radial_passes:
                gcode += f"G00 Z{start_z:.3f}\n\n"

    # Fin à Z clearance
    gcode += f"G00 Z{clearance_height:.3f}\n"

    # Pour calculate_stock_dimensions
    end_x = start_x + hole_diameter
    end_y = start_y + hole_diameter
    current_z = start_z - thread_number * thread_pitch

    return gcode, start_x, start_y, start_z, current_z, end_x, end_y, clearance_height

def matrix_drilling(config):
    defaults = config.get("matrix_drilling", {})
    start_x = defaults.get("start_x", 0.0)
    start_y = defaults.get("start_y", 0.0)
    start_z = defaults.get("start_z", 0.0)
    num_cols = int(float(defaults.get("num_cols", 1)))
    spacing_x = float(defaults.get("spacing_x", 10.0))
    num_rows = int(float(defaults.get("num_rows", 1)))
    spacing_y = float(defaults.get("spacing_y", 10.0))
    clearance_height = float(defaults.get("clearance_height", 5.0))
    deburr_height = float(defaults.get("deburr_height", 2.0))
    total_depth = float(defaults.get("total_depth", 2.0))
    depth_per_pass = float(defaults.get("depth_per_pass", 0.5))
    feed_rate = float(defaults.get("feed_rate", 1800))
    spindle_speed = float(defaults.get("spindle_speed", 1000))

    # Validation des paramètres
    if total_depth <= 0 or depth_per_pass <= 0:
        raise ValueError("Les profondeurs doivent être positives.")
    if clearance_height <= 0 or deburr_height <= 0:
        raise ValueError("La hauteur de dégagement et de débourrage doivent être positives.")
    if depth_per_pass > total_depth:
        raise ValueError("La profondeur par passe ne peut pas dépasser la profondeur totale.")
    if num_cols < 1 or num_rows < 1:
        raise ValueError("Le nombre de perçages doit être au moins 1.")
    if spacing_x < 0 or spacing_y < 0:
        raise ValueError("Les pas sur X et Y doivent être positifs ou nuls.")

    num_passes_z = int(total_depth / depth_per_pass) + (1 if total_depth % depth_per_pass != 0 else 0)
    end_x = start_x + (num_cols - 1) * spacing_x
    end_y = start_y + (num_rows - 1) * spacing_y

    gcode = f"\n; Matrix drilling RAST\n"
    gcode += f"; {num_cols} x {num_rows} holes\n"
    gcode += f"; Pas X= {spacing_x}, Pas Y= {spacing_y}\n"
    gcode += f"; (X,Y,Z = {start_x}, {start_y}, {start_z}, H = {total_depth})\n\n"
    gcode += f"G0 S{spindle_speed:.0f}  F{feed_rate:.0f}\n"
    gcode += f"G00 Z{clearance_height:.3f}  F{feed_rate:.0f}\n"
    gcode += f"G00 X{start_x:.3f} Y{start_y:.3f}\n"

    for j in range(num_rows):
        current_y = start_y + j * spacing_y
        x_positions = [start_x + i * spacing_x for i in range(num_cols)]
        if j % 2 == 1:  # Inverse l'ordre pour les lignes impaires
            x_positions = x_positions[::-1]
        for current_x in x_positions:
            gcode += f"; Hole at X={current_x:.3f}, Y={current_y:.3f}\n"
            gcode += f"G00 X{current_x:.3f} Y{current_y:.3f}\n"
            current_z = start_z
            for k in range(num_passes_z):
                current_z -= min(depth_per_pass, total_depth - k * depth_per_pass)
                gcode += f"; Pass {k+1} at Z={current_z:.3f}\n"
                gcode += f"G01 Z{current_z:.3f} F{feed_rate * percent / 100:.3f}\n"
                if k < num_passes_z - 1:
                    gcode += f"G00 Z{deburr_height:.3f}\n"
            gcode += f"G00 Z{clearance_height:.3f}\n"

    return gcode, start_x, start_y, start_z, current_z, end_x, end_y, clearance_height

def corner_radius(config):
    defaults = config.get("corner_radius", {})
    start_z = defaults.get("start_z", 0.0)
    clearance_height = defaults.get("clearance_height", 5.0)
    radius = defaults.get("radius", 10.0)
    tool_diameter = defaults.get("tool_diameter", 10.0)
    total_depth = defaults.get("total_depth", 2.0)
    depth_per_pass = defaults.get("depth_per_pass", 0.5)
    feed_rate = defaults.get("feed_rate", 1800)
    spindle_speed = defaults.get("spindle_speed", 1000)
    path_type = defaults.get("path_type", "conventional")
    corner_type = defaults.get("corner_type", "front_left")

    # Obtenir le label pour affichage
    path_type_label = path_type_map.get(path_type, {}).get("fr", "Opposition")
    corner_type_label = corner_type_map.get(corner_type, {}).get("fr", "Avant Gauche (AVG)")

    # Validation des paramètres
    if radius <= 0 or tool_diameter <= 0:
        raise ValueError("Le rayon et le diamètre de la fraise doivent être positifs.")
    if total_depth <= 0 or depth_per_pass <= 0:
        raise ValueError("Les profondeurs doivent être positives.")
    if clearance_height <= 0:
        raise ValueError("La hauteur de dégagement doit être positive.")
    if depth_per_pass > total_depth:
        raise ValueError("La profondeur par passe ne peut pas dépasser la profondeur totale.")

    num_passes_z = int(total_depth / depth_per_pass) + (1 if total_depth % depth_per_pass != 0 else 0)
    tool_radius = tool_diameter / 2
    arc_radius = radius + tool_radius

    gcode = f"\n; Corner radius operation ({corner_type_label}, {path_type_label})\n"
    gcode += f"G0 S{spindle_speed:.0f}  F{feed_rate:.0f}\n"
    gcode += f"G00 Z{clearance_height:.3f}  F{feed_rate:.0f}\n"
    gcode += "G91\n"  # Mode relatif pour les arcs

    # Définir les commandes d'arc et retours selon corner_type et path_type
    if corner_type == "front_left":
        if path_type == "conventional":
            arc_cmd = f"G03 X{arc_radius:.3f} Y-{arc_radius:.3f} I{arc_radius:.3f} J0.000  F{feed_rate:.0f}"
            return_x = f"G00 X-{arc_radius:.3f}"
            return_y = f"G00 Y{arc_radius:.3f}"
        else:
            arc_cmd = f"G02 X-{arc_radius:.3f} Y{arc_radius:.3f} I0.000 J{arc_radius:.3f}  F{feed_rate:.0f}"
            return_x = f"G00 X{arc_radius:.3f}"
            return_y = f"G00 Y-{arc_radius:.3f}"
    elif corner_type == "front_right":
        if path_type == "conventional":
            arc_cmd = f"G03 X{arc_radius:.3f} Y{arc_radius:.3f} I0.000 J{arc_radius:.3f}  F{feed_rate:.0f}"
            return_x = f"G00 X-{arc_radius:.3f}"
            return_y = f"G00 Y-{arc_radius:.3f}"
        else:
            arc_cmd = f"G02 X-{arc_radius:.3f} Y-{arc_radius:.3f} I-{arc_radius:.3f} J0.000  F{feed_rate:.0f}"
            return_x = f"G00 X{arc_radius:.3f}"
            return_y = f"G00 Y{arc_radius:.3f}"
    elif corner_type == "rear_right":
        if path_type == "conventional":
            arc_cmd = f"G03 X-{arc_radius:.3f} Y{arc_radius:.3f} I-{arc_radius:.3f} J0.000  F{feed_rate:.0f}"
            return_x = f"G00 X{arc_radius:.3f}"
            return_y = f"G00 Y-{arc_radius:.3f}"
        else:
            arc_cmd = f"G02 X{arc_radius:.3f} Y-{arc_radius:.3f} I0.000 J-{arc_radius:.3f}  F{feed_rate:.0f}"
            return_x = f"G00 X-{arc_radius:.3f}"
            return_y = f"G00 Y{arc_radius:.3f}"
    elif corner_type == "rear_left":
        if path_type == "conventional":
            arc_cmd = f"G03 X-{arc_radius:.3f} Y-{arc_radius:.3f} I0.000 J-{arc_radius:.3f}  F{feed_rate:.0f}"
            return_x = f"G00 X{arc_radius:.3f}"
            return_y = f"G00 Y{arc_radius:.3f}"
        else:
            arc_cmd = f"G02 X{arc_radius:.3f} Y{arc_radius:.3f} I{arc_radius:.3f} J0.000  F{feed_rate:.0f}"
            return_x = f"G00 X-{arc_radius:.3f}"
            return_y = f"G00 Y-{arc_radius:.3f}"

    # Exécuter les passes
    for i in range(num_passes_z):
        depth = min(depth_per_pass, total_depth - i * depth_per_pass)
        target_z = start_z - (i * depth_per_pass + depth)
        gcode += f"; Pass {i+1} at Z={target_z:.3f}\n"
        gcode += "G90\n"  # Mode absolu pour Z
        gcode += f"G01 Z{target_z:.3f} F{feed_rate * percent / 100:.3f}\n"
        gcode += "G91\n"  # Retour au mode relatif pour l'arc
        gcode += f"{arc_cmd}\n"
        gcode += "G90\n"
        gcode += f"G00 Z{clearance_height:.3f}\n"
        if i < num_passes_z - 1:
            gcode += "G91\n"
            gcode += f"{return_x}\n"
            gcode += f"{return_y}\n"

    stock_x = arc_radius * 2
    stock_y = arc_radius * 2
    stock_z = clearance_height + total_depth

    return gcode, 0.0, 0.0, start_z, target_z, stock_x, stock_y, clearance_height + total_depth

def oblong_hole(config):
    defaults = config.get("oblong_hole", {})
    start_x = defaults.get("start_x", 0.0)
    start_y = defaults.get("start_y", 0.0)
    start_z = defaults.get("start_z", 0.0)
    length_x = defaults.get("length_x", 20.0)
    length_y = defaults.get("length_y", 20.0)
    width = defaults.get("width", 10.0)
    tool_diameter = defaults.get("tool_diameter", 5.0)
    path_type = defaults.get("path_type", "conventional")
    total_depth = defaults.get("total_depth", 2.0)
    depth_per_pass = defaults.get("depth_per_pass", 0.5)
    feed_rate = defaults.get("feed_rate", 1800)
    spindle_speed = defaults.get("spindle_speed", 1000)

    # Obtenir le label pour affichage
    path_type_label = path_type_map.get(path_type, {}).get("fr", "Opposition")

    # Validation des paramètres
    if length_x < 0 or length_y < 0 or width <= 0 or tool_diameter <= 0:
        raise ValueError("Les dimensions et le diamètre de la fraise doivent être positifs.")
    if total_depth <= 0 or depth_per_pass <= 0:
        raise ValueError("Les profondeurs doivent être positives.")
    if depth_per_pass > total_depth:
        raise ValueError("La profondeur par passe ne peut pas dépasser la profondeur totale.")
    if width < tool_diameter:
        raise ValueError("La largeur doit être au moins égale au diamètre de la fraise.")

    num_passes_z = int(total_depth / depth_per_pass) + (1 if total_depth % depth_per_pass != 0 else 0)
    half_width = (width - tool_diameter) / 2
    half_length_x = length_x / 2
    half_length_y = length_y / 2

    gcode = f"\n; Oblong hole operation ({path_type_label})\n"
    gcode += f"G0 S{spindle_speed:.0f}  F{feed_rate:.0f}\n"
    gcode += f"G90\n"
    gcode += f"G00 X{start_x:.3f} Y{start_y:.3f} Z{start_z:.3f}  F{feed_rate:.0f}\n"

    for i in range(num_passes_z):
        current_depth = min((i + 1) * depth_per_pass, total_depth)
        target_z = start_z - current_depth
        gcode += f"; Pass {i+1} at Z={target_z:.3f}\n"

       
        if path_type == "conventional":
            gcode += f"G90\n"
            gcode += f"G00 X{start_x:.3f} Y{start_y-half_width:.3f} Z{start_z:.3f}  F{feed_rate:.0f}\n"
            gcode += f"G01 Z{target_z:.3f} F{feed_rate * percent / 100:.3f}\n"
            gcode += "G91\n"
            gcode += f"G00 X{-half_length_x:.3f} Y{-half_length_y:.3f}\n"
            gcode += f"G02 X{-half_width:.3f} Y{half_width:.3f} I0.000 J{half_width:.3f}  F{feed_rate:.0f}\n"
            gcode += f"G01 X0.000 Y{length_y:.3f}  F{feed_rate:.0f}\n"
            gcode += f"G02 X{half_width:.3f} Y{half_width:.3f} I{half_width:.3f} J0.000  F{feed_rate:.0f}\n"
            gcode += f"G01 X{length_x:.3f} Y0.000  F{feed_rate:.0f}\n"
            gcode += f"G02 X{half_width:.3f} Y{-half_width:.3f} I0.000 J{-half_width:.3f}  F{feed_rate:.0f}\n"
            gcode += f"G01 X0.000 Y{-length_y:.3f}  F{feed_rate:.0f}\n"
            gcode += f"G02 X{-half_width:.3f} Y{-half_width:.3f} I{-half_width:.3f} J0.000  F{feed_rate:.0f}\n"
            gcode += f"G01 X{-length_x:.3f} Y0.000  F{feed_rate:.0f}\n"
            gcode += "G90\n"
        else:
            gcode += f"G90\n"
            gcode += f"G00 X{start_x-half_width:.3f} Y{start_y-(length_y):.3f} Z{start_z:.3f}  F{feed_rate:.0f}\n"
            gcode += f"G01 Z{target_z:.3f} F{feed_rate * percent / 100:.3f}\n"
            gcode += "G91\n"
            gcode += f"G00 X{-half_length_x:.3f} Y{half_length_y:.3f}\n"
            gcode += f"G03 X{half_width:.3f} Y{-half_width:.3f} I{half_width:.3f} J0.000  F{feed_rate:.0f}\n"
            gcode += f"G01 X{length_x:.3f} Y0.000  F{feed_rate:.0f}\n"
            gcode += f"G03 X{half_width:.3f} Y{half_width:.3f} I0.000 J{half_width:.3f}  F{feed_rate:.0f}\n"
            gcode += f"G01 X0.000 Y{length_y:.3f}  F{feed_rate:.0f}\n"
            gcode += f"G03 X{-half_width:.3f} Y{half_width:.3f} I{-half_width:.3f} J0.000  F{feed_rate:.0f}\n"
            gcode += f"G01 X{-length_x:.3f} Y0.000  F{feed_rate:.0f}\n"
            gcode += f"G03 X{-half_width:.3f} Y{-half_width:.3f} I0.000 J{-half_width:.3f}  F{feed_rate:.0f}\n"
            gcode += f"G01 X0.000 Y{-length_y:.3f}  F{feed_rate:.0f}\n"
            gcode += "G90\n"

 
    gcode += f"G00 X{start_x:.3f} Y{start_y:.3f} Z{start_z:.3f}\n"
    gcode += "G90\n"

    stock_x = length_x
    stock_y = length_y
    stock_z = start_z + total_depth

    return gcode, start_x - half_length_x, start_y - half_length_y, start_z, start_z - total_depth, start_x + half_length_x, start_y + half_length_y, stock_z

def main():
    config = load_config()
    project_name = config.get("project_name", "test")
    machine_name = config.get("machine", "CNC_450x800")
    operation = config.get("last_operation", "1")

    # Récupérer la valeur de base (vitesse max)
    # Récupérer la valeur de base (vitesse max) — priorité à la nouvelle clé
    #base_feed_rate = config.get("global_feed_rate_base", config.get("global_feed_rate_drill", 1800))

    # Récupérer le pourcentage depuis config.json (ex: "75%") — priorité à la nouvelle clé
    percent_str = config.get("global_feed_rate_percent", config.get("global_feed_rate_drill_percent", "25%"))
    percent_str = str(percent_str).strip().strip("%")
    global percent
    print(f"Pourcentage de vitesse de coupe (plongée) configuré: {percent_str}%")
    try:
        percent = int(percent_str)
    except ValueError:
        percent = 100
    print(f"Pourcentage de vitesse calculé: {percent/100}%")

    # Calculer la vitesse effective (si besoin)
    #effective_feed_rate = int(base_feed_rate * percent / 100)
    
    # AJOUT OBLIGATOIRE : définition de global_units
    global_units = config.get("global_units", "mm")
    if global_units not in ["mm", "in"]:
        print(f"AVERTISSEMENT: Unités invalides '{global_units}', fallback à 'mm'")
        global_units = "mm"

    operation_map = {
        "1": "Surfaçage",
        "2": "Perçages par détourage",
        "3": "Perçages verticaux (matrice)",
        "4": "Rayon sur 90°",
        "5": "Trou oblong",
        "6": "Filetage"
    }
    selected_operation = operation_map.get(operation, "Surfaçage")
    print(f"Mode sélectionné : {selected_operation} (ID: {operation})")
    print(f"Unités globales : {global_units}")  # Maintenant OK

    # Étape 2 : Exécuter la fonction correspondante avec les paramètres du mode
    operations = []
    try:
        if operation == "1":
            gcode, start_x, start_y, start_z, current_z, end_x, end_y, clearance_height = surfacing(config)
            operations.append((gcode, start_x, start_y, start_z, current_z, end_x, end_y, clearance_height))
        elif operation == "2":
            gcode, start_x, start_y, start_z, current_z, end_x, end_y, clearance_height = contour_drilling(config)
            operations.append((gcode, start_x, start_y, start_z, current_z, end_x, end_y, clearance_height))
        elif operation == "6":
            gcode, start_x, start_y, start_z, current_z, end_x, end_y, clearance_height = threading(config)
            operations.append((gcode, start_x, start_y, start_z, current_z, end_x, end_y, clearance_height))
        elif operation == "3":
            gcode, start_x, start_y, start_z, current_z, end_x, end_y, clearance_height = matrix_drilling(config)
            operations.append((gcode, start_x, start_y, start_z, current_z, end_x, end_y, clearance_height))
        elif operation == "4":
            gcode, start_x, start_y, start_z, current_z, end_x, end_y, clearance_height = corner_radius(config)
            operations.append((gcode, start_x, start_y, start_z, current_z, end_x, end_y, clearance_height))
        elif operation == "5":
            gcode, start_x, start_y, start_z, current_z, end_x, end_y, clearance_height = oblong_hole(config)
            operations.append((gcode, start_x, start_y, start_z, current_z, end_x, end_y, clearance_height))
        else:
            raise ValueError(f"Mode inconnu : {operation}")

        # Étape 3 : Calculer les dimensions et générer le fichier
        stock_x, stock_y, stock_z = calculate_stock_dimensions(operations)
        # MODIFIÉ: Passage de global_units à generate_header
        gcode = generate_header(project_name, machine_name, stock_x, stock_y, stock_z, global_units)
        for op, _, _, _, _, _, _, _ in operations:
            gcode += op
        gcode += "G90\nM5\nM30\n"

        # Nettoyer project_name pour éviter les caractères non valides
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            project_name = project_name.replace(char, '_')

        # Définir le nom du fichier et créer le dossier NC
        filename = f"NC/{operation}_{project_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.nc"
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        # Vérifier les permissions d'écriture
        if not os.access(os.path.dirname(filename), os.W_OK):
            raise PermissionError(f"Pas de permissions d'écriture dans {os.path.dirname(filename)}")

        # Écrire le fichier G-code
        with open(filename, "w") as file:
            file.write(gcode)
        print(f"G-code sauvegardé dans {filename}")

        # Afficher messagebox
        tk.Tk().withdraw()
        tk.messagebox.showinfo("Confirmation", f"G-code sauvegardé dans\n{filename}")

        # Utiliser des chemins absolus normalisés
        abs_filename = os.path.normpath(os.path.abspath(filename))
        abs_display_script = os.path.normpath(os.path.abspath("display_gcode_3d.py"))

        # Vérifier l'existence des fichiers
        if not os.path.exists(abs_filename):
            raise FileNotFoundError(f"Fichier G-code non trouvé : {abs_filename}")
        if not os.path.exists(abs_display_script):
            raise FileNotFoundError(f"Script display_gcode_3d.py non trouvé : {abs_display_script}")

        # Définir l'interpréteur Python de l'environnement virtuel
        venv_python = os.path.normpath(os.path.join(os.path.dirname(__file__), "venv", "Scripts", "python.exe"))
        if not os.path.exists(venv_python):
            print(f"Débogage: Interpréteur de l'environnement virtuel non trouvé, utilisation de sys.executable : {sys.executable}")
            venv_python = sys.executable

        # Propager l'environnement virtuel
        env = os.environ.copy()
        venv_site_packages = os.path.normpath(os.path.join(os.path.dirname(__file__), "venv", "Lib", "site-packages"))
        env["PYTHONPATH"] = venv_site_packages + (f";{env.get('PYTHONPATH', '')}" if env.get('PYTHONPATH') else "")
        env["PATH"] = os.path.normpath(os.path.join(os.path.dirname(__file__), "venv", "Scripts")) + f";{env['PATH']}"

        # Journaliser les informations
        print(f"Débogage: Interpréteur utilisé : {venv_python}")
        print(f"Débogage: Script de visualisation : {abs_display_script}")
        print(f"Débogage: Fichier G-code : {abs_filename}")
        print(f"Débogage: PYTHONPATH : {env['PYTHONPATH']}")
        print(f"Débogage: PATH : {env['PATH']}")

        # Lancer display_gcode_3d.py de manière non bloquante
        subprocess.Popen([venv_python, abs_display_script, abs_filename], env=env)
        print("Débogage: display_gcode_3d.py lancé en mode non bloquant")

    except Exception as e:
        print(f"Une erreur s'est produite : {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        tk.Tk().withdraw()
        tk.messagebox.showerror("Erreur", f"Échec de la génération : {str(e)}")

if __name__ == "__main__":
    main()