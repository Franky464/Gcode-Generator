# display_gcode_3d.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import matplotlib
matplotlib.use('TkAgg')  # Forcer l'utilisation du backend TkAgg
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import re
import os
import glob
import numpy as np
from datetime import datetime
import sys
import traceback

# Journaliser l'environnement au démarrage
print(f"Débogage: sys.executable : {sys.executable}")
print(f"Débogage: PYTHONPATH : {os.environ.get('PYTHONPATH', 'Non défini')}")
print(f"Débogage: Version matplotlib : {matplotlib.__version__}")

# Vérification de l'importation de mpl_toolkits.mplot3d
try:
    from mpl_toolkits.mplot3d import Axes3D
    print("Débogage: Importation de mpl_toolkits.mplot3d réussie")
except ImportError as e:
    print(f"Débogage: Échec de l'importation de Axes3D : {str(e)}")
    messagebox.showerror("Erreur", f"Échec de l'importation de la bibliothèque 3D : {str(e)}\nVeuillez réinstaller matplotlib.")
    sys.exit(1)

def get_latest_gcode_file(nc_dir="NC"):
    """Récupère le fichier G-code spécifié en argument ou le plus récent dans le dossier NC."""
    print("Débogage: Début de get_latest_gcode_file")
    try:
        if len(sys.argv) > 1:
            gcode_file = sys.argv[1]
            if os.path.exists(gcode_file):
                print(f"Débogage: Utilisation du fichier G-code spécifié : {gcode_file}")
                return gcode_file
            else:
                print(f"Débogage: Fichier spécifié '{gcode_file}' non trouvé")
                return None
        nc_dir = os.path.join(os.path.dirname(__file__), nc_dir)
        if not os.path.exists(nc_dir):
            print(f"Débogage: Dossier NC '{nc_dir}' non trouvé")
            return None
        gcode_files = glob.glob(os.path.join(nc_dir, "*.nc"))
        if not gcode_files:
            print(f"Débogage: Aucun fichier .nc trouvé dans {nc_dir}")
            return None
        latest_file = max(gcode_files, key=os.path.getmtime)
        print(f"Débogage: Fichier G-code le plus récent : {latest_file}")
        return latest_file
    except Exception as e:
        print(f"Débogage: Erreur dans get_latest_gcode_file : {str(e)}")
        return None

def parse_stock_dimensions(gcode):
    """Extrait les dimensions du stock depuis l'en-tête du G-code."""
    print("Débogage: Début de parse_stock_dimensions")
    try:
        stock_pattern = re.compile(r'\[(\d+\.\d+), (\d+\.\d+), (\d+\.\d+)\]')
        for line in gcode.split('\n'):
            match = stock_pattern.search(line)
            if match:
                dimensions = float(match.group(1)), float(match.group(2)), float(match.group(3))
                print(f"Débogage: Dimensions extraites : {dimensions}")
                return dimensions
        print("Débogage: Dimensions par défaut utilisées")
        return 100.0, 100.0, 10.0
    except Exception as e:
        print(f"Débogage: Erreur dans parse_stock_dimensions : {str(e)}")
        return 100.0, 100.0, 10.0

def interpolate_arc(start_x, start_y, start_z, end_x, end_y, end_z, i, j, direction='G03', num_points=50):
    """Interpole un arc (G02/G03) entre les points de départ et d'arrivée."""
    print(f"Débogage: Interpolation d'arc de ({start_x}, {start_y}, {start_z}) à ({end_x}, {end_y}, {end_z})")
    try:
        center_x = start_x + i
        center_y = start_y + j
        radius = np.sqrt(i**2 + j**2)
        if radius < 0.0001:
            print(f"Débogage: Rayon nul ou trop petit pour I={i}, J={j}")
            return [start_x, end_x], [start_y, end_y], [start_z, end_z]
        start_angle = np.arctan2(start_y - center_y, start_x - center_x)
        end_angle = np.arctan2(end_y - center_y, end_x - center_x)
        if direction == 'G03':
            if end_angle <= start_angle:
                end_angle += 2 * np.pi
        else:
            if end_angle >= start_angle:
                end_angle -= 2 * np.pi
        angles = np.linspace(start_angle, end_angle, num_points)
        x_arc = [center_x + radius * np.cos(angle) for angle in angles]
        y_arc = [center_y + radius * np.sin(angle) for angle in angles]
        z_arc = np.linspace(start_z, end_z, num_points)
        print("Débogage: Arc interpolé avec succès")
        return x_arc, y_arc, z_arc
    except Exception as e:
        print(f"Débogage: Erreur dans interpolate_arc : {str(e)}")
        return [start_x, end_x], [start_y, end_y], [start_z, end_z]

