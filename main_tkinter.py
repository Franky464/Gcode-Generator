import sys
import json
import os
from datetime import datetime

def load_config():
    """Charge les derniers paramètres depuis config.json, s'il existe."""
    config_path = "config.json"
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)
    return {}

def save_config(config):
    """Sauvegarde les paramètres dans config.json."""
    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)

def save_config(config):
    """Sauvegarde les paramètres dans config.json."""
    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)

def generate_header(project_name, machine_name, stock_x, stock_y, stock_z):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f"""; NC file from Picture_CNC
; {project_name}
; {current_time}
; {machine_name}
; [{stock_x:.3f}, {stock_y:.3f}, {stock_z:.3f}]

G21
G90
M3 S1000
G04 P5
"""
    return header

def calculate_stock_dimensions(operations):
    min_x, min_y, min_z = float('inf'), float('inf'), float('inf')
    max_x, max_y, max_z = float('-inf'), float('-inf'), float('-inf')

    for op in operations:
        _, start_x, start_y, start_z, current_z, end_x, end_y, clearance_height = op
        min_x = min(min_x, start_x)
        min_y = min(min_y, start_y)
        min_z = min(min_z, current_z)
        max_x = max(max_x, end_x)
        max_y = max(max_y, end_y)
        max_z = max(max_z, clearance_height)

    if min_x == float('inf'):
        return 0, 0, 0

    stock_x = max_x - min_x
    stock_y = max_y - min_y
    stock_z = max_z - min_z
    return stock_x, stock_y, stock_z

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
    path_type = defaults.get("path_type", "1")  # Valeur brute depuis config.json

    # Mapping bidirectionnel pour path_type
    path_type_map = {
        "1": "Opposition",
        "2": "Avalant",
        "3": "Alternance",
        "Opposition": "1",
        "Avalant": "2",
        "Alternance": "3"
    }
    path_type_code = path_type_map.get(path_type, path_type)  # Utilise la valeur brute si elle est déjà un label
    path_type_label = path_type_map.get(path_type_code, "Opposition")
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
    gcode += f"G0 S{spindle_speed:.1f} f{feed_rate}\n"
    gcode += f"G00 Z{clearance_height:.3f} f{feed_rate}\n"

    if path_type_code == "2":  # En avalant
        gcode += f"G00 X{initial_x:.3f} Y{end_y:.3f}\n"
    elif path_type_code == "3":  # En alternance
        gcode += f"G00 X{initial_x:.3f} Y{initial_y:.3f}\n"
    else:  # En opposition (défaut ou 1)
        gcode += f"G00 X{initial_x:.3f} Y{initial_y:.3f}\n"

    current_z = start_z
    for i in range(num_passes_z):
        current_z -= min(depth_per_pass, total_depth - i * depth_per_pass)
        gcode += f"; Pass {i+1} at Z={current_z:.3f}\n"
        gcode += f"G01 Z{current_z:.3f}\n"
        current_y = initial_y
        for j in range(num_passes_y):
            if current_y > start_y + length_y:
                continue
            if path_type_code == "3":  # En alternance
                gcode += f"G01 Y{current_y:.3f}\n"
                if j % 2 == 0:
                    gcode += f"G01 X{end_x:.3f}\n"
                else:
                    gcode += f"G01 X{start_x:.3f}\n"
            else:  # En opposition ou En avalant
                if path_type_code == "2":  # En avalant
                    gcode += f"G01 Y{current_y:.3f}\n"
                    gcode += f"G01 X{start_x:.3f}\n"
                    if current_y + step_over <= start_y + length_y:
                        gcode += f"G00 X{end_x:.3f}\n"
                else:  # En opposition
                    gcode += f"G01 Y{current_y:.3f}\n"
                    gcode += f"G01 X{end_x:.3f}\n"
                    if current_y + step_over <= start_y + length_y:
                        gcode += f"G00 X{start_x:.3f}\n"
            current_y += step_over
        if current_y <= start_y + length_y:
            gcode += f"G01 Y{current_y:.3f}\n"
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
    path_type = {"Opposition": "Opposition", "Avalant": "Avalant"}.get(defaults.get("path_type", "Opposition"), "Opposition")
    is_blind_hole = defaults.get("is_blind_hole", False)
    overlap_percent = defaults.get("overlap_percent", 50.0) if is_blind_hole else 0.0

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
    gcode += f"; ({path_type}, {'trou borgne' if is_blind_hole else 'trou traversant'})"
    gcode += f"\n; D={hole_diameter:.1f} H={total_depth:.1f} Bit={tool_diameter}"
    gcode += f"\n; P={total_depth/depth_per_pass} x {depth_per_pass}mm"
    gcode += f"\n; X,Y,Z = {start_x}, {start_y}, {start_z}\n\n"
    gcode += f"G0 S{spindle_speed:.1f} f{feed_rate}\n"
    gcode += f"G00 Z{clearance_height:.3f} f{feed_rate}\n"
    gcode += f"G00 X{initial_x:.3f} Y{initial_y:.3f}\n"

    hole_radius = hole_diameter / 2
    tool_radius = tool_diameter / 2
    step_over = tool_diameter * (1 - overlap_percent / 100) if is_blind_hole else hole_radius
    num_circles = int((hole_radius - tool_radius) / step_over) + 1 if is_blind_hole else 1

    current_z = start_z
    for i in range(num_passes_z):
        current_z -= min(depth_per_pass, total_depth - i * depth_per_pass)
        gcode += f"; Pass {i+1} at Z={current_z:.3f}\n"
        for j in range(num_circles):
            circle_radius = tool_radius + j * step_over if is_blind_hole else hole_radius - tool_radius
            if circle_radius > hole_radius - tool_radius:
                circle_radius = hole_radius - tool_radius
            tangent_x = start_x + circle_radius 
            gcode += f"G00 X{tangent_x:.3f} Y{initial_y:.3f}\n"
            gcode += f"G01 Z{current_z:.3f}\n"
            if path_type == "Opposition":
                gcode += f"G02 X{tangent_x:.3f} Y{initial_y:.3f} I{-circle_radius:.3f} J0.000\n"
            else:
                gcode += f"G03 X{tangent_x:.3f} Y{initial_y:.3f} I{-circle_radius:.3f} J0.000\n"

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
    path_type = {"Droite": "G02", "Gauche": "G03"}.get(defaults.get("path_type", "G03"), "G03")
    thread_pitch = defaults.get("thread_pitch", 10.0)
    thread_number = int(defaults.get("thread_number", 6))
    thread_type = defaults.get("thread_type", "Ecrou (Interne)")  # Nouveau paramètre
    overlap_percent = defaults.get("overlap_percent", 50.0)  # Not used in this implementation

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
    if thread_type == "Ecrou (Interne)":
        # Bloc actuel pour filetage interne (Ecrou)
        base_x = hole_radius - depth_per_pass - tool_radius - total_depth # Formule du commentaire pour première passe
        i_value = -base_x  # Comme dans l'exemple

        gcode = f"\n; Threading operation"
        gcode += f"\n;(Ecrou, {defaults.get('path_type', 'Left')})"
        gcode += f"\n; D={hole_diameter:.1f} H={thread_number*thread_pitch:.1f} P={thread_pitch:.1f}"
        gcode += f"\n; X,Y,Z = {start_x}, {start_y}, {start_z}\n\n"
        gcode += f"G00 Z{clearance_height} S{spindle_speed:.1f}\n"
        gcode += f"G00 X{start_x:.3f} Y{start_y:.3f} Z{start_z:.3f} f{feed_rate} S{spindle_speed:.1f}\n"

        for pass_num in range(1, num_radial_passes + 1):
            current_x = base_x + (pass_num + 1) * depth_per_pass
            gcode += f"G01 X{start_x + current_x:.3f} Y{start_y:.3f}\n"  # Assumer centre à (start_x, start_y)

            for turn in range(1, thread_number + 1):
                next_z = start_z - thread_pitch * turn  # Z absolu depuis start_z
                gcode += f"{path_type} X{start_x + current_x:.3f} Y{start_y:.3f} I{-start_x - current_x + start_x:.3f} J0.000 Z{next_z:.3f}\n"

            gcode += f"G00 X{start_x:.3f} Y{start_y:.3f}\n"  # Retour au centre
            if pass_num < num_radial_passes:
                gcode += f"G00 Z{start_z:.3f}\n\n"  # Reposition pour prochaine passe
    else:  # Vis (Externe)
        # Bloc alternatif pour filetage externe (Vis) - Copie initiale pour validation
        base_x = hole_radius- depth_per_pass + tool_radius  # À ajuster pour Vis si nécessaire
        i_value = -base_x # À ajuster pour Vis si nécessaire

        gcode = f"\n; Threading operation"
        gcode += f"\n;(Vis, {defaults.get('path_type', 'Left')})"
        gcode += f"\n; D={hole_diameter:.1f} H={thread_number*thread_pitch:.1f} P={thread_pitch:.1f}"
        gcode += f"\n; X,Y,Z = {start_x}, {start_y}, {start_z}\n\n"
        gcode += f"G00 Z{clearance_height} S{spindle_speed:.1f}\n"
        gcode += f"G00 X{start_x + hole_radius + tool_radius + total_depth:.3f} Y{start_y:.3f} Z{start_z:.3f} f{feed_rate}\n"

        for pass_num in range(1, num_radial_passes + 1):
            current_x = base_x - (pass_num) * depth_per_pass + depth_per_pass
            gcode += f"G01 X{start_x + current_x:.3f} Y{start_y:.3f}\n"  # Assumer centre à (start_x, start_y)

            for turn in range(1, thread_number + 1):
                next_z = start_z - thread_pitch * turn  # Z absolu depuis start_z
                gcode += f"{path_type} X{start_x + current_x:.3f} Y{start_y:.3f} I{-start_x - current_x + start_x:.3f} J0.000 Z{next_z:.3f}\n"

            gcode += f"G00 X{start_x + hole_radius + tool_radius + total_depth:.3f} Y{start_y:.3f}\n"  # Retour au centre
            if pass_num < num_radial_passes:
                gcode += f"G00 Z{start_z:.3f}\n\n"  # Reposition pour prochaine passe

    # Fin à Z clearance
    gcode += f"G00 Z{clearance_height:.3f}\n"

    # Pour calculate_stock_dimensions : end_x/y basé sur hole_diameter, current_z = start_z - thread_number * thread_pitch
    end_x = start_x + hole_diameter
    end_y = start_y + hole_diameter
    current_z = start_z - thread_number * thread_pitch

    return gcode, start_x, start_y, start_z, current_z, end_x, end_y, clearance_height

