import sys, os, random, json
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QListWidget, QListWidgetItem, QFileDialog, 
                               QLabel, QComboBox, QSplitter, QStatusBar, QMessageBox, QProgressBar,
                               QCheckBox, QGraphicsOpacityEffect)
from PySide6.QtCore import Qt, QSize, QTimer, QThread, Signal, QPropertyAnimation
from PySide6.QtGui import QPixmap, QTransform

VERSION = "V1.8"
TAILLE_MIN_KO = 50 

class ImportWorker(QThread):
    progress_update = Signal(str) 
    finished_import = Signal(list)

    def __init__(self, paths_to_search, already_loaded_paths):
        super().__init__()
        self.paths_to_search = paths_to_search
        self.already_loaded_paths = set(already_loaded_paths)
        self.found_images = []

    def is_valid_fast(self, path):
        try:
            if os.path.getsize(path) < TAILLE_MIN_KO * 1024: return False
        except OSError: return False
        return True

    def run(self):
        for path in self.paths_to_search:
            if os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    for f in files:
                        if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                            full_path = os.path.join(root, f)
                            if full_path not in self.already_loaded_paths and self.is_valid_fast(full_path):
                                self.found_images.append(full_path)
                                self.already_loaded_paths.add(full_path)
        self.finished_import.emit(self.found_images)