def plot_gcode_3d(gcode, canvas_widget, stock_x, stock_y, stock_z):
    """Trace le G-code en 3D dans une fenêtre Tkinter."""
    print("Débogage: Début de plot_gcode_3d")
    try:
        fig = plt.figure(figsize=(8, 6))
        try:
            ax = fig.add_subplot(111, projection='3d')
            print("Débogage: Axe 3D créé avec succès")
        except Exception as e:
            print(f"Débogage: Échec de la création de l'axe 3D : {str(e)}")
            raise

        x, y, z = [], [], []
        colors = []
        current_x, current_y, current_z = 0.0, 0.0, 0.0
        x.append(current_x)
        y.append(current_y)
        z.append(current_z)
        colors.append('b')

        # Parsing du G-code
        for line in gcode.split('\n'):
            line = line.strip()
            if not line or line.startswith(';') or line.startswith('('):
                continue
            print(f"Débogage: Traitement de la ligne : {line}")

            try:
                g_match = re.search(r'G(\d+)', line)
                x_match = re.search(r'X([-]?\d+\.\d+)', line)
                y_match = re.search(r'Y([-]?\d+\.\d+)', line)
                z_match = re.search(r'Z([-]?\d+\.\d+)', line)
                i_match = re.search(r'I([-]?\d+\.\d+)', line)
                j_match = re.search(r'J([-]?\d+\.\d+)', line)

                new_x = float(x_match.group(1)) if x_match else current_x
                new_y = float(y_match.group(1)) if y_match else current_y
                new_z = float(z_match.group(1)) if z_match else current_z

                if g_match:
                    g_code = g_match.group(0)
                    if g_code in ('G00', 'G01'):
                        x.append(new_x)
                        y.append(new_y)
                        z.append(new_z)
                        colors.append('b' if g_code == 'G01' else 'r')
                        current_x, current_y, current_z = new_x, new_y, new_z
                    elif g_code in ('G02', 'G03'):
                        i = float(i_match.group(1)) if i_match else 0.0
                        j = float(j_match.group(1)) if j_match else 0.0
                        x_arc, y_arc, z_arc = interpolate_arc(
                            current_x, current_y, current_z,
                            new_x, new_y, new_z,
                            i, j, direction=g_code, num_points=50
                        )
                        x.extend(x_arc[1:])
                        y.extend(y_arc[1:])
                        z.extend(z_arc[1:])
                        colors.extend(['b'] * (len(x_arc) - 1))
                        current_x, current_y, current_z = new_x, new_y, new_z
                    else:
                        print(f"Débogage: Commande G-code ignorée : {g_code}")
            except Exception as e:
                print(f"Débogage: Erreur lors du traitement de la ligne '{line}' : {str(e)}")
                continue  # Ignorer les lignes problématiques

        if len(x) > 1:
            x_min, x_max = min(x, default=0), max(x, default=stock_x)
            y_min, y_max = min(y, default=0), max(y, default=stock_y)
            z_min, z_max = min(z, default=0), max(z, default=stock_z)
            x_margin, y_margin, z_margin = stock_x * 0.1, stock_y * 0.1, stock_z * 0.1
            ax.set_xlim(x_min - x_margin, x_max + x_margin)
            ax.set_ylim(y_min - y_margin, y_max + y_margin)
            ax.set_zlim(z_min - z_margin, z_max + z_margin)

            for i in range(len(x) - 1):
                color = colors[i]
                if not (np.isnan(x[i]) or np.isnan(x[i+1]) or np.isnan(y[i]) or np.isnan(y[i+1]) or np.isnan(z[i]) or np.isnan(z[i+1])):
                    ax.plot([x[i], x[i+1]], [y[i], y[i+1]], [z[i], z[i+1]], color + '-', linewidth=1)
                else:
                    print(f"Débogage: Segment ignoré à l'index {i} en raison de valeurs non valides")
        else:
            print("Débogage: Pas de données valides pour le tracé 3D")
            messagebox.showwarning("Avertissement", "Aucune donnée valide pour l'affichage 3D.")
            return None

        ax.set_xlabel('X (mm)')
        ax.set_ylabel('Y (mm)')
        ax.set_zlabel('Z (mm)')
        ax.set_title('Visualisation 3D du G-code')

        # Stocker la figure et l'axe pour réutilisation
        canvas_widget.figure = fig
        canvas_widget.ax = ax

        # Nettoyer les widgets existants
        for widget in canvas_widget.winfo_children():
            widget.destroy()

        canvas = FigureCanvasTkAgg(fig, master=canvas_widget)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        try:
            toolbar = NavigationToolbar2Tk(canvas, canvas_widget)  # Supprimer pack_toolbar
            toolbar.update()
            toolbar.pack(side=tk.TOP, fill=tk.X)
            canvas.draw()
        except Exception as e:
            print(f"Débogage: Erreur lors de l'initialisation de la barre d'outils : {str(e)}")
            print(f"Débogage: Traceback : {traceback.format_exc()}")
            # Continuer sans la barre d'outils si elle échoue
            canvas.draw()

        print("Débogage: Visualisation 3D affichée avec succès")
        return canvas

    except Exception as e:
        print(f"Débogage: Erreur dans plot_gcode_3d : {str(e)}")
        print(f"Débogage: Traceback : {traceback.format_exc()}")
        messagebox.showerror("Erreur", f"Échec du chargement du G-code : {str(e)}")
        return None

