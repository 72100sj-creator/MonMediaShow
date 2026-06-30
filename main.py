import sys, os, random
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QListWidget, QListWidgetItem, QFileDialog, 
                               QLabel, QComboBox, QSplitter, QStatusBar, QMessageBox)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QIcon, QPixmap

# Version du logiciel
VERSION = "V1.1"

class SlideshowWindow(QWidget):
    def __init__(self, images, interval_ms):
        super().__init__()
        self.images, self.interval_ms, self.current_idx, self.paused = images, interval_ms, 0, False
        self.setWindowTitle(f"Diaporama - MonMediaShow {VERSION}")
        self.showFullScreen()
        self.setStyleSheet("background-color: black; color: white;")
        layout = QVBoxLayout(self)
        self.label = QLabel(); self.label.setAlignment(Qt.AlignCenter); layout.addWidget(self.label)
        self.counter_label = QLabel(); self.counter_label.setAlignment(Qt.AlignCenter); layout.addWidget(self.counter_label)
        self.timer = QTimer(self); self.timer.timeout.connect(self.next_image); self.timer.start(self.interval_ms)
        self.show_image()

    def show_image(self):
        if not self.images: return
        pixmap = QPixmap(self.images[self.current_idx])
        if pixmap.isNull(): self.next_image(); return
        self.label.setPixmap(pixmap.scaled(self.size() - QSize(0, 50), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.counter_label.setText(f"{self.current_idx + 1} / {len(self.images)}")

    def next_image(self): self.current_idx = (self.current_idx + 1) % len(self.images); self.show_image()
    def prev_image(self): self.current_idx = (self.current_idx - 1) % len(self.images); self.show_image()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape: self.timer.stop(); self.close()
        elif event.key() == Qt.Key_Space:
            self.paused = not self.paused
            if self.paused: self.timer.stop()
            else: self.timer.start(self.interval_ms)
        elif event.key() == Qt.Key_Right: self.next_image()
        elif event.key() == Qt.Key_Left: self.prev_image()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"MonMediaShow {VERSION}")
        self.resize(1000, 700); self.images_paths = []
        self.playlist_dir = os.path.expanduser("~/Desktop/MonMediaShow/playlists")
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
        
        pl_layout = QHBoxLayout()
        self.btn_save = QPushButton("Sauvegarder Playlist"); self.btn_save.clicked.connect(self.save_playlist)
        self.btn_load = QPushButton("Ouvrir Playlist"); self.btn_load.clicked.connect(self.load_playlist)
        pl_layout.addWidget(self.btn_save); pl_layout.addWidget(self.btn_load)
        right_layout.addLayout(pl_layout)
        
        self.btn_remove = QPushButton("Supprimer la sélection"); self.btn_remove.clicked.connect(self.remove_selected)
        right_layout.addWidget(self.btn_remove)
        self.sort_combo = QComboBox(); self.sort_combo.addItems(["Tri : Aucun", "Nom (A-Z)", "Nom (Z-A)", "Date création", "Date modif", "Aléatoire"])
        self.sort_combo.currentIndexChanged.connect(self.sort_photos)
        right_layout.addWidget(QLabel("Classer les photos :")); right_layout.addWidget(self.sort_combo)
        self.time_combo = QComboBox(); self.time_combo.addItems(["1s", "2s", "3s", "5s", "10s"])
        right_layout.addWidget(QLabel("Temps par photo :")); right_layout.addWidget(self.time_combo)
        self.btn_slideshow = QPushButton("Lancer le diaporama"); self.btn_slideshow.clicked.connect(self.lancer_diaporama)
        right_layout.addWidget(self.btn_slideshow)
        self.list_widget = QListWidget(); self.list_widget.setSelectionMode(QListWidget.ExtendedSelection)
        self.list_widget.itemSelectionChanged.connect(self.update_preview)
        right_layout.addWidget(self.list_widget)
        
        splitter.addWidget(self.preview_label); splitter.addWidget(right_panel)
        main_layout.addWidget(splitter)
        self.status_bar = QStatusBar(); self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(f"MonMediaShow {VERSION} prêt.")
        self.setStyleSheet("QPushButton { background-color: #333; color: white; border-radius: 5px; padding: 8px; }")

    def save_playlist(self):
        name, ok = QFileDialog.getSaveFileName(self, "Sauvegarder la playlist", self.playlist_dir, "Texte (*.txt)")
        if ok and name:
            with open(name, "w") as f: f.write("\n".join(self.images_paths))
            QMessageBox.information(self, "Succès", "Playlist enregistrée !")

    def load_playlist(self):
        file, _ = QFileDialog.getOpenFileName(self, "Ouvrir une playlist", self.playlist_dir, "Texte (*.txt)")
        if file:
            with open(file, "r") as f:
                paths = f.read().splitlines()
                for p in paths:
                    if os.path.exists(p) and p not in self.images_paths: self.images_paths.append(p)
            self.refresh_list()

    def update_preview(self):
        items = self.list_widget.selectedItems()
        if items:
            path = items[0].data(Qt.UserRole)
            pixmap = QPixmap(path).scaled(500, 500, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.preview_label.setPixmap(pixmap)
        self.status_bar.showMessage(f"{VERSION} | Total : {len(self.images_paths)} | Sélectionnées : {len(items)}")

    def is_valid_image(self, path): return not QPixmap(path).isNull()
    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Sélectionner", "", "Images (*.png *.jpg *.jpeg)")
        for f in files:
            if f not in self.images_paths and self.is_valid_image(f): self.images_paths.append(f)
        self.refresh_list()

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Sélectionner")
        if folder:
            for f in os.listdir(folder):
                if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                    path = os.path.join(folder, f)
                    if path not in self.images_paths and self.is_valid_image(path): self.images_paths.append(path)
        self.refresh_list()

    def remove_selected(self):
        for item in self.list_widget.selectedItems():
            path = item.data(Qt.UserRole)
            if path in self.images_paths: self.images_paths.remove(path)
        self.refresh_list()

    def sort_photos(self):
        mode = self.sort_combo.currentText()
        if "Nom (A-Z)" in mode: self.images_paths.sort()
        elif "Nom (Z-A)" in mode: self.images_paths.sort(reverse=True)
        elif "création" in mode: self.images_paths.sort(key=os.path.getctime)
        elif "modif" in mode: self.images_paths.sort(key=os.path.getmtime, reverse=True)
        elif "Aléatoire" in mode: random.shuffle(self.images_paths)
        self.refresh_list()

    def refresh_list(self):
        self.list_widget.clear()
        for path in self.images_paths:
            item = QListWidgetItem(os.path.basename(path))
            item.setData(Qt.UserRole, path)
            self.list_widget.addItem(item)
        self.status_bar.showMessage(f"{VERSION} | Total : {len(self.images_paths)}")

    def lancer_diaporama(self):
        if self.images_paths:
            seconds = int(self.time_combo.currentText().replace('s', ''))
            self.diapo = SlideshowWindow(self.images_paths, seconds * 1000)
            self.diapo.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
