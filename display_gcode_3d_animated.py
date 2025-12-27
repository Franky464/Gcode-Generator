# display_gcode_3d_animated.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.animation import FuncAnimation
import re
import os
import glob
import numpy as np
import sys
import traceback

# Journalisation
print(f"Python: {sys.executable}")
print(f"Matplotlib version: {matplotlib.__version__}")

# Vérification 3D
try:
    from mpl_toolkits.mplot3d import Axes3D
    print("Importation mpl_toolkits.mplot3d réussie")
except ImportError as e:
    messagebox.showerror("Erreur", f"mpl_toolkits.mplot3d manquant : {e}")
    sys.exit(1)


def get_latest_gcode_file(nc_dir="NC"):
    """Récupère le fichier .nc le plus récent ou celui passé en argument."""
    if len(sys.argv) > 1:
        path = sys.argv[1]
        if os.path.exists(path):
            return path
    nc_dir = os.path.join(os.path.dirname(__file__), nc_dir)
    if not os.path.isdir(nc_dir):
        return None
    files = glob.glob(os.path.join(nc_dir, "*.nc"))
    return max(files, key=os.path.getmtime) if files else None


def parse_stock_dimensions(gcode):
    """Extrait [X, Y, Z] du stock dans l'en-tête."""
    match = re.search(r'\[(\d+\.\d+), (\d+\.\d+), (\d+\.\d+)\]', gcode)
    return (float(match.group(1)), float(match.group(2)), float(match.group(3))) if match else (100.0, 100.0, 10.0)


def interpolate_arc(start_x, start_y, start_z, end_x, end_y, end_z, i, j, direction='G03', num_points=30):
    """Interpole un arc G02/G03."""
    try:
        center_x, center_y = start_x + i, start_y + j
        radius = np.sqrt(i**2 + j**2)
        if radius < 1e-6:
            return [start_x, end_x], [start_y, end_y], [start_z, end_z]

        start_angle = np.arctan2(start_y - center_y, start_x - center_x)
        end_angle = np.arctan2(end_y - center_y, end_x - center_x)
        if direction == 'G03' and end_angle <= start_angle:
            end_angle += 2 * np.pi
        elif direction == 'G02' and end_angle >= start_angle:
            end_angle -= 2 * np.pi

        angles = np.linspace(start_angle, end_angle, num_points)
        x_arc = center_x + radius * np.cos(angles)
        y_arc = center_y + radius * np.sin(angles)
        z_arc = np.linspace(start_z, end_z, num_points)
        return x_arc.tolist(), y_arc.tolist(), z_arc.tolist()
    except:
        return [start_x, end_x], [start_y, end_y], [start_z, end_z]


def prepare_gcode_segments(gcode):
    """Parse le G-code et retourne liste de segments + couleurs."""
    segments = []
    colors = []
    current_x = current_y = current_z = 0.0
    mode = 'absolute'

    for line in gcode.split('\n'):
        line = line.strip()
        if not line or line.startswith(';') or line.startswith('('):
            continue

        coord_dict = dict(re.findall(r'([XYZEIJ])([-+]?\d*\.?\d+)', line))
        for k in coord_dict:
            coord_dict[k] = float(coord_dict[k])

        new_x = coord_dict.get('X', current_x) if mode == 'absolute' else current_x + coord_dict.get('X', 0)
        new_y = coord_dict.get('Y', current_y) if mode == 'absolute' else current_y + coord_dict.get('Y', 0)
        new_z = coord_dict.get('Z', current_z) if mode == 'absolute' else current_z + coord_dict.get('Z', 0)

        g_match = re.search(r'G(\d+)', line)
        if not g_match:
            continue
        g_code = f'G{g_match.group(1).zfill(2)}'

        if g_code == 'G90':
            mode = 'absolute'
            continue
        if g_code == 'G91':
            mode = 'relative'
            continue

        if g_code in ('G00', 'G01'):
            color = 'y' if g_code == 'G00' else 'r'
            segments.append(([current_x, new_x], [current_y, new_y], [current_z, new_z]))
            colors.append(color)
            current_x, current_y, current_z = new_x, new_y, new_z

        elif g_code in ('G02', 'G03'):
            i = coord_dict.get('I', 0.0)
            j = coord_dict.get('J', 0.0)
            x_arc, y_arc, z_arc = interpolate_arc(current_x, current_y, current_z, new_x, new_y, new_z, i, j, g_code)
            for k in range(1, len(x_arc)):
                segments.append(([x_arc[k-1], x_arc[k]], [y_arc[k-1], y_arc[k]], [z_arc[k-1], z_arc[k]]))
                colors.append('b')
            current_x, current_y, current_z = new_x, new_y, new_z

    return segments, colors