def matrix_drilling(config):
    defaults = config.get("matrix_drilling", {})
    start_x = defaults.get("start_x", 0.0)
    start_y = defaults.get("start_y", 0.0)
    start_z = defaults.get("start_z", 0.0)
    num_cols = int(float(defaults.get("num_cols", 1)))  # Forcer conversion en int
    step_x = float(defaults.get("step_x", 10.0))
    num_rows = int(float(defaults.get("num_rows", 1)))  # Forcer conversion en int
    step_y = float(defaults.get("step_y", 10.0))
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
    if step_x < 0 or step_y < 0:
        raise ValueError("Les pas sur X et Y doivent être positifs ou nuls.")
    #print(f"Debug: num_cols={num_cols}, num_rows={num_rows}, step_x={step_x}, step_y={step_y}")  # Ligne de débogage

    num_passes_z = int(total_depth / depth_per_pass) + (1 if total_depth % depth_per_pass != 0 else 0)
    end_x = start_x + (num_cols - 1) * step_x
    end_y = start_y + (num_rows - 1) * step_y

    gcode = f"\n; Matrix drilling operation ({num_cols}x{num_rows} holes, RAST strategy)"
    gcode += f"\n; X,Y,Z = {start_x}, {start_y}, {start_z}"
    gcode += f"\n; Matrix X x Y = {num_cols} x {num_rows}, H = {total_depth}\n\n"
    gcode += f"G0 S{spindle_speed:.1f} f{feed_rate}\n"
    gcode += f"G00 Z{clearance_height:.3f} f{feed_rate}\n"
    gcode += f"G00 X{start_x:.3f} Y{start_y:.3f}\n"

    for j in range(num_rows):
        current_y = start_y + j * step_y
        x_positions = [start_x + i * step_x for i in range(num_cols)]
        if j % 2 == 1:  # Inverse l'ordre pour les lignes impaires
            x_positions = x_positions[::-1]
        #print(f"Debug: Row {j+1}, Y={current_y}, X positions: {x_positions}")  # Ligne de débogage
        for current_x in x_positions:
            gcode += f"; Hole at X={current_x:.3f}, Y={current_y:.3f}\n"
            gcode += f"G00 X{current_x:.3f} Y{current_y:.3f}\n"
            current_z = start_z
            for k in range(num_passes_z):
                current_z -= min(depth_per_pass, total_depth - k * depth_per_pass)
                gcode += f"; Pass {k+1} at Z={current_z:.3f}\n"
                gcode += f"G01 Z{current_z:.3f}\n"
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
    path_type = {"Opposition": "Opposition", "Avalant": "Avalant"}.get(defaults.get("path_type", "Opposition"), "Opposition")
    corner_type = defaults.get("corner_type", "Avant Gauche (AVG)")  # Valeur directe depuis config.json

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

    gcode = f"\n; Corner radius operation ({corner_type}, {path_type})\n"
    gcode += f"G0 S{spindle_speed:.1f} f{feed_rate}\n"
    gcode += f"G00 Z{clearance_height:.3f} f{feed_rate}\n"
    gcode += "G91\n"  # Mode relatif pour les arcs

    # Définir les commandes d'arc et retours selon corner_type et path_type
    if corner_type == "Avant Gauche (AVG)":
        if path_type == "Opposition":
            arc_cmd = f"G03 X{arc_radius:.3f} Y-{arc_radius:.3f} I{arc_radius:.3f} J0.000"
            return_x = f"G00 X-{arc_radius:.3f}"
            return_y = f"G00 Y{arc_radius:.3f}"
        else:
            arc_cmd = f"G02 X-{arc_radius:.3f} Y{arc_radius:.3f} I0.000 J{arc_radius:.3f}"
            return_x = f"G00 X{arc_radius:.3f}"
            return_y = f"G00 Y-{arc_radius:.3f}"
    elif corner_type == "Avant Droit (AVD)":
        if path_type == "Opposition":
            arc_cmd = f"G03 X{arc_radius:.3f} Y{arc_radius:.3f} I0.000 J{arc_radius:.3f}"
            return_x = f"G00 X-{arc_radius:.3f}"
            return_y = f"G00 Y-{arc_radius:.3f}"
        else:
            arc_cmd = f"G02 X-{arc_radius:.3f} Y-{arc_radius:.3f} I-{arc_radius:.3f} J0.000"
            return_x = f"G00 X{arc_radius:.3f}"
            return_y = f"G00 Y{arc_radius:.3f}"
    elif corner_type == "Arrière Droit (ARD)":
        if path_type == "Opposition":
            arc_cmd = f"G03 X-{arc_radius:.3f} Y{arc_radius:.3f} I-{arc_radius:.3f} J0.000"
            return_x = f"G00 X{arc_radius:.3f}"
            return_y = f"G00 Y-{arc_radius:.3f}"
        else:
            arc_cmd = f"G02 X{arc_radius:.3f} Y-{arc_radius:.3f} I0.000 J-{arc_radius:.3f}"
            return_x = f"G00 X-{arc_radius:.3f}"
            return_y = f"G00 Y{arc_radius:.3f}"
    elif corner_type == "Arrière Gauche (ARG)":
        if path_type == "Opposition":
            arc_cmd = f"G03 X-{arc_radius:.3f} Y-{arc_radius:.3f} I0.000 J-{arc_radius:.3f}"
            return_x = f"G00 X{arc_radius:.3f}"
            return_y = f"G00 Y{arc_radius:.3f}"
        else:
            arc_cmd = f"G02 X{arc_radius:.3f} Y{arc_radius:.3f} I{arc_radius:.3f} J0.000"
            return_x = f"G00 X-{arc_radius:.3f}"
            return_y = f"G00 Y-{arc_radius:.3f}"

    # Exécuter les passes
    for i in range(num_passes_z):
        depth = min(depth_per_pass, total_depth - i * depth_per_pass)
        target_z = start_z - (i * depth_per_pass + depth)
        gcode += f"; Pass {i+1} at Z={target_z:.3f}\n"
        gcode += "G90\n"  # Mode absolu pour Z
        gcode += f"G01 Z{target_z:.3f}\n"
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
    path_type = {"Opposition": "Opposition", "Avalant": "Avalant"}.get(defaults.get("path_type", "Opposition"), "Opposition")
    total_depth = defaults.get("total_depth", 2.0)
    depth_per_pass = defaults.get("depth_per_pass", 0.5)
    feed_rate = defaults.get("feed_rate", 1800)
    spindle_speed = defaults.get("spindle_speed", 1000)

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

    gcode = f"\n; Oblong hole operation ({path_type})\n"
    gcode += f"G0 S{spindle_speed:.1f} f{feed_rate}\n"
    gcode += f"G90\n"
    gcode += f"G00 X{start_x:.3f} Y{start_y:.3f} Z{start_z:.3f} f{feed_rate}\n"

    for i in range(num_passes_z):
        current_depth = min((i + 1) * depth_per_pass, total_depth)
        target_z = start_z - current_depth
        gcode += f"; Pass {i+1} at Z={target_z:.3f}\n"
        gcode += f"G90\n"
        gcode += f"G00 X{start_x:.3f} Y{start_y:.3f} Z{start_z:.3f}\n"
        gcode += f"G01 Z{target_z:.3f}\n"
        gcode += "G91\n"

        gcode += f"G00 X{-half_length_x:.3f} Y{-half_length_y:.3f}\n"
        if path_type == "Opposition":
            gcode += f"G02 X{-half_width:.3f} Y{half_width:.3f} I0.000 J{half_width:.3f}\n"
            gcode += f"G01 X0.000 Y{length_y:.3f}\n"
            gcode += f"G02 X{half_width:.3f} Y{half_width:.3f} I{half_width:.3f} J0.000\n"
            gcode += f"G01 X{length_x:.3f} Y0.000\n"
            gcode += f"G02 X{half_width:.3f} Y{-half_width:.3f} I0.000 J{-half_width:.3f}\n"
            gcode += f"G01 X0.000 Y{-length_y:.3f}\n"
            gcode += f"G02 X{-half_width:.3f} Y{-half_width:.3f} I{-half_width:.3f} J0.000\n"
            gcode += f"G01 X{-length_x:.3f} Y0.000\n"
        else:
            gcode += f"G03 X{half_width:.3f} Y{-half_width:.3f} I{half_width:.3f} J0.000\n"
            gcode += f"G01 X{length_x:.3f} Y0.000\n"
            gcode += f"G03 X{half_width:.3f} Y{half_width:.3f} I0.000 J{half_width:.3f}\n"
            gcode += f"G01 X0.000 Y{length_y:.3f}\n"
            gcode += f"G03 X{-half_width:.3f} Y{half_width:.3f} I{-half_width:.3f} J0.000\n"
            gcode += f"G01 X{-length_x:.3f} Y0.000\n"
            gcode += f"G03 X{-half_width:.3f} Y{-half_width:.3f} I0.000 J{-half_width:.3f}\n"
            gcode += f"G01 X0.000 Y{-length_y:.3f}\n"

        gcode += "G90\n"

    gcode += f"G00 X{start_x:.3f} Y{start_y:.3f} Z{start_z:.3f}\n"
    gcode += "G90\n"

    stock_x = length_x
    stock_y = length_y
    stock_z = start_z + total_depth

    return gcode, start_x - half_length_x, start_y - half_length_y, start_z, start_z - total_depth, start_x + half_length_x, start_y + half_length_y, stock_z

def main():
    # Étape 1 : Récupérer les paramètres communs dans le JSON
    config = load_config()
    project_name = config.get("project_name", "test")
    machine_name = config.get("machine", "CNC_450x800")
    operation = config.get("last_operation", "1")
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
        gcode = generate_header(project_name, machine_name, stock_x, stock_y, stock_z)
        for op, _, _, _, _, _, _, _ in operations:
            gcode += op
        gcode += "G90\nM5\nM30\n"

        filename = f"NC\{operation}_{project_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.nc"
        if not os.access(os.getcwd(), os.W_OK):
            raise PermissionError("Pas de permissions d'écriture dans le répertoire courant.")
        with open(filename, "w") as file:
            file.write(gcode)
        print(f"G-code sauvegardé dans {filename}")
    except Exception as e:
        print(f"Une erreur s'est produite : {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()