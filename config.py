import os

# === INFORMATIONS DU LOGICIEL ===
APP_NAME = "MediaShow Photo"
VERSION = "V2.6.3"

# === CHEMINS ET DOSSIERS ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "mediashow.log")
PLAYLIST_DIR = os.path.join(BASE_DIR, "playlists")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

# === PARAMETRES DES IMAGES ===
SUPPORTED_FORMATS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.svg')
FILE_DIALOG_FILTER = "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.svg)"
TAILLE_MIN_KO = 5

# === TRANSITIONS ===
TRANSITION_OPTIONS = ["Aucune", "Fondu au noir", "Fondu blanc", "Zoom doux", "Déplacement lent"]
ANIMATION_DURATION_FADE = 800
ZOOM_FACTOR = 1.15
PAN_FACTOR = 1.15
PAN_OFFSET = 0.05
ANIMATION_ZOOM_PAN_EXTRA_TIME = 2000

# === TRI ===
SORT_OPTIONS = ["Nom (A-Z)", "Nom (Z-A)", "Date de création", "Date de modif", "Aléatoire"]