def animate_gcode_3d(gcode, canvas_widget, stock_x, stock_y, stock_z):
    global anim_running
    anim_running = False

    segments, colors = prepare_gcode_segments(gcode)
    if not segments:
        messagebox.showwarning("Avertissement", "Aucun mouvement détecté.")
        return None

    # === CALCUL DES LIMITES RÉELLES ===
    all_x = [coord for seg in segments for coord in seg[0]]
    all_y = [coord for seg in segments for coord in seg[1]]
    all_z = [coord for seg in segments for coord in seg[2]]

    x_min, x_max = min(all_x), max(all_x)
    y_min, y_max = min(all_y), max(all_y)
    z_min, z_max = min(all_z), max(all_z)

    # Éviter division par zéro
    x_span = max(x_max - x_min, 1)
    y_span = max(y_max - y_min, 1)
    max_span = max(x_span, y_span)

    # Marges
    margin = 0.1
    x_margin = x_span * margin
    y_margin = y_span * margin
    z_margin = max(stock_z * 0.1, 1.0)

    # === FIG & AX ===
    fig = plt.figure(figsize=(10, 7))
    ax = fig.add_subplot(111, projection='3d')

    # === RÉFÉRENCES VERTES (ancrées au min, longueur = max_span) ===
    ax.plot([x_min, x_min + max_span], [y_min, y_min], [0, 0], 'g-', linewidth=2, label=f'Réf {max_span:.1f} mm')
    ax.plot([x_min, x_min], [y_min, y_min + max_span], [0, 0], 'g-', linewidth=2)

    # === LIMITES FINALES ===
    ax.set_xlim(x_min - x_margin, x_min + max_span + x_margin)
    ax.set_ylim(y_min - y_margin, y_min + max_span + y_margin)
    ax.set_zlim(z_min - z_margin, z_max + z_margin)

    # === ASPECT RATIO ===
    try:
        ax.set_box_aspect([max_span, max_span, (z_max - z_min + 2*z_margin) * 0.5])
    except:
        ax.dist = 10

    ax.set_xlabel('X (mm)'); ax.set_ylabel('Y (mm)'); ax.set_zlabel('Z (mm)')
    ax.set_title('Animation 3D du G-code')
    ax.legend()

    lines = []

    def init():
        return lines

    def update(frame):
        nonlocal lines
        for line in lines:
            line.remove()
        lines = []
        for i in range(frame):
            xs, ys, zs = segments[i]
            line, = ax.plot(xs, ys, zs, colors[i] + '-', linewidth=1.5)
            lines.append(line)
        return lines

    # Animation
    anim = FuncAnimation(
        fig, update, frames=len(segments),
        init_func=init, interval=100, blit=False, repeat=False
    )

    # Intégrer dans Tkinter
    for widget in canvas_widget.winfo_children():
        widget.destroy()

    canvas = FigureCanvasTkAgg(fig, master=canvas_widget)
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    toolbar = NavigationToolbar2Tk(canvas, canvas_widget)
    toolbar.update()
    toolbar.pack(side=tk.TOP, fill=tk.X)

    canvas.draw()

    # Stocker
    canvas_widget.anim = anim
    canvas_widget.figure = fig
    canvas_widget.ax = ax
    canvas_widget.segments = segments
    canvas_widget.colors = colors

    anim_running = True
    return canvas


# === Interface Tkinter ===
def open_gcode_file():
    path = filedialog.askopenfilename(
        initialdir=os.path.join(os.path.dirname(__file__), "NC"),
        title="Ouvrir G-code",
        filetypes=[("G-code", "*.nc"), ("Tous", "*.*")]
    )
    if path:
        load_and_animate(path)

def load_and_animate(file_path):
    global current_file
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            gcode = f.read()
        current_file = file_path
        stock_x, stock_y, stock_z = parse_stock_dimensions(gcode)
        file_label.configure(text=f"Fichier: {os.path.basename(file_path)}")
        animate_gcode_3d(gcode, canvas_frame, stock_x, stock_y, stock_z)
    except Exception as e:
        messagebox.showerror("Erreur", f"Échec chargement :\n{e}")

def update_visualization():
    file_path = get_latest_gcode_file()
    if file_path and os.path.exists(file_path):
        load_and_animate(file_path)
    else:
        messagebox.showerror("Erreur", "Aucun fichier .nc dans le dossier NC.")

def save_image():
    if not hasattr(canvas_frame, 'figure'):
        messagebox.showwarning("Avertissement", "Aucune visualisation à sauvegarder.")
        return
    path = filedialog.asksaveasfilename(
        defaultextension=".png",
        filetypes=[("PNG", "*.png")],
        title="Sauvegarder image"
    )
    if path:
        canvas_frame.figure.savefig(path, dpi=150, bbox_inches='tight')
        messagebox.showinfo("Succès", f"Image sauvegardée :\n{path}")