def open_gcode_file():
    """Ouvre un fichier G-code via un dialogue de fichier."""
    print("Débogage: Ouverture d'un fichier G-code")
    file_path = filedialog.askopenfilename(
        initialdir=os.path.join(os.path.dirname(__file__), "NC"),
        title="Sélectionner un fichier G-code",
        filetypes=[("Fichiers G-code", "*.nc"), ("Tous les fichiers", "*.*")]
    )
    if file_path:
        try:
            with open(file_path, 'r') as f:
                gcode = f.read()
            print(f"Débogage: Fichier G-code chargé : {file_path}")
            file_label.configure(text=f"Fichier chargé : {os.path.basename(file_path)}")
            stock_x, stock_y, stock_z = parse_stock_dimensions(gcode)
            print(f"Débogage: Dimensions du stock : {stock_x}, {stock_y}, {stock_z}")
            plot_gcode_3d(gcode, canvas_frame, stock_x, stock_y, stock_z)
        except Exception as e:
            print(f"Débogage: Erreur dans open_gcode_file : {str(e)}")
            print(f"Débogage: Traceback : {traceback.format_exc()}")
            messagebox.showerror("Erreur", f"Échec du chargement du G-code : {str(e)}")
            file_label.configure(text="Erreur lors du chargement")

def save_image():
    """Sauvegarde la visualisation 3D comme PNG."""
    print("Débogage: Sauvegarde de l'image")
    file_path = filedialog.asksaveasfilename(
        initialdir=os.path.join(os.path.dirname(__file__), "NC"),
        title="Sauvegarder l'image",
        defaultextension=".png",
        filetypes=[("Images PNG", "*.png"), ("Tous les fichiers", "*.*")]
    )
    if file_path:
        try:
            canvas_frame.figure.savefig(file_path)
            print(f"Débogage: Image sauvegardée dans {file_path}")
            messagebox.showinfo("Succès", f"Image sauvegardée dans\n{file_path}")
        except Exception as e:
            print(f"Débogage: Erreur dans save_image : {str(e)}")
            print(f"Débogage: Traceback : {traceback.format_exc()}")
            messagebox.showerror("Erreur", f"Échec de la sauvegarde de l'image : {str(e)}")

