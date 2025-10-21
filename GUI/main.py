import json
import os
from datetime import datetime

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)
    return {}

def contour_drilling(defaults):
    start_x = defaults.get("start_x", 0.0)
    start_y = defaults.get("start_y", 0.0)
    start_z = defaults.get("start_z", 0.0)
    clearance_height = defaults.get("clearance_height", 5.0)
    tool_diameter = defaults.get("tool_diameter", 10.0)
    hole_diameter = defaults.get("hole_diameter", 30.0)
    total_depth = defaults.get("total_depth", 2.0)
    depth_per_pass = defaults.get("depth_per_pass", 1.0)
    feed_rate = defaults.get("feed_rate", 1800.0)
    spindle_speed = defaults.get("spindle_speed", 24000.0)
    path_type = defaults.get("path_type", "Opposition")
    drilling_type = defaults.get("drilling_type", "Contour" if not defaults.get("is_blind_hole", False) else "Blind")
    overlap_percent = defaults.get("overlap_percent", 50.0)

    if drilling_type not in ["Blind", "Contour", "Outer"]:
        raise ValueError("Type de perçage invalide : doit être 'Blind', 'Contour' ou 'Outer'.")

    tool_radius = tool_diameter / 2
    hole_radius = hole_diameter / 2
    if drilling_type == "Outer":
        circle_radius = hole_radius + tool_radius
        stock_x = stock_y = hole_diameter + tool_diameter
    else:
        circle_radius = hole_radius - tool_radius
        stock_x = stock_y = hole_diameter
    stock_z = total_depth + clearance_height

    gcode = []
    gcode.append("(Contour Drilling)")
    gcode.append(f"(Stock: [{stock_x:.3f}, {stock_y:.3f}, {stock_z:.3f}])")
    gcode.append(f"(Tool: Diameter={tool_diameter:.3f})")
    gcode.append("G90 G54 G17")
    gcode.append(f"G21 (Metric)")
    gcode.append(f"G0 Z{clearance_height:.3f}")
    gcode.append(f"G0 X{start_x:.3f} Y{start_y:.3f}")
    gcode.append(f"S{spindle_speed:.0f} M3")

    current_z = start_z
    num_passes = int(total_depth / depth_per_pass) + (1 if total_depth % depth_per_pass else 0)
    for i in range(num_passes):
        current_z -= depth_per_pass
        if current_z < -total_depth:
            current_z = -total_depth
        gcode.append(f"G1 Z{current_z:.3f} F{feed_rate / 2:.1f}")

        if drilling_type == "Blind":
            current_radius = circle_radius * (1 - overlap_percent / 100 * (i / (num_passes - 1)))
            gcode.append(f"G1 X{start_x + current_radius:.3f} F{feed_rate:.1f}")
            gcode.append(f"G2 X{start_x + current_radius:.3f} Y{start_y:.3f} I{-current_radius:.3f} J0.000 F{feed_rate:.1f}")
        else:
            gcode.append(f"G1 X{start_x + circle_radius:.3f} F{feed_rate:.1f}")
            gcode.append(f"G2 X{start_x + circle_radius:.3f} Y{start_y:.3f} I{-circle_radius:.3f} J0.000 F{feed_rate:.1f}" if path_type == "Opposition" else
                         f"G3 X{start_x + circle_radius:.3f} Y{start_y:.3f} I{-circle_radius:.3f} J0.000 F{feed_rate:.1f}")

    gcode.append(f"G0 Z{clearance_height:.3f}")
    gcode.append("M5")
    gcode.append("M30")
    return gcode, start_x, start_y, start_z, current_z, start_x, start_y, clearance_height

def main():
    config = load_config()
    mode = config.get("last_operation", "1")
    project_name = config.get("project_name", "test")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(os.path.dirname(__file__), "NC")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{mode}_{project_name}_{timestamp}.nc")

    if mode == "2":
        gcode, _, _, _, _, _, _, _ = contour_drilling(config.get("contour_drilling", {}))
    else:
        gcode = ["(Mode non supporté dans cet exemple)"]

    with open(output_file, "w") as f:
        for line in gcode:
            f.write(line + "\n")
    print(f"G-code généré : {output_file}")

if __name__ == "__main__":
    main()