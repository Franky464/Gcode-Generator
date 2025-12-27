# setup_environment.ps1

# Définir le chemin du projet et de l'interpréteur Python
$projectDir = "C:\Users\farno\OneDrive\Documents\GitHub\Gcode-Generator"
#$pythonPath = "C:\Users\farno\AppData\Local\Programs\Python\Python38\python.exe"
$pythonPath = "C:\Users\farno\AppData\Local\Python\bin\python.exe"
Write-Host "Configuration de l'environnement pour Gcode-Generator..."

# Étape 1 : Vérifier si l'interpréteur Python existe
if (-Not (Test-Path $pythonPath)) {
    Write-Host "Erreur : Chemin Python spécifié ($pythonPath) non trouvé."
    Write-Host "Veuillez vérifier le chemin ou installer Python 3.8 depuis https://www.python.org/downloads/."
    exit 1
}
Write-Host "Python trouvé : $pythonPath"

# Étape 2 : Vérifier la version de Python
$pythonVersion = & $pythonPath --version
Write-Host "Version de Python : $pythonVersion"

# Étape 3 : Supprimer l'environnement virtuel existant (pour éviter les conflits)
$venvDir = Join-Path $projectDir "venv"
if (Test-Path $venvDir) {
    Write-Host "Suppression de l'environnement virtuel existant pour éviter les conflits..."
    Remove-Item -Path $venvDir -Recurse -Force
}
Write-Host "Création d'un nouvel environnement virtuel dans $venvDir..."
& $pythonPath -m venv $venvDir

# Étape 4 : Activer l'environnement virtuel
$activateScript = Join-Path $venvDir "Scripts\Activate.ps1"
if (-Not (Test-Path $activateScript)) {
    Write-Host "Erreur : Script d'activation de l'environnement virtuel non trouvé."
    exit 1
}
Write-Host "Activation de l'environnement virtuel..."
& $activateScript

# Étape 5 : Mettre à jour pip
Write-Host "Mise à jour de pip..."
python -m pip install --upgrade pip

# Étape 6 : Installer les bibliothèques nécessaires
Write-Host "Installation des bibliothèques matplotlib==3.7.2, numpy, et pillow..."
pip install --force-reinstall matplotlib==3.7.2 numpy pillow

# Étape 7 : Vérifier la présence de mpl_toolkits.mplot3d
Write-Host "Vérification de mpl_toolkits.mplot3d..."
$checkMpl3d = python -c "from mpl_toolkits.mplot3d import Axes3D; import matplotlib; print('mpl_toolkits.mplot3d OK, version: ' + matplotlib.__version__)" 2>&1
if ($checkMpl3d -like "*mpl_toolkits.mplot3d OK*") {
    Write-Host "mpl_toolkits.mplot3d correctement installé : $checkMpl3d"
} else {
    Write-Host "Erreur : Échec de l'installation de mpl_toolkits.mplot3d. Sortie : $checkMpl3d"
    exit 1
}

# Étape 8 : Associer les fichiers .py à l'interpréteur Python
Write-Host "Configuration de l'association des fichiers .py..."
try {
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c assoc .py=Python.File" -Verb RunAs -Wait
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c ftype Python.File=`"$pythonPath`" `"%1`" %*" -Verb RunAs -Wait
    Write-Host "Association des fichiers .py configurée avec $pythonPath."
} catch {
    Write-Host "Avertissement : Impossible de configurer l'association des fichiers .py."
    Write-Host "Exécutez PowerShell en mode administrateur pour configurer l'association."
}

# Étape 9 : Vérifier les bibliothèques
Write-Host "Vérification des bibliothèques..."
$checkLibs = python -c "import matplotlib, numpy, PIL, tkinter; print('Bibliothèques OK')" 2>&1
if ($checkLibs -like "*Bibliothèques OK*") {
    Write-Host "Bibliothèques matplotlib, numpy, pillow, et tkinter correctement installées."
} else {
    Write-Host "Erreur : Échec de l'installation des bibliothèques. Sortie : $checkLibs"
    exit 1
}

# Étape 10 : Vérifier la présence des scripts
$guiScript = Join-Path $projectDir "GUI.py"
$mainScript = Join-Path $projectDir "main_tkinter.py"
$displayScript = Join-Path $projectDir "display_gcode_3d.py"
if (-Not (Test-Path $guiScript)) {
    Write-Host "Erreur : GUI.py non trouvé dans $projectDir"
    exit 1
}
if (-Not (Test-Path $mainScript)) {
    Write-Host "Erreur : main_tkinter.py non trouvé dans $projectDir"
    exit 1
}
if (-Not (Test-Path $displayScript)) {
    Write-Host "Erreur : display_gcode_3d.py non trouvé dans $projectDir"
    exit 1
}

# Étape 11 : Créer le dossier NC
$ncDir = Join-Path $projectDir "NC"
if (-Not (Test-Path $ncDir)) {
    Write-Host "Création du dossier NC dans $ncDir..."
    New-Item -Path $ncDir -ItemType Directory
}

# Étape 12 : Définir le répertoire de travail
Write-Host "Définition du répertoire de travail à $projectDir..."
Set-Location -Path $projectDir

# Étape 13 : Lancer GUI.py
Write-Host "Lancement de GUI.py..."
python $guiScript

Write-Host "Exécution terminée. L'environnement est configuré."