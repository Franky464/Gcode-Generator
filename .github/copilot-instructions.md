<!-- Instructions Copilot pour le dépôt Gcode-Generator -->
# Gcode-Generator — Guide pour assistant IA (version française)

Ce document décrit rapidement l'organisation du dépôt et les règles à suivre pour des modifications sûres et utiles.

- Projet : Générateur de G-code CNC en Python avec interface Tkinter.
- UI principale : `GUI.py` (widgets Tkinter, gestion des images et de la localisation).
- Logique métier : `main_tkinter.py` (fonctions de génération de G-code : surfacing, contour_drilling, matrix_drilling, threading, corner_radius, etc.).
- Configuration & i18n : `config.json` stocke les valeurs par défaut ; `translations.json` contient les chaînes traduites.

Architecture et objectif
- L'application expose six modes (dégrossissage, perçage de contour, perçage en matrice, rayon de coin, trou oblong, filetage). La sélection de mode dans l'UI crée un formulaire dont les valeurs sont passées aux fonctions de `main_tkinter.py` pour produire le G-code.
- UI et logique sont volontairement découplés : `GUI.py` construit les formulaires à partir de `mode_params` et lit/écrit `config.json`; `main_tkinter.py` produit des blocs G-code et renvoie aussi des coordonnées utiles au calcul des dimensions de stock.

Conventions importantes du projet
- `config.json` utilise des sections au niveau racine dont les clés correspondent aux noms de modes (ex. `"surfacing"`, `"threading"`).
- Certaines valeurs (notamment `path_type`) peuvent être soit un code numérique soit un label texte (ex. `"1"` ou `"Opposition"). Ne cassez pas cette prise en charge bidirectionnelle quand vous modifiez la logique.
- Contrat des fonctions de génération : elles retournent toujours
	(gcode_string, start_x, start_y, start_z, current_z, end_x, end_y, clearance_height).
	Respectez ce format lors d'un refactor ou d'un appel depuis l'UI.
- Les images de l'UI sont construites par `generate_image_filename` (dans `GUI.py`) ; respectez le même schéma de nommage dans le dossier `images/` si vous ajoutez des variantes.

Flux de travail développeur (pratiques à suivre)
- Exécution locale : utiliser Python 3.x et installer Pillow (module PIL). L'UI se lance avec `python GUI.py`. On peut aussi importer et appeler directement des fonctions dans `main_tkinter.py` pour des tests unitaires manuels.
- Si vous renommez un paramètre utilisé par une fonction de `main_tkinter.py`, mettez à jour `mode_params` dans `GUI.py` et les valeurs par défaut dans `config.json` pour garder la synchronisation.
- Pour ajouter une traduction : ajoutez la clé dans `translations.json` sous `translations["<lang>"]` et utilisez la clé dans `GUI.py` (sections `fields`, `path_types`, `corner_types`, etc.).

Sécurité et modifications minimales
- Favorisez les modifications locales et limitées. Évitez les renommages globaux sans mettre à jour `config.json`, `GUI.py` et toute lecture de la clé.
- Conservez la forme des chaînes G-code renvoyées (sauts de ligne, entêtes) sauf si vous modifiez volontairement `generate_header`.

Exemples concrets
- Ajouter un champ `coolant_on` pour le surfacing :
	1) ajouter la clé par défaut dans `config.json` sous `surfacing`,
	2) ajouter l'entrée correspondante dans `mode_params["1"]` dans `GUI.py`,
	3) lire `config.get("surfacing", {})` dans `main_tkinter.surfacing`.
- Pour modifier la sélection d'images du mode 5 : éditer `generate_image_filename` (qui mappe mode+path_type -> nom de fichier) et ajouter la ou les images dans `images/`.

Fichiers à consulter avant modification
- `GUI.py` — logique UI, chargeur de traductions, `generate_image_filename`, et `mode_params`.
- `main_tkinter.py` — fonctions de génération, `generate_header`, `calculate_stock_dimensions`.
- `config.json` — valeurs par défaut persistées (à mettre à jour lors d'ajouts/changements de champs).
- `translations.json` — traductions localisées.

Quick start (PowerShell)
- Créer un environnement virtuel et installer les dépendances (le repo fournit `requirement.txt`) :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirement.txt
```

- Lancer l'UI (fenêtre Tkinter) :

```powershell
python GUI.py
```

- Test rapide sans UI (exécution d'une fonction de génération) :

```powershell
python - <<'PY'
import json
from main_tkinter import load_config, surfacing, generate_header, calculate_stock_dimensions
cfg = load_config()
gcode, sx, sy, sz, cz, ex, ey, ch = surfacing(cfg)
hx, hy, hz = calculate_stock_dimensions([(gcode, sx, sy, sz, cz, ex, ey, ch)])
print(generate_header(cfg.get('project_name','proj'), cfg.get('machine','machine'), hx, hy, hz))
print('\n'.join(gcode.splitlines()[:20]))
PY
```

Si quelque chose n'est pas clair, précisez l'intention (bugfix, nouvelle fonctionnalité, refactor) et le mode concerné. Je peux aussi fournir un exemple de patch pour un champ précis.