def rotate_view(axis, angle):
    """Tourne la vue 3D autour de l'axe spécifié (X ou Y) de l'angle donné."""
    print(f"Débogage: Rotation autour de l'axe {axis} de {angle} degrés")
    try:
        ax = canvas_frame.ax
        elev, azim = ax.elev, ax.azim
        if axis == 'X':
            ax.view_init(elev=elev + angle, azim=azim)
        elif axis == 'Y':
            ax.view_init(elev=elev, azim=azim + angle)
        canvas_frame.figure.canvas.draw()
        print("Débogage: Vue tournée")
    except Exception as e:
        print(f"Débogage: Erreur dans rotate_view : {str(e)}")
        print(f"Débogage: Traceback : {traceback.format_exc()}")
        messagebox.showerror("Erreur", f"Échec de la rotation : {str(e)}")

def reset_view():
    """Réinitialise la vue 3D."""
    print("Débogage: Réinitialisation de la vue")
    try:
        ax = canvas_frame.ax
        ax.view_init(elev=30, azim=45)
        canvas_frame.figure.canvas.draw()
        print("Débogage: Vue réinitialisée")
    except Exception as e:
        print(f"Débogage: Erreur dans reset_view : {str(e)}")
        print(f"Débogage: Traceback : {traceback.format_exc()}")
        messagebox.showerror("Erreur", f"Échec de la réinitialisation de la vue : {str(e)}")

def show_help():
    """Affiche les instructions pour interagir avec le modèle 3D."""
    print("Débogage: Affichage de l'aide")
    help_text = (
        "Instructions pour interagir avec la visualisation 3D :\n"
        "- Rotation : Clic gauche + glisser dans la zone de visualisation\n"
        "- Zoom : Clic droit + glisser ou molette de la souris\n"
        "- Pan : Clic central + glisser\n"
        "- Boutons de rotation : Utilisez 'Tourner X+', 'Tourner X-', 'Tourner Y+', 'Tourner Y-' pour tourner manuellement\n"
        "- Réinitialiser la vue : Menu Affichage > Réinitialiser la vue\n"
        "- Barre d'outils : Utilisez les icônes en haut pour zoom, pan, rotation, etc."
    )
    messagebox.showinfo("Aide", help_text)

def about():
    """Affiche les informations sur l'application."""
    print("Débogage: Affichage de la boîte À propos")
    messagebox.showinfo("À propos", "Visualisation 3D du G-code\nVersion 1.0\nDéveloppé pour Gcode-Generator")

def update_visualization():
    """Met à jour la visualisation 3D avec le dernier fichier G-code."""
    print("Débogage: Début de update_visualization")
    gcode_file = get_latest_gcode_file()
    if not gcode_file:
        print("Débogage: Aucun fichier G-code trouvé")
        messagebox.showerror("Erreur", "Aucun fichier G-code trouvé dans le dossier NC.")
        file_label.configure(text="Aucun fichier chargé")
        return

    try:
        with open(gcode_file, 'r') as f:
            gcode = f.read()
        print(f"Débogage: Fichier G-code chargé : {gcode_file}")
        file_label.configure(text=f"Fichier chargé : {os.path.basename(gcode_file)}")
        stock_x, stock_y, stock_z = parse_stock_dimensions(gcode)
        print(f"Débogage: Dimensions du stock : {stock_x}, {stock_y}, {stock_z}")
        canvas = plot_gcode_3d(gcode, canvas_frame, stock_x, stock_y, stock_z)
        if canvas is None:
            print("Débogage: Échec du tracé 3D, canvas est None")
            file_label.configure(text="Erreur lors du chargement")
    except Exception as e:
        print(f"Débogage: Erreur dans update_visualization : {str(e)}")
        print(f"Débogage: Traceback : {traceback.format_exc()}")
        messagebox.showerror("Erreur", f"Échec du chargement du G-code : {str(e)}")
        file_label.configure(text="Erreur lors du chargement")