class SlideshowWindow(QWidget):
    def __init__(self, images, interval_ms, use_fade, transformations):
        super().__init__()
        self.images, self.interval_ms, self.use_fade, self.transformations = images, interval_ms, use_fade, transformations
        self.current_idx, self.paused = 0, False
        self.cache = {}
        
        self.setWindowTitle(f"Diaporama - MonMediaShow {VERSION}")
        self.showFullScreen()
        self.setStyleSheet("background-color: black; color: white;")
        layout = QVBoxLayout(self)
        self.label = QLabel(); self.label.setAlignment(Qt.AlignCenter); layout.addWidget(self.label)
        self.counter_label = QLabel(); self.counter_label.setAlignment(Qt.AlignCenter); layout.addWidget(self.counter_label)
        
        self.opacity_effect = QGraphicsOpacityEffect(self.label)
        self.label.setGraphicsEffect(self.opacity_effect)
        
        self.show_image()
        self.timer = QTimer(self); self.timer.timeout.connect(self.transition_next); self.timer.start(self.interval_ms)

    def appliquer_transformations(self, pixmap, path):
        trans = self.transformations.get(path, {"rot": 0, "mirror": False})
        t = QTransform()
        if trans["mirror"]: t.scale(-1, 1)
        t.rotate(trans["rot"])
        return pixmap.transformed(t, Qt.SmoothTransformation)

    def gerer_le_cache(self):
        total = len(self.images)
        if total == 0: return
        taille_cible = self.size() - QSize(0, 50)
        positions_a_garder = set([(self.current_idx + i) % total for i in range(-1, 4)])
        for idx in list(self.cache.keys()):
            if idx not in positions_a_garder: del self.cache[idx]
        for idx in positions_a_garder:
            if idx not in self.cache:
                path = self.images[idx]
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    pixmap = pixmap.scaled(taille_cible, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.cache[idx] = self.appliquer_transformations(pixmap, path)

    def show_image(self):
        if not self.images: return
        self.gerer_le_cache() 
        pixmap_pret = self.cache.get(self.current_idx)
        if not pixmap_pret: 
            self.next_image()
            return
            
        self.label.setPixmap(pixmap_pret)
        self.counter_label.setText(f"{self.current_idx + 1} / {len(self.images)}")
        
        if self.use_fade:
            self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
            self.anim.setDuration(800)
            self.anim.setStartValue(0); self.anim.setEndValue(1)
            self.anim.start()
        else:
            self.opacity_effect.setOpacity(1)

    def transition_next(self):
        if self.use_fade:
            self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
            self.anim.setDuration(800)
            self.anim.setStartValue(1); self.anim.setEndValue(0)
            self.anim.finished.connect(self.next_image)
            self.anim.start()
        else:
            self.next_image()

    def next_image(self): 
        if not self.images: return
        self.current_idx = (self.current_idx + 1) % len(self.images); self.show_image()
    def prev_image(self): 
        if not self.images: return
        self.current_idx = (self.current_idx - 1) % len(self.images); self.show_image()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape: self.timer.stop(); self.close()
        elif event.key() == Qt.Key_Space:
            self.paused = not self.paused
            if self.paused: self.timer.stop()
            else: self.timer.start(self.interval_ms)
        elif event.key() == Qt.Key_Right: self.transition_next()
        elif event.key() == Qt.Key_Left: self.prev_image()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"MonMediaShow {VERSION}")
        self.resize(1000, 700)
        self.images_paths = []
        self.history_list = []
        self.last_slideshow_paths = []
        self.transformations = {} 
        
        self.base_dir = os.path.expanduser("~/Desktop/MonMediaShow")
        self.playlist_dir = os.path.join(self.base_dir, "playlists")
        self.config_file = os.path.join(self.base_dir, "config.json")
        if not os.path.exists(self.playlist_dir): os.makedirs(self.playlist_dir)
        
        main_widget = QWidget(); self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        splitter = QSplitter(Qt.Horizontal)
        
        self.preview_label = QLabel("Sélectionnez une photo"); self.preview_label.setAlignment(Qt.AlignCenter)
        right_panel = QWidget(); right_layout = QVBoxLayout(right_panel)
        
        btn_layout = QHBoxLayout()
        self.btn_add_files = QPushButton("Ajouter photos"); self.btn_add_files.clicked.connect(self.add_files)
        self.btn_add_folder = QPushButton("Charger dossier"); self.btn_add_folder.clicked.connect(self.add_folder)
        btn_layout.addWidget(self.btn_add_files); btn_layout.addWidget(self.btn_add_folder)
        right_layout.addLayout(btn_layout)
        
        # Outils
        tool_layout = QHBoxLayout()
        self.btn_rot = QPushButton("🔄 Rotation"); self.btn_rot.clicked.connect(self.apply_rotation)
        self.btn_mirror = QPushButton("↔️ Miroir"); self.btn_mirror.clicked.connect(self.apply_mirror)
        tool_layout.addWidget(self.btn_rot); tool_layout.addWidget(self.btn_mirror)
        right_layout.addLayout(tool_layout)
        
        self.history_combo = QComboBox()
        self.history_combo.currentIndexChanged.connect(self.load_history_folder)
        right_layout.addWidget(QLabel("🕒 Dossiers récents :"))
        right_layout.addWidget(self.history_combo)
        
        pl_layout = QHBoxLayout()
        self.btn_save = QPushButton("Sauvegarder Playlist"); self.btn_save.clicked.connect(self.save_playlist)
        self.btn_load = QPushButton("Ouvrir Playlist"); self.btn_load.clicked.connect(self.load_playlist)
        pl_layout.addWidget(self.btn_save); pl_layout.addWidget(self.btn_load)
        right_layout.addLayout(pl_layout)
        
        self.sort_combo = QComboBox(); self.sort_combo.addItems(["Tri : Aucun", "Nom (A-Z)", "Nom (Z-A)", "Date création", "Date modif", "Aléatoire"])
        self.sort_combo.currentIndexChanged.connect(self.sort_photos)
        right_layout.addWidget(QLabel("Classer les photos :")); right_layout.addWidget(self.sort_combo)
        
        self.time_combo = QComboBox(); self.time_combo.addItems(["1s", "2s", "3s", "5s", "10s"])
        right_layout.addWidget(QLabel("Temps par photo :")); right_layout.addWidget(self.time_combo)
        
        self.chk_fade = QCheckBox("Activer le fondu")
        self.chk_fade.setChecked(True)
        right_layout.addWidget(self.chk_fade)
        
        self.btn_slideshow = QPushButton("Lancer le diaporama"); self.btn_slideshow.clicked.connect(self.lancer_diaporama)
        right_layout.addWidget(self.btn_slideshow)
        
        self.list_widget = QListWidget(); self.list_widget.setSelectionMode(QListWidget.ExtendedSelection)
        self.list_widget.itemSelectionChanged.connect(self.update_preview)
        right_layout.addWidget(self.list_widget)
        
        splitter.addWidget(self.preview_label); splitter.addWidget(right_panel)
        main_layout.addWidget(splitter)
        
        self.status_bar = QStatusBar(); self.setStatusBar(self.status_bar)
        self.load_config()
        self.setStyleSheet("QPushButton { background-color: #333; color: white; border-radius: 5px; padding: 8px; }")

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                    self.sort_combo.setCurrentIndex(data.get("sort_idx", 0))
                    self.time_combo.setCurrentIndex(data.get("time_idx", 2))
                    self.history_list = data.get("history", [])
            except: pass
        self.update_history_combo_ui()

    def save_config(self):
        data = {"sort_idx": self.sort_combo.currentIndex(), "time_idx": self.time_combo.currentIndex(), "history": self.history_list}
        try:
            with open(self.config_file, "w") as f: json.dump(data, f)
        except: pass

    def add_to_history(self, folder_path):
        if folder_path in self.history_list: self.history_list.remove(folder_path)
        self.history_list.insert(0, folder_path)
        self.history_list = self.history_list[:10]
        self.update_history_combo_ui()
        self.save_config()

    def update_history_combo_ui(self):
        self.history_combo.blockSignals(True)
        self.history_combo.clear()
        self.history_combo.addItem("Choisir un dossier récent...")
        for path in self.history_list: self.history_combo.addItem(os.path.basename(path), path)
        self.history_combo.blockSignals(False)

    def load_history_folder(self, index):
        if index > 0: self.start_import([self.history_combo.itemData(index)])

    def save_playlist(self):
        name, _ = QFileDialog.getSaveFileName(self, "Sauvegarder la playlist", self.playlist_dir, "Texte (*.txt)")
        if name:
            with open(name, "w") as f: f.write("\n".join(self.images_paths))

    def load_playlist(self):
        file, _ = QFileDialog.getOpenFileName(self, "Ouvrir", self.playlist_dir, "Texte (*.txt)")
        if file:
            with open(file, "r") as f: self.start_import(f.read().splitlines())

    def apply_rotation(self):
        for item in self.list_widget.selectedItems():
            path = item.data(Qt.UserRole)
            if path not in self.transformations: self.transformations[path] = {"rot": 0, "mirror": False}
            self.transformations[path]["rot"] = (self.transformations[path]["rot"] + 90) % 360
        self.update_preview()

    def apply_mirror(self):
        for item in self.list_widget.selectedItems():
            path = item.data(Qt.UserRole)
            if path not in self.transformations: self.transformations[path] = {"rot": 0, "mirror": False}
            self.transformations[path]["mirror"] = not self.transformations[path]["mirror"]
        self.update_preview()

    def update_preview(self):
        items = self.list_widget.selectedItems()
        if items:
            path = items[0].data(Qt.UserRole)
            pixmap = QPixmap(path)
            trans = self.transformations.get(path, {"rot": 0, "mirror": False})
            t = QTransform()
            if trans["mirror"]: t.scale(-1, 1)
            t.rotate(trans["rot"])
            pixmap = pixmap.transformed(t, Qt.SmoothTransformation)
            self.preview_label.setPixmap(pixmap.scaled(500, 500, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def start_import(self, paths):
        self.worker = ImportWorker(paths, self.images_paths)
        self.worker.finished_import.connect(self.on_import_finished)
        self.worker.start()

    def on_import_finished(self, new_images):
        self.images_paths.extend(new_images)
        self.refresh_list()

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Sélectionner", "", "Images (*.png *.jpg *.jpeg)")
        if files: self.start_import(files)

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Sélectionner")
        if folder: 
            self.start_import([folder])
            self.add_to_history(folder)

    def refresh_list(self):
        self.list_widget.clear()
        for path in self.images_paths:
            item = QListWidgetItem(os.path.basename(path))
            item.setData(Qt.UserRole, path)
            self.list_widget.addItem(item)
        self.status_bar.showMessage(f"Total : {len(self.images_paths)}")

    def sort_photos(self):
        mode = self.sort_combo.currentText()
        if "Nom (A-Z)" in mode: self.images_paths.sort()
        elif "Nom (Z-A)" in mode: self.images_paths.sort(reverse=True)
        elif "Aléatoire" in mode: random.shuffle(self.images_paths)
        self.refresh_list()
        self.save_config()

    def lancer_diaporama(self):
        if self.images_paths:
            seconds = int(self.time_combo.currentText().replace('s', ''))
            self.diapo = SlideshowWindow(self.images_paths, seconds * 1000, self.chk_fade.isChecked(), self.transformations)
            self.diapo.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())