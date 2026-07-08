import sys, os, random, json, logging
import config
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QListWidget, QListWidgetItem, QFileDialog, 
                               QLabel, QComboBox, QSplitter, QStatusBar, QCheckBox,
                               QGraphicsOpacityEffect, QSlider, QTabWidget, QFrame, QMessageBox)
from PySide6.QtCore import Qt, QSize, QTimer, QThread, Signal, QPropertyAnimation, QRect, QTime
from PySide6.QtGui import QPixmap, QTransform, QCloseEvent, QDragEnterEvent, QDropEvent, QIcon

# Initialisation des logs
os.makedirs(config.LOG_DIR, exist_ok=True)
logging.basicConfig(filename=config.LOG_FILE, level=logging.ERROR, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# --- STYLE MODERNE GLOBAL ---
MODERN_STYLE = """
QWidget { background-color: #121212; color: #FFFFFF; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; font-size: 13px; }
QPushButton { background-color: #1E1E1E; border: 1px solid #333333; border-radius: 8px; padding: 8px 15px; color: #FFFFFF; font-weight: bold; }
QPushButton:hover { background-color: #2A2A2A; border: 1px solid #00BCD4; }
QPushButton:pressed { background-color: #00BCD4; color: #000000; }
QPushButton:disabled { background-color: #1A1A1A; color: #555555; border: 1px solid #222222; }
QPushButton#PlayButton { background-color: #00BCD4; color: #000000; border: none; }
QPushButton#PlayButton:hover { background-color: #00E5FF; }
QPushButton#PlayButton:disabled { background-color: #225555; color: #888888; }
QComboBox { background-color: #1E1E1E; border: 1px solid #333333; border-radius: 6px; padding: 6px; color: white; }
QComboBox:hover { border: 1px solid #00BCD4; }
QSlider::groove:horizontal { border-radius: 2px; height: 4px; background: #333333; }
QSlider::handle:horizontal { background: #00BCD4; width: 16px; height: 16px; margin: -6px 0; border-radius: 8px; }
QSlider::handle:horizontal:hover { background: #00E5FF; }
QListWidget { background-color: #181818; border: 1px solid #222222; border-radius: 12px; outline: none; }
QListWidget::item { background-color: #222222; border-radius: 10px; margin: 8px; padding: 10px; color: #DDDDDD; }
QListWidget::item:selected { background-color: #2A2A2A; border: 2px solid #00BCD4; color: #FFFFFF; }
QTabWidget::pane { border: 1px solid #333333; border-radius: 8px; background: #181818; top: -1px; }
QTabBar::tab { background: #121212; color: #888888; padding: 8px 20px; border-top-left-radius: 6px; border-top-right-radius: 6px; font-weight: bold; }
QTabBar::tab:selected { background: #181818; color: #00BCD4; border-bottom: 2px solid #00BCD4; }
QCheckBox { spacing: 10px; }
QCheckBox::indicator { width: 18px; height: 18px; border-radius: 9px; border: 2px solid #555555; background: #1E1E1E; }
QCheckBox::indicator:checked { background: #00BCD4; border: 2px solid #00BCD4; }
"""

class ImportWorker(QThread):
    finished_import = Signal(list)
    def __init__(self, paths_to_search, already_loaded_paths):
        super().__init__()
        self.paths_to_search = paths_to_search
        self.already_loaded_paths = set(already_loaded_paths)
        self.found_images = []

    def is_valid_fast(self, path):
        try:
            if os.path.getsize(path) < config.TAILLE_MIN_KO * 1024: return False
            return True
        except Exception as e: return False

    def run(self):
        for path in self.paths_to_search:
            if os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    for f in files:
                        if f.lower().endswith(config.SUPPORTED_FORMATS):
                            full_path = os.path.join(root, f)
                            if full_path not in self.already_loaded_paths and self.is_valid_fast(full_path):
                                self.found_images.append(full_path)
                                self.already_loaded_paths.add(full_path)
            elif os.path.isfile(path):
                if path.lower().endswith(config.SUPPORTED_FORMATS):
                    if path not in self.already_loaded_paths and self.is_valid_fast(path):
                        self.found_images.append(path)
                        self.already_loaded_paths.add(path)
        self.finished_import.emit(self.found_images)

class SlideshowWindow(QWidget):
    def __init__(self, images, interval_ms, transition_type, transformations, screen_idx=0, options=None):
        super().__init__()
        self.images, self.interval_ms, self.transition_type, self.transformations = images, interval_ms, transition_type, transformations
        self.current_idx, self.paused = 0, False
        self.cache = {}
        self.options = options if options else {"version": True, "filename": True, "counter": True, "time": True}
        self.setWindowTitle(f"Diaporama - {config.APP_NAME} {config.VERSION}")
        screens = QApplication.screens()
        target_screen = screens[screen_idx] if screen_idx < len(screens) else QApplication.primaryScreen()
        self.setScreen(target_screen)
        screen_geo = target_screen.geometry()
        self.W, self.H = screen_geo.width(), screen_geo.height()
        self.setGeometry(screen_geo)
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setGeometry(0, 0, self.W, self.H)
        self.info_panel = QFrame(self)
        self.info_panel.setStyleSheet("background-color: rgba(20, 20, 20, 210); border-radius: 15px;")
        self.info_layout = QHBoxLayout(self.info_panel)
        self.info_layout.setContentsMargins(20, 8, 20, 8)
        self.counter_label = QLabel("")
        self.counter_label.setAlignment(Qt.AlignCenter)
        self.counter_label.setStyleSheet("color: #FFFFFF; font-weight: 500; font-size: 14px; background: transparent;")
        self.info_layout.addWidget(self.counter_label)
        self.info_panel.setGeometry((self.W - 500) // 2, self.H - 70, 500, 40)
        self.info_panel.hide()
        self.setMouseTracking(True)
        self.mouse_timer = QTimer(self)
        self.mouse_timer.timeout.connect(self.hide_floating_bar)
        self.showFullScreen()
        self.show_image()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.transition_next)
        self.timer.start(self.interval_ms)
        self.info_timer = QTimer(self)
        self.info_timer.timeout.connect(self.update_info_text)
        self.info_timer.start(1000)
        self.show_floating_bar()

    def mouseMoveEvent(self, event): self.show_floating_bar()
    def show_floating_bar(self): self.info_panel.show(); self.setCursor(Qt.ArrowCursor); self.mouse_timer.start(3000)
    def hide_floating_bar(self): self.info_panel.hide(); self.setCursor(Qt.BlankCursor); self.mouse_timer.stop()
    def appliquer_transformations(self, pixmap, path):
        try:
            trans = self.transformations.get(path, {"rot": 0, "mirror": False})
            t = QTransform()
            if trans["mirror"]: t.scale(-1, 1)
            t.rotate(trans["rot"])
            return pixmap.transformed(t, Qt.SmoothTransformation)
        except: return pixmap
    def gerer_le_cache(self):
        total = len(self.images)
        if total == 0: return
        taille_cible = QSize(self.W, self.H)
        positions_a_garder = set([(self.current_idx + i) % total for i in range(-1, 4)])
        for idx in list(self.cache.keys()):
            if idx not in positions_a_garder: del self.cache[idx]
        for idx in positions_a_garder:
            if idx not in self.cache:
                path = self.images[idx]
                if os.path.exists(path):
                    try:
                        pixmap = QPixmap(path)
                        if not pixmap.isNull():
                            pixmap = pixmap.scaled(taille_cible, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            self.cache[idx] = self.appliquer_transformations(pixmap, path)
                    except: pass
    def update_info_text(self):
        if not self.images: self.counter_label.setText(""); return
        parts = []
        if self.options.get("version", True): parts.append(f"{config.APP_NAME} {config.VERSION}")
        if self.options.get("filename", True) and 0 <= self.current_idx < len(self.images): parts.append(os.path.basename(self.images[self.current_idx]))
        if self.options.get("counter", True): parts.append(f"{self.current_idx + 1} / {len(self.images)}")
        if self.options.get("time", True): parts.append(QTime.currentTime().toString("HH:mm"))
        text = "  •  ".join(parts)
        self.counter_label.setText(text)
        self.counter_label.adjustSize()
        new_width = self.counter_label.width() + 60
        self.info_panel.setGeometry((self.W - new_width) // 2, self.H - 70, new_width, 40)
    def show_image(self):
        if not self.images: return
        self.gerer_le_cache()
        pixmap_pret = self.cache.get(self.current_idx)
        if pixmap_pret is None or pixmap_pret.isNull(): self.next_image(); return
        self.setStyleSheet("background-color: white;" if self.transition_type == "Fondu blanc" else "background-color: black;")
        self.label.setPixmap(pixmap_pret)
        self.update_info_text()
        pw, ph = pixmap_pret.width(), pixmap_pret.height()
        base_rect = QRect((self.W - pw) // 2, (self.H - ph) // 2, pw, ph)
        if hasattr(self, 'anim') and self.anim: self.anim.stop()
        self.label.setGraphicsEffect(None)
        if self.transition_type in ["Fondu au noir", "Fondu blanc"]:
            self.label.setScaledContents(False); self.label.setGeometry(base_rect)
            opacity_effect = QGraphicsOpacityEffect(self.label); self.label.setGraphicsEffect(opacity_effect)
            self.anim = QPropertyAnimation(opacity_effect, b"opacity"); self.anim.setDuration(config.ANIMATION_DURATION_FADE); self.anim.setStartValue(0.0); self.anim.setEndValue(1.0); self.anim.start()
        elif self.transition_type == "Zoom doux":
            self.label.setScaledContents(True); end_pw, end_ph = int(pw * config.ZOOM_FACTOR), int(ph * config.ZOOM_FACTOR)
            end_rect = QRect((self.W - end_pw) // 2, (self.H - end_ph) // 2, end_pw, end_ph)
            self.anim = QPropertyAnimation(self.label, b"geometry"); self.anim.setDuration(self.interval_ms + config.ANIMATION_ZOOM_PAN_EXTRA_TIME); self.anim.setStartValue(base_rect); self.anim.setEndValue(end_rect); self.anim.start()
        elif self.transition_type == "Déplacement lent":
            self.label.setScaledContents(True); pan_pw, pan_ph = int(pw * config.PAN_FACTOR), int(ph * config.PAN_FACTOR); offset = int(pan_pw * config.PAN_OFFSET)
            start_x, end_x = (self.W - pan_pw) // 2 - offset, (self.W - pan_pw) // 2 + offset; start_y = (self.H - pan_ph) // 2
            self.anim = QPropertyAnimation(self.label, b"geometry"); self.anim.setDuration(self.interval_ms + config.ANIMATION_ZOOM_PAN_EXTRA_TIME); self.anim.setStartValue(QRect(start_x, start_y, pan_pw, pan_ph)); self.anim.setEndValue(QRect(end_x, start_y, pan_pw, pan_ph)); self.anim.start()
        else: self.label.setScaledContents(False); self.label.setGeometry(base_rect)
    def transition_next(self):
        if self.transition_type in ["Fondu au noir", "Fondu blanc"]:
            eff = self.label.graphicsEffect() or QGraphicsOpacityEffect(self.label)
            if not self.label.graphicsEffect(): self.label.setGraphicsEffect(eff)
            self.anim = QPropertyAnimation(eff, b"opacity"); self.anim.setDuration(config.ANIMATION_DURATION_FADE); self.anim.setStartValue(1.0); self.anim.setEndValue(0.0); self.anim.finished.connect(self.next_image); self.anim.start()
        else: self.next_image()
    def next_image(self): 
        if not self.images: return
        self.current_idx = (self.current_idx + 1) % len(self.images); self.show_image()
    def prev_image(self): 
        if not self.images: return
        self.current_idx = (self.current_idx - 1) % len(self.images); self.show_image()
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape: self.timer.stop(); self.info_timer.stop(); self.mouse_timer.stop(); self.close()
        elif event.key() == Qt.Key_Space:
            self.paused = not self.paused
            if self.paused: self.timer.stop(); (hasattr(self, 'anim') and self.anim.state() == QPropertyAnimation.Running and self.anim.pause()); self.show_floating_bar(); self.mouse_timer.stop()
            else: self.timer.start(self.interval_ms); (hasattr(self, 'anim') and self.anim.state() == QPropertyAnimation.Paused and self.anim.resume()); self.mouse_timer.start(3000)
        elif event.key() == Qt.Key_Right: self.transition_next()
        elif event.key() == Qt.Key_Left: self.prev_image()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{config.APP_NAME} {config.VERSION}")
        self.resize(1100, 750)
        icon_path = os.path.join(config.ASSETS_DIR, "icon.png")
        if os.path.exists(icon_path): self.setWindowIcon(QIcon(icon_path))
        self.setStyleSheet(MODERN_STYLE); self.setAcceptDrops(True)
        self.images_paths = []; self.history_list = []; self.transformations = {} 
        self.base_dir, self.playlist_dir, self.config_file = config.BASE_DIR, config.PLAYLIST_DIR, config.CONFIG_FILE
        if not os.path.exists(self.playlist_dir): os.makedirs(self.playlist_dir)
        main_widget = QWidget(); self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget); main_layout.setContentsMargins(10, 10, 10, 10); main_layout.setSpacing(15)
        toolbar_layout = QHBoxLayout()
        self.btn_add_files = QPushButton("📂 Ajouter"); self.btn_add_files.clicked.connect(self.add_files)
        self.btn_add_folder = QPushButton("🖼 Dossier"); self.btn_add_folder.clicked.connect(self.add_folder)
        self.btn_remove_files = QPushButton("🗑 Retirer"); self.btn_remove_files.clicked.connect(self.remove_files)
        self.btn_clear_all = QPushButton("🗑️ Vider la Setlist"); self.btn_clear_all.clicked.connect(self.clear_setlist); self.btn_clear_all.setEnabled(False) 
        self.btn_slideshow = QPushButton("▶ Lecture"); self.btn_slideshow.setObjectName("PlayButton"); self.btn_slideshow.clicked.connect(self.lancer_diaporama); self.btn_slideshow.setEnabled(False) 
        toolbar_layout.addWidget(self.btn_add_files); toolbar_layout.addWidget(self.btn_add_folder); toolbar_layout.addWidget(self.btn_remove_files); toolbar_layout.addWidget(self.btn_clear_all); toolbar_layout.addStretch(); toolbar_layout.addWidget(self.btn_slideshow)
        main_layout.addLayout(toolbar_layout)
        splitter = QSplitter(Qt.Horizontal)
        self.list_widget = QListWidget(); self.list_widget.setViewMode(QListWidget.IconMode); self.list_widget.setIconSize(QSize(100, 100)); self.list_widget.setResizeMode(QListWidget.Adjust); self.list_widget.setSpacing(12); self.list_widget.setSelectionMode(QListWidget.ExtendedSelection); splitter.addWidget(self.list_widget)
        right_panel = QWidget(); right_layout = QVBoxLayout(right_panel); right_layout.setContentsMargins(0, 0, 0, 0); self.tabs = QTabWidget()
        tab_lecture = QWidget(); lecture_layout = QVBoxLayout(tab_lecture); lecture_layout.setSpacing(20)
        dur_layout = QVBoxLayout(); self.lbl_duree = QLabel("Durée : 4 s"); self.lbl_duree.setStyleSheet("color: #00BCD4; font-weight: bold;"); self.slider_duree = QSlider(Qt.Horizontal); self.slider_duree.setRange(1, 60); self.slider_duree.setValue(4); self.slider_duree.valueChanged.connect(self.update_duration_label); dur_layout.addWidget(self.lbl_duree); dur_layout.addWidget(self.slider_duree); lecture_layout.addLayout(dur_layout)
        self.transition_combo = QComboBox(); self.transition_combo.addItems(config.TRANSITION_OPTIONS); self.transition_combo.currentIndexChanged.connect(self.save_config); lecture_layout.addWidget(QLabel("Effet de transition :")); lecture_layout.addWidget(self.transition_combo)
        self.screen_combo = QComboBox(); self.screen_combo.currentIndexChanged.connect(self.save_config); lecture_layout.addWidget(QLabel("Écran de projection :")); lecture_layout.addWidget(self.screen_combo); self.detecter_les_ecrans(); lecture_layout.addStretch(); self.tabs.addTab(tab_lecture, "⚙ Paramètres")
        tab_affichage = QWidget(); aff_layout = QVBoxLayout(tab_affichage); aff_layout.setSpacing(15)
        self.cb_version = QCheckBox("Afficher la version"); self.cb_filename = QCheckBox("Afficher le nom du fichier"); self.cb_counter = QCheckBox("Afficher le compteur"); self.cb_time = QCheckBox("Afficher l'heure")
        for cb in [self.cb_version, self.cb_filename, self.cb_counter, self.cb_time]: cb.stateChanged.connect(self.save_config); aff_layout.addWidget(cb)
        aff_layout.addStretch(); self.tabs.addTab(tab_affichage, "📊 Affichage")
        tab_outils = QWidget(); outils_layout = QVBoxLayout(tab_outils); outils_layout.setSpacing(15)
        tool_btns = QHBoxLayout(); self.btn_rot = QPushButton("🔄 Rotation"); self.btn_rot.clicked.connect(self.apply_rotation); self.btn_mirror = QPushButton("↔️ Miroir"); self.btn_mirror.clicked.connect(self.apply_mirror); tool_btns.addWidget(self.btn_rot); tool_btns.addWidget(self.btn_mirror); outils_layout.addLayout(tool_btns)
        self.sort_combo = QComboBox(); self.sort_combo.addItems(config.SORT_OPTIONS); self.sort_combo.currentIndexChanged.connect(self.sort_photos); outils_layout.addWidget(QLabel("Trier par :")); outils_layout.addWidget(self.sort_combo)
        self.history_combo = QComboBox(); self.history_combo.currentIndexChanged.connect(self.load_history_folder); outils_layout.addWidget(QLabel("Dossiers récents :")); outils_layout.addWidget(self.history_combo)
        pl_btns = QHBoxLayout(); self.btn_save = QPushButton("💾 Sauver Playlist"); self.btn_save.clicked.connect(self.save_playlist); self.btn_load = QPushButton("📂 Ouvrir Playlist"); self.btn_load.clicked.connect(self.load_playlist); pl_btns.addWidget(self.btn_save); pl_btns.addWidget(self.btn_load); outils_layout.addLayout(pl_btns); outils_layout.addStretch(); self.tabs.addTab(tab_outils, "🛠 Outils")
        right_layout.addWidget(self.tabs); splitter.addWidget(right_panel); splitter.setSizes([750, 350]); main_layout.addWidget(splitter); self.status_bar = QStatusBar(); self.setStatusBar(self.status_bar); self.load_config()

    def detecter_les_ecrans(self):
        self.screen_combo.clear(); screens = QApplication.screens()
        for i, screen in enumerate(screens): self.screen_combo.addItem("Écran principal" if screen == QApplication.primaryScreen() else f"Écran secondaire ({i})", i)
    def update_duration_label(self, value): self.lbl_duree.setText(f"Durée : {value} s"); self.save_config()
    def dragEnterEvent(self, event: QDragEnterEvent): event.acceptProposedAction() if event.mimeData().hasUrls() else event.ignore()
    def dropEvent(self, event: QDropEvent):
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if paths: self.start_import(paths); self.add_to_history(paths[0]) if os.path.isdir(paths[0]) else None
    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                    self.sort_combo.setCurrentIndex(data.get("sort_idx", 0))
                    self.slider_duree.setValue(data.get("time_s", 4))
                    self.transition_combo.setCurrentIndex(data.get("transition_idx", 0))
                    self.screen_combo.setCurrentIndex(data.get("projection_idx", 0))
                    self.cb_version.setChecked(data.get("show_version", True))
                    self.cb_filename.setChecked(data.get("show_filename", True))
                    self.cb_counter.setChecked(data.get("show_counter", True))
                    self.cb_time.setChecked(data.get("show_time", True))
                    self.history_list = data.get("history", [])
                    self.resize(data.get("width", 1100), data.get("height", 750))
            except: pass
        self.update_history_combo_ui()
    def save_config(self):
        data = { "sort_idx": self.sort_combo.currentIndex(), "time_s": self.slider_duree.value(), "transition_idx": self.transition_combo.currentIndex(), "projection_idx": self.screen_combo.currentIndex(), "show_version": self.cb_version.isChecked(), "show_filename": self.cb_filename.isChecked(), "show_counter": self.cb_counter.isChecked(), "show_time": self.cb_time.isChecked(), "history": self.history_list, "width": self.width(), "height": self.height() }
        try:
            with open(self.config_file, "w") as f: json.dump(data, f)
        except: pass
    def closeEvent(self, event: QCloseEvent): self.save_config(); event.accept()
    def add_to_history(self, folder_path):
        if folder_path in self.history_list: self.history_list.remove(folder_path)
        self.history_list.insert(0, folder_path); self.history_list = self.history_list[:10]; self.update_history_combo_ui(); self.save_config()
    def update_history_combo_ui(self):
        self.history_combo.blockSignals(True); self.history_combo.clear(); self.history_combo.addItem("Choisir un dossier récent...")
        for path in self.history_list: self.history_combo.addItem(os.path.basename(path), path)
        self.history_combo.blockSignals(False)
    def load_history_folder(self, index):
        if index > 0: self.start_import([self.history_combo.itemData(index)])
    def save_playlist(self):
        name, _ = QFileDialog.getSaveFileName(self, "Sauvegarder", self.playlist_dir, "Texte (*.txt)")
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
    def apply_mirror(self):
        for item in self.list_widget.selectedItems():
            path = item.data(Qt.UserRole)
            if path not in self.transformations: self.transformations[path] = {"rot": 0, "mirror": False}
            self.transformations[path]["mirror"] = not self.transformations[path]["mirror"]
    def start_import(self, paths): self.status_bar.showMessage("Importation en cours..."); self.worker = ImportWorker(paths, self.images_paths); self.worker.finished_import.connect(self.on_import_finished); self.worker.start()
    def on_import_finished(self, new_images): self.images_paths.extend(new_images); self.refresh_list()
    def add_files(self): files, _ = QFileDialog.getOpenFileNames(self, "Sélectionner", "", config.FILE_DIALOG_FILTER); self.start_import(files) if files else None
    def add_folder(self): folder = QFileDialog.getExistingDirectory(self, "Sélectionner"); (self.start_import([folder]), self.add_to_history(folder)) if folder else None
    def remove_files(self):
        for item in self.list_widget.selectedItems():
            path = item.data(Qt.UserRole)
            if path in self.images_paths: self.images_paths.remove(path)
        self.refresh_list()
    def clear_setlist(self):
        if not self.images_paths: return
        msg_box = QMessageBox(self); msg_box.setWindowTitle("Vider la Setlist"); msg_box.setText("Voulez-vous vraiment supprimer toutes les photos de la Setlist ?")
        btn_vider = msg_box.addButton("Vider", QMessageBox.AcceptRole); btn_annuler = msg_box.addButton("Annuler", QMessageBox.RejectRole); msg_box.exec()
        if msg_box.clickedButton() == btn_vider: self.images_paths.clear(); self.refresh_list()
    def refresh_list(self):
        self.list_widget.clear()
        for path in self.images_paths:
            nom = os.path.basename(path)
            item = QListWidgetItem(nom[:12] + "..." if len(nom) > 15 else nom); item.setData(Qt.UserRole, path); item.setTextAlignment(Qt.AlignCenter); item.setIcon(QIcon(path)); self.list_widget.addItem(item)
        nb_photos = len(self.images_paths); self.status_bar.showMessage(f"Prêt — {nb_photos} photos chargées."); self.btn_slideshow.setEnabled(nb_photos > 0); self.btn_clear_all.setEnabled(nb_photos > 0)
    def sort_photos(self):
        mode = self.sort_combo.currentText()
        try:
            if "Nom (A-Z)" in mode: self.images_paths.sort()
            elif "Nom (Z-A)" in mode: self.images_paths.sort(reverse=True)
            elif "création" in mode: self.images_paths.sort(key=lambda x: os.path.getctime(x) if os.path.exists(x) else 0)
            elif "modif" in mode: self.images_paths.sort(key=lambda x: os.path.getmtime(x) if os.path.exists(x) else 0, reverse=True)
            elif "Aléatoire" in mode: random.shuffle(self.images_paths)
        except: pass
        self.refresh_list(); self.save_config()
    def lancer_diaporama(self):
        if self.images_paths:
            ms_duration = self.slider_duree.value() * 1000
            self.diapo = SlideshowWindow(self.images_paths, ms_duration, self.transition_combo.currentText(), self.transformations, self.screen_combo.currentData() or 0, {"version": self.cb_version.isChecked(), "filename": self.cb_filename.isChecked(), "counter": self.cb_counter.isChecked(), "time": self.cb_time.isChecked()})
            self.diapo.show()

if __name__ == "__main__":
    app = QApplication(sys.argv); window = MainWindow(); window.show(); sys.exit(app.exec())