def on_closing():
    """Gère la fermeture de la fenêtre."""
    print("Débogage: Tentative de fermeture de display_gcode_3d.py")
    if messagebox.askokcancel("Quitter", "Voulez-vous quitter la visualisation 3D ?"):
        print("Débogage: Fermeture confirmée")
        try:
            plt.close('all')  # Fermer toutes les figures Matplotlib
            root.destroy()
            print("Débogage: root.destroy() exécuté")
        except Exception as e:
            print(f"Débogage: Erreur lors de root.destroy() : {str(e)}")
            print(f"Débogage: Traceback : {traceback.format_exc()}")

try:
    root = tk.Tk()
    root.title("Visualisation 3D du G-code")
    root.geometry("1000x700")  # Taille augmentée pour afficher menus et barre d'outils

    # Créer la barre de menus
    menubar = tk.Menu(root)
    root.config(menu=menubar)

    # Menu Fichier
    file_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Fichier", menu=file_menu)
    file_menu.add_command(label="Ouvrir...", command=open_gcode_file)
    file_menu.add_command(label="Recharger", command=update_visualization)
    file_menu.add_command(label="Sauvegarder image...", command=save_image)
    file_menu.add_separator()
    file_menu.add_command(label="Quitter", command=on_closing)

    # Menu Affichage
    view_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Affichage", menu=view_menu)
    view_menu.add_command(label="Réinitialiser la vue", command=reset_view)

    # Menu Aide
    help_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Aide", menu=help_menu)
    help_menu.add_command(label="Instructions", command=show_help)
    help_menu.add_command(label="À propos", command=about)

    style = ttk.Style()
    style.configure("TFrame", borderwidth=2, relief="groove")
    style.configure("TLabel", borderwidth=1, relief="flat")
    style.configure("TButton", padding=5)

    canvas_frame = ttk.Frame(root, style="TFrame")
    canvas_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

    # Frame pour les boutons de rotation
    control_frame = ttk.Frame(root, style="TFrame")
    control_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

    # Boutons de rotation
    ttk.Button(control_frame, text="Tourner X+", command=lambda: rotate_view('X', 15)).grid(row=0, column=0, padx=5)
    ttk.Button(control_frame, text="Tourner X-", command=lambda: rotate_view('X', -15)).grid(row=0, column=1, padx=5)
    ttk.Button(control_frame, text="Tourner Y+", command=lambda: rotate_view('Y', 15)).grid(row=0, column=2, padx=5)
    ttk.Button(control_frame, text="Tourner Y-", command=lambda: rotate_view('Y', -15)).grid(row=0, column=3, padx=5)

    file_label = ttk.Label(root, text="Aucun fichier chargé", style="TLabel")
    file_label.grid(row=2, column=0, padx=5, pady=5)

    reload_button = ttk.Button(root, text="Recharger le dernier G-code", command=update_visualization)
    reload_button.grid(row=3, column=0, padx=5, pady=10)

    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(0, weight=1)

    # Ajouter le gestionnaire de fermeture
    root.protocol("WM_DELETE_WINDOW", on_closing)

    update_visualization()
    root.mainloop()

except Exception as e:
    print(f"Débogage: Erreur lors de l'initialisation de la fenêtre : {str(e)}")
    print(f"Débogage: Traceback : {traceback.format_exc()}")
    messagebox.showerror("Erreur", f"Échec de l'initialisation : {str(e)}")
    sys.exit(1)