def toggle_animation():
    global anim_running
    if not hasattr(canvas_frame, 'anim'):
        return
    if anim_running:
        canvas_frame.anim.event_source.stop()
        toggle_btn.configure(text="▶ Reprendre")
        anim_running = False
    else:
        canvas_frame.anim.event_source.start()
        toggle_btn.configure(text="⏸ Pause")
        anim_running = True

def reset_view():
    if hasattr(canvas_frame, 'ax'):
        canvas_frame.ax.view_init(elev=30, azim=45)
        canvas_frame.figure.canvas.draw()

def show_help():
    msg = (
        "Animation 3D du G-code\n\n"
        "• Jaune : G00 (rapide)\n"
        "• Rouge : G01 (linéaire)\n"
        "• Bleu : G02/G03 (arcs)\n"
        "• Vert : Références X/Y\n\n"
        "Interaction :\n"
        "• Rotation : Clic gauche + glisser\n"
        "• Zoom : Molette ou clic droit\n"
        "• Pan : Clic milieu\n"
        "• Boutons : Tourner X/Y, Pause, etc."
    )
    messagebox.showinfo("Aide", msg)

def about():
    messagebox.showinfo("À propos", "Visualisation 3D Animée du G-code\nVersion 2.0\nDéveloppé pour Gcode-Generator")

def on_closing():
    plt.close('all')
    root.destroy()


# === Lancement ===
try:
    root = tk.Tk()
    root.title("Visualisation 3D Animée du G-code")
    root.geometry("750x780+900+50")
    root.minsize(600, 500)

    # Menu
    menubar = tk.Menu(root)
    root.config(menu=menubar)

    file_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Fichier", menu=file_menu)
    file_menu.add_command(label="Ouvrir...", command=open_gcode_file)
    file_menu.add_command(label="Recharger dernier", command=update_visualization)
    file_menu.add_command(label="Sauvegarder image...", command=save_image)
    file_menu.add_separator()
    file_menu.add_command(label="Quitter", command=on_closing)

    view_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Affichage", menu=view_menu)
    view_menu.add_command(label="Réinitialiser vue", command=reset_view)

    help_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Aide", menu=help_menu)
    help_menu.add_command(label="Instructions", command=show_help)
    help_menu.add_command(label="À propos", command=about)

    # Style
    style = ttk.Style()
    style.configure("TFrame", padding=5)
    style.configure("TButton", padding=6)

    # Canvas
    canvas_frame = ttk.Frame(root)
    canvas_frame.grid(row=0, column=0, columnspan=5, padx=5, pady=5, sticky="nsew")

    # Contrôles
    ctrl_frame = ttk.Frame(root)
    ctrl_frame.grid(row=1, column=0, columnspan=5, pady=5, sticky="ew")

    ttk.Button(ctrl_frame, text="Tourner X+", command=lambda: [setattr(canvas_frame.ax, 'azim', canvas_frame.ax.azim + 15), canvas_frame.figure.canvas.draw()]).grid(row=0, column=0, padx=3)
    ttk.Button(ctrl_frame, text="Tourner X-", command=lambda: [setattr(canvas_frame.ax, 'azim', canvas_frame.ax.azim - 15), canvas_frame.figure.canvas.draw()]).grid(row=0, column=1, padx=3)
    ttk.Button(ctrl_frame, text="Tourner Y+", command=lambda: [setattr(canvas_frame.ax, 'elev', canvas_frame.ax.elev + 15), canvas_frame.figure.canvas.draw()]).grid(row=0, column=2, padx=3)
    ttk.Button(ctrl_frame, text="Tourner Y-", command=lambda: [setattr(canvas_frame.ax, 'elev', canvas_frame.ax.elev - 15), canvas_frame.figure.canvas.draw()]).grid(row=0, column=3, padx=3)

    toggle_btn = ttk.Button(ctrl_frame, text="⏸ Pause", command=toggle_animation)
    toggle_btn.grid(row=0, column=4, padx=10)

    # Étiquette fichier
    file_label = ttk.Label(root, text="Aucun fichier chargé", foreground="gray")
    file_label.grid(row=2, column=0, columnspan=5, pady=5)

    # Bouton recharger
    ttk.Button(root, text="Recharger dernier G-code", command=update_visualization).grid(row=3, column=0, columnspan=5, pady=8)

    # Grille
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(0, weight=1)

    root.protocol("WM_DELETE_WINDOW", on_closing)

    # Démarrage
    update_visualization()
    root.mainloop()

except Exception as e:
    messagebox.showerror("Erreur fatale", f"{e}\n{traceback.format_exc()}")
    sys.exit(1)