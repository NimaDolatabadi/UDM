import sys
import os
import json
import logging
import threading
import fnmatch
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import requests

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLineEdit, QPushButton, QProgressBar, QFileDialog, 
                             QMessageBox, QLabel, QTabWidget, QListWidget, QStyle,
                             QToolBar, QTreeWidget, QTreeWidgetItem, QSplitter, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QInputDialog,
                             QDialog, QFormLayout, QDialogButtonBox, QComboBox, QSpinBox, 
                             QTimeEdit, QDateEdit, QMenu, QCheckBox, QScrollArea, QWidgetAction,
                             QSystemTrayIcon)
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, Qt, QMimeData, QSize, QTime, QDate
from PyQt6.QtGui import (QIcon, QAction, QPixmap, QPainter, 
                         QColor, QBrush, QPen, QDragEnterEvent, QDropEvent)
from PyQt6.QtWidgets import QSizePolicy

logging.basicConfig(filename='download_manager.log', level=logging.INFO)

DARK_STYLESHEET = """
QWidget { background-color: #2b2b2b; color: #e0e0e0; font-size: 13px; }
QToolBar { 
    background-color: #323232; 
    border-bottom: 1px solid #1a1a1a; 
    spacing: 8px; 
    padding: 4px; 
}
QToolButton {
    background-color: #3a3a3a;
    border: 1px solid #4f4f4f;
    border-radius: 5px;
    margin: 2px;
    padding: 4px;
}
QToolButton:hover {
    background-color: #4a4a4a;
    border: 1px solid #6c6c6c;
}
QToolButton:pressed {
    background-color: #252525;
    border: 1px solid #333333;
}
QTreeWidget, QTableWidget, QListWidget, QTabWidget::pane { background-color: #1e1e1e; border: 1px solid #444; }
QHeaderView::section { background-color: #333; padding: 4px; border: 1px solid #444; }
QLineEdit, QComboBox, QSpinBox, QTimeEdit, QDateEdit { background-color: #1e1e1e; border: 1px solid #555; padding: 4px; color: #e0e0e0; }
QComboBox, QTimeEdit, QDateEdit { min-width: 110px; }
QComboBox QAbstractItemView { min-width: 110px; }
QPushButton { background-color: #404040; border: 1px solid #555; padding: 6px; border-radius: 4px; }
QPushButton:hover { background-color: #505050; }
QProgressBar { border: 1px solid #555; text-align: center; }
QProgressBar::chunk { background-color: #0588bc; }
QDialog { background-color: #2b2b2b; }
"""

TRANSLATIONS = {
    "English": {
        "title": "UDM (Umbrella Download Manager) - Advanced Download Manager", "tab_dl": "Downloads", "tab_grabber": "Site Grabber",
        "tab_bulk": "Bulk Recursive", "tab_torrents": "Torrents", "btn_load_tor": "Load .torrent File", "btn_add_mag": "Add Magnet",
        "mag_ph": "Paste magnet link here...",
        "add_url": "Add URL", "resume": "Resume", "stop": "Stop", "stop_all": "Stop All",
        "delete": "Delete", "del_comp": "Delete Completed", "options": "Options", "grabber": "Grabber",
        "scheduler": "Scheduler",
        "btn_spider": "Start Web Spider", "filter_ph": "Filter files (e.g., zip, x64)", "url_ph": "Enter website URL to spider...",
        "btn_sel_all": "Select All", "btn_trans": "Transfer to Queue (Paused)",
        "q_queues": "Queues", "q_main": "Main Download Queue", "q_sync": "Main Sync Queue",
        "dl_headers": ["File Name", "Size", "Status", "Time Left", "Transfer Rate", "Description"],
        "tor_headers": ["Torrent Name", "Size", "Status", "Time Left", "Transfer Rate", "Description"],
        "grab_headers": ["Detected Download URL"],
        "ctx_sched": "Add to Schedule"
    },
    "Persian": {
        "title": "UDM (Umbrella Download Manager) - مدیریت دانلود پیشرفته", "tab_dl": "دانلودها", "tab_grabber": "استخراج سایت",
        "tab_bulk": "دانلود انبوه بازگشتی", "tab_torrents": "تورنت‌ها", "btn_load_tor": "بارگذاری فایل تورنت", "btn_add_mag": "افزودن مگنت",
        "mag_ph": "لینک مگنت را اینجا جای‌گذاری کنید...",
        "add_url": "افزودن لینک", "resume": "ادامه", "stop": "توقف", "stop_all": "توقف همه",
        "delete": "حذف", "del_comp": "حذف تکمیل‌شده‌ها", "options": "تنظیمات", "grabber": "استخراج",
        "scheduler": "زمان‌بند",
        "btn_spider": "شروع استخراج", "filter_ph": "فیلتر فایل‌ها...", "url_ph": "لینک سایت را وارد کنید...",
        "btn_sel_all": "انتخاب همه", "btn_trans": "انتقال به صف (توقف‌شده)",
        "q_queues": "صف‌ها", "q_main": "صف اصلی دانلود", "q_sync": "صف همگام‌سازی اصلی",
        "dl_headers": ["نام فایل", "حجم", "وضعیت", "زمان باقیمانده", "سرعت انتقال", "توضیحات"],
        "tor_headers": ["نام تورنت", "حجم", "وضعیت", "زمان باقیمانده", "سرعت انتقال", "توضیحات"],
        "grab_headers": ["لینک‌های شناسایی شده"],
        "ctx_sched": "افزودن به زمان‌بندی"
    },
    "Russian": {
        "title": "UDM (Umbrella Download Manager) - Расширенный менеджер загрузок", "tab_dl": "Загрузки", "tab_grabber": "Парсер сайтов",
        "tab_bulk": "Пакетная рекурсивная", "tab_torrents": "Торренты", "btn_load_tor": "Загрузить .torrent", "btn_add_mag": "Добавить Magnet",
        "mag_ph": "Вставьте magnet-ссылку...",
        "add_url": "Добавить URL", "resume": "Продолжить", "stop": "Стоп", "stop_all": "Остановить все",
        "delete": "Удалить", "del_comp": "Удалить завершенные", "options": "Настройки", "grabber": "Парсер",
        "scheduler": "Планировщик",
        "btn_spider": "Запустить парсер", "filter_ph": "Фильтр (напр. zip, x64)", "url_ph": "Введите URL сайта...",
        "btn_sel_all": "Выбрать все", "btn_trans": "В очередь (Пауза)",
        "q_queues": "Очереди", "q_main": "Основная очередь", "q_sync": "Очередь синхронизации",
        "dl_headers": ["Имя файла", "Размер", "Статус", "Осталось", "Скорость", "Описание"],
        "tor_headers": ["Имя торрента", "Размер", "Статус", "Осталось", "Скорость", "Описание"],
        "grab_headers": ["Найденные URL"],
        "ctx_sched": "Добавить в расписание"
    },
    "French": {
        "title": "UDM (Umbrella Download Manager) - Gestionnaire de téléchargement", "tab_dl": "Téléchargements", "tab_grabber": "Aspirateur",
        "tab_bulk": "Téléchargement en gros", "tab_torrents": "Torrents", "btn_load_tor": "Charger .torrent", "btn_add_mag": "Ajouter Magnet",
        "mag_ph": "Collez le lien magnet ici...",
        "add_url": "Ajouter URL", "resume": "Reprendre", "stop": "Arrêter", "stop_all": "Tout Arrêter",
        "delete": "Supprimer", "del_comp": "Supprimer terminés", "options": "Options", "grabber": "Aspirateur",
        "scheduler": "Planificateur",
        "btn_spider": "Démarrer l'Aspirateur", "filter_ph": "Filtrer (ex: zip, x64)", "url_ph": "Entrez l'URL du site...",
        "btn_sel_all": "Tout sélectionner", "btn_trans": "Transférer (En pause)",
        "q_queues": "Files d'attente", "q_main": "File principale", "q_sync": "File de synchronisation",
        "dl_headers": ["Nom du fichier", "Taille", "Statut", "Temps restant", "Vitesse", "Description"],
        "tor_headers": ["Nom du torrent", "Taille", "Statut", "Temps restant", "Vitesse", "Description"],
        "grab_headers": ["URL Détectée"],
        "ctx_sched": "Ajouter au planning"
    },
    "Italian": {
        "title": "UDM (Umbrella Download Manager) - Gestore Download Avanzato", "tab_dl": "Download", "tab_grabber": "Cattura Sito",
        "tab_bulk": "Download Ricorsivo", "tab_torrents": "Torrent", "btn_load_tor": "Carica .torrent", "btn_add_mag": "Aggiungi Magnet",
        "mag_ph": "Incolla il link magnet qui...",
        "add_url": "Aggiungi URL", "resume": "Riprendi", "stop": "Ferma", "stop_all": "Ferma Tutti",
        "delete": "Elimina", "del_comp": "Elimina completati", "options": "Opzioni", "grabber": "Cattura",
        "scheduler": "Pianificatore",
        "btn_spider": "Avvia Cattura", "filter_ph": "Filtra (es. zip, x64)", "url_ph": "Inserisci URL del sito...",
        "btn_sel_all": "Seleziona Tutto", "btn_trans": "Trasferisci in Coda (Pausa)",
        "q_queues": "Code", "q_main": "Coda Principale", "q_sync": "Coda di Sincronizzazione",
        "dl_headers": ["Nome File", "Dimensione", "Stato", "Tempo Rimanente", "Velocità", "Descrizione"],
        "tor_headers": ["Nome Torrent", "Dimensione", "Stato", "Tempo Rimanente", "Velocità", "Descrizione"],
        "grab_headers": ["URL Rilevato"],
        "ctx_sched": "Aggiungi alla Programmazione"
    }
}

SCHEDULE_COLORS = ["#ff4d4d", "#ffad33", "#2eb82e", "#3399ff", "#b366ff"]
RECURRENCE_OPTIONS = ["Every Day", "Even Days", "Odd Days"]

DEFAULT_CONFIG = {
    "language": "English",
    "proxy": "",
    "dns": "",
    "segments": 8,
    "start_with_os": False,
    "start_minimized": False,
    "close_to_tray": True,
    "clipboard_monitor": False,
    "sound_on_complete": False,
    "schedules": [
        {
            "name": "Default Schedule", "active": False, "max_dl": 2, 
            "start_time": "00:00", "end_time": "06:00", 
            "start_date": "2026-01-01", "end_date": "2026-12-31", 
            "recurrence": "Every Day", "color": SCHEDULE_COLORS[0], "is_default": True
        }
    ],
    "categories": {
        "Compressed": "zip, rar, gz, tar, 7z, bz2",
        "Documents": "pdf, doc, docx, txt, ppt, pptx, xls, xlsx, odt, rtf",
        "Music": "mp3, wav, flac, aac, ogg, m4a",
        "Programs/Windows": "exe, msi, bat, cmd",
        "Programs/Linux": "deb, rpm, sh, AppImage, run, bin",
        "Programs/Mac": "dmg, pkg",
        "Videos": "mp4, mkv, avi, mov, wmv, flv, webm",
        "Android": "apk, xapk, apks, obb",
        "Torrents": "torrent"
    }
}

class ConfigManager:
    def __init__(self, config_path="udm_config.json"):
        self.config_path = config_path
        self.config = self.load_config()

    def load_config(self):
        if not os.path.exists(self.config_path):
            self.save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG
        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)
                for k, v in DEFAULT_CONFIG.items():
                    if k not in data:
                        data[k] = v
                return data
        except Exception as e:
            logging.error(f"Config load error: {e}")
            return DEFAULT_CONFIG

    def save_config(self, config_data):
        self.config = config_data
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config_data, f, indent=4)
        except Exception as e:
            logging.error(f"Config save error: {e}")

    def get_category_path(self, filename):
        ext = os.path.splitext(filename)[1].lower().replace('.', '')
        base_dir = os.path.expanduser("~/Downloads/UDM")
        
        for category, extensions_str in self.config.get("categories", {}).items():
            ext_list = [e.strip().lower().replace('.', '') for e in extensions_str.split(',')]
            if ext in ext_list:
                path = os.path.join(base_dir, category)
                os.makedirs(path, exist_ok=True)
                return path
                
        path = os.path.join(base_dir, "Others")
        os.makedirs(path, exist_ok=True)
        return path

def set_system_startup(enable):
    if sys.platform == "darwin":
        plist_path = os.path.expanduser("~/Library/LaunchAgents/com.udm.manager.plist")
        if enable:
            exe_path = sys.executable
            script_path = os.path.abspath(sys.argv[0])
            plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.udm.manager</string>
    <key>ProgramArguments</key>
    <array>
        <string>{exe_path}</string>
        <string>{script_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
"""
            try:
                os.makedirs(os.path.dirname(plist_path), exist_ok=True)
                with open(plist_path, "w") as f:
                    f.write(plist_content)
            except Exception as e:
                logging.error(f"Failed to set startup plist: {e}")
        else:
            if os.path.exists(plist_path):
                try:
                    os.remove(plist_path)
                except Exception as e:
                    logging.error(f"Failed to remove startup plist: {e}")
    elif sys.platform.startswith("win"):
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            if enable:
                winreg.SetValueEx(key, "UDMManager", 0, winreg.REG_SZ, f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"')
            else:
                try:
                    winreg.DeleteValue(key, "UDMManager")
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            logging.error(f"Failed to set windows registry startup: {e}")

def create_queue_icon(color_name, file_count, has_clock=False):
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    color = QColor(color_name)
    painter.setBrush(QBrush(color))
    painter.setPen(QPen(Qt.GlobalColor.black, 1))
    
    for i in range(file_count):
        painter.drawRect(2 + (i * 6), 2 + (i * 6), 14, 18)
        
    if has_clock:
        painter.setBrush(QBrush(QColor("white")))
        painter.setPen(QPen(QColor("black"), 2))
        painter.drawEllipse(16, 16, 14, 14)
        painter.drawLine(23, 23, 23, 19)
        painter.drawLine(23, 23, 26, 23)
        
    painter.end()
    return QIcon(pixmap)

class PurePythonDownloadWorker(QThread):
    progress_signal = pyqtSignal(str, int, str, str) 
    finished_signal = pyqtSignal(str, bool, str) 

    def __init__(self, dl_id, url, save_path, segments=8, proxy=None):
        super().__init__()
        self.dl_id = dl_id
        self.url = url
        self.save_path = save_path
        self.segments = segments
        self.proxy = proxy
        self._is_paused = False
        self._is_cancelled = False

    def run(self):
        proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None
        headers = {"User-Agent": "Mozilla/5.0"}
        
        try:
            head = requests.head(self.url, headers=headers, proxies=proxies, allow_redirects=True, timeout=10)
            file_size = int(head.headers.get('content-length', 0))
            accept_ranges = head.headers.get('accept-ranges', 'none')
        except Exception:
            file_size = 0
            accept_ranges = 'none'

        if file_size == 0 or accept_ranges == 'none' or self.segments <= 1:
            self.download_single_thread(headers, proxies, file_size)
        else:
            self.download_multi_thread(headers, proxies, file_size)

    def download_single_thread(self, headers, proxies, file_size):
        try:
            resp = requests.get(self.url, headers=headers, proxies=proxies, stream=True, timeout=15)
            resp.raise_for_status()
            downloaded = 0
            
            with open(self.save_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if self._is_cancelled:
                        return
                    while self._is_paused:
                        self.msleep(100)
                        if self._is_cancelled:
                            return
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        pct = int((downloaded / file_size) * 100) if file_size > 0 else 0
                        self.progress_signal.emit(self.dl_id, pct, "Active", "Downloading")
                        
            self.finished_signal.emit(self.dl_id, True, "Completed")
        except Exception as e:
            self.finished_signal.emit(self.dl_id, False, str(e))

    def download_multi_thread(self, headers, proxies, file_size):
        part_size = file_size // self.segments
        threads = []
        temp_files = []

        def download_part(start, end, part_file):
            h = headers.copy()
            h['Range'] = f"bytes={start}-{end}"
            try:
                r = requests.get(self.url, headers=h, proxies=proxies, stream=True, timeout=15)
                with open(part_file, 'wb') as pf:
                    for chunk in r.iter_content(chunk_size=8192):
                        if self._is_cancelled:
                            return
                        while self._is_paused:
                            self.msleep(100)
                        if chunk:
                            pf.write(chunk)
            except Exception as e:
                logging.error(f"Segment error: {e}")

        try:
            for i in range(self.segments):
                start = i * part_size
                end = file_size - 1 if i == self.segments - 1 else (start + part_size - 1)
                part_file = f"{self.save_path}.part{i}"
                temp_files.append(part_file)
                
                t = threading.Thread(target=download_part, args=(start, end, part_file))
                threads.append(t)
                t.start()

            while any(t.is_alive() for t in threads):
                if self._is_cancelled:
                    return
                self.msleep(200)
                downloaded = sum(os.path.getsize(pf) for pf in temp_files if os.path.exists(pf))
                pct = int((downloaded / file_size) * 100) if file_size > 0 else 0
                self.progress_signal.emit(self.dl_id, pct, f"{self.segments} Segments", "Downloading")

            for t in threads:
                t.join()

            if self._is_cancelled:
                return

            with open(self.save_path, 'wb') as outfile:
                for pf in temp_files:
                    if os.path.exists(pf):
                        with open(pf, 'rb') as inf:
                            outfile.write(inf.read())
                        os.remove(pf)

            self.finished_signal.emit(self.dl_id, True, "Completed")
        except Exception as e:
            self.finished_signal.emit(self.dl_id, False, str(e))

    def pause(self):
        self._is_paused = True

    def resume(self):
        self._is_paused = False

    def cancel(self):
        self._is_cancelled = True

class BulkRecursiveSpiderThread(QThread):
    found_link = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished = pyqtSignal(int)

    def __init__(self, start_url, extensions):
        super().__init__()
        self.start_url = start_url
        self.extensions = [e.strip().lower().replace('.', '') for e in extensions if e.strip()]
        self._is_cancelled = False

    def run(self):
        visited = set()
        queue = [self.start_url]
        collected_links = set()
        
        parsed_base = urlparse(self.start_url)
        base_domain = parsed_base.netloc

        total_nodes = 1
        processed_nodes = 0

        while queue and not self._is_cancelled:
            current_url = queue.pop(0)
            if current_url in visited:
                continue
            visited.add(current_url)
            processed_nodes += 1

            progress_pct = int((processed_nodes / max(total_nodes, len(queue) + processed_nodes)) * 100)
            self.progress_signal.emit(min(progress_pct, 99))

            try:
                headers = {"User-Agent": "Mozilla/5.0"}
                resp = requests.get(current_url, headers=headers, timeout=8)
                if 'text/html' not in resp.headers.get('content-type', ''):
                    continue
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                for a in soup.find_all('a', href=True):
                    if self._is_cancelled:
                        break
                    href = a['href']
                    full_url = urljoin(current_url, href)
                    parsed_full = urlparse(full_url)
                    
                    if parsed_full.netloc != base_domain:
                        continue
                        
                    ext = os.path.splitext(parsed_full.path)[1].lower().replace('.', '')
                    
                    if ext in self.extensions:
                        if full_url not in collected_links:
                            collected_links.add(full_url)
                            self.found_link.emit(full_url)
                    elif not ext and full_url not in visited and full_url not in queue:
                        queue.append(full_url)
                        total_nodes += 1
            except Exception as e:
                logging.error(f"Bulk spider error at {current_url}: {e}")

        self.progress_signal.emit(100)
        self.finished.emit(len(collected_links))

    def cancel(self):
        self._is_cancelled = True

class SchedulerDialog(QDialog):
    def __init__(self, current_schedules, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Download Scheduler Management")
        
        self.layout = QVBoxLayout(self)
        self.sched_rows = []
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.container_widget = QWidget()
        self.container_layout = QVBoxLayout(self.container_widget)
        self.container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.container_widget)
        
        for sched in current_schedules:
            self.add_schedule_row(sched)
            
        self.layout.addWidget(scroll)
        
        btn_add = QPushButton("Add Schedule")
        btn_add.clicked.connect(lambda: self.add_schedule_row({
            "name": "New Schedule", "active": True, "max_dl": 2, 
            "start_time": "08:00", "end_time": "17:00", 
            "start_date": QDate.currentDate().toString("yyyy-MM-dd"), 
            "end_date": QDate.currentDate().addDays(7).toString("yyyy-MM-dd"), 
            "recurrence": "Every Day", "is_default": False
        }))
        self.layout.addWidget(btn_add)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        self.layout.addWidget(btn_box)
        
        self.resize(820, 320)

    def add_schedule_row(self, sched):
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        
        idx = len(self.sched_rows)
        color_code = SCHEDULE_COLORS[idx % len(SCHEDULE_COLORS)]
        
        color_lbl = QLabel("  ")
        color_lbl.setStyleSheet(f"background-color: {color_code}; border-radius: 4px;")
        color_lbl.setFixedSize(20, 20)
        
        active_cb = QCheckBox("Enable")
        active_cb.setChecked(sched.get("active", False))
        
        name_input = QLineEdit(sched["name"])
        name_input.setMinimumWidth(180)
        if sched.get("is_default", False):
            name_input.setReadOnly(True)
            
        max_dl_spin = QSpinBox()
        max_dl_spin.setRange(1, 20)
        max_dl_spin.setValue(sched["max_dl"])
        
        start_date = QDate.fromString(sched.get("start_date", "2026-01-01"), "yyyy-MM-dd")
        start_date_edit = QDateEdit()
        start_date_edit.setDate(start_date if start_date.isValid() else QDate.currentDate())
        start_date_edit.setCalendarPopup(True)
        
        end_date = QDate.fromString(sched.get("end_date", "2026-12-31"), "yyyy-MM-dd")
        end_date_edit = QDateEdit()
        end_date_edit.setDate(end_date if end_date.isValid() else QDate.currentDate().addDays(7))
        end_date_edit.setCalendarPopup(True)
        
        start_time = QTime.fromString(sched.get("start_time", "00:00"), "HH:mm")
        start_edit = QTimeEdit()
        start_edit.setTime(start_time if start_time.isValid() else QTime(0, 0))
        
        end_time = QTime.fromString(sched.get("end_time", "06:00"), "HH:mm")
        end_edit = QTimeEdit()
        end_edit.setTime(end_time if end_time.isValid() else QTime(6, 0))
        
        recur_cb = QComboBox()
        recur_cb.addItems(RECURRENCE_OPTIONS)
        current_recur = sched.get("recurrence", "Every Day")
        if current_recur not in RECURRENCE_OPTIONS:
            current_recur = "Every Day"
        recur_cb.setCurrentText(current_recur)
        
        row_layout.addWidget(color_lbl)
        row_layout.addWidget(active_cb)
        row_layout.addWidget(name_input)
        row_layout.addWidget(QLabel("Max:"))
        row_layout.addWidget(max_dl_spin)
        row_layout.addWidget(QLabel("From:"))
        row_layout.addWidget(start_date_edit)
        row_layout.addWidget(start_edit)
        row_layout.addWidget(QLabel("To:"))
        row_layout.addWidget(end_date_edit)
        row_layout.addWidget(end_edit)
        row_layout.addWidget(recur_cb)
        
        btn_del = QPushButton("Delete")
        if sched.get("is_default", False):
            btn_del.setEnabled(False)
        else:
            btn_del.clicked.connect(lambda: self.remove_schedule_row(row_widget))
            
        row_layout.addWidget(btn_del)
        
        self.container_layout.addWidget(row_widget)
        self.sched_rows.append({
            "widget": row_widget,
            "active": active_cb,
            "name": name_input,
            "max_dl": max_dl_spin,
            "start_date": start_date_edit,
            "end_date": end_date_edit,
            "start_time": start_edit,
            "end_time": end_edit,
            "recurrence": recur_cb,
            "is_default": sched.get("is_default", False),
            "color": color_code
        })
        
        self.adjustSize()

    def remove_schedule_row(self, row_widget):
        for item in self.sched_rows:
            if item["widget"] == row_widget:
                if item["is_default"]:
                    return
                row_widget.deleteLater()
                self.sched_rows.remove(item)
                self.adjustSize()
                break

    def get_updated_schedules(self):
        new_schedules = []
        for item in self.sched_rows:
            new_schedules.append({
                "name": item["name"].text().strip(),
                "active": item["active"].isChecked(),
                "max_dl": item["max_dl"].value(),
                "start_date": item["start_date"].date().toString("yyyy-MM-dd"),
                "end_date": item["end_date"].date().toString("yyyy-MM-dd"),
                "start_time": item["start_time"].time().toString("HH:mm"),
                "end_time": item["end_time"].time().toString("HH:mm"),
                "recurrence": item["recurrence"].currentText(),
                "color": item["color"],
                "is_default": item["is_default"]
            })
        return new_schedules

class OptionsDialog(QDialog):
    def __init__(self, current_config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("UDM Options")
        self.resize(550, 450)
        
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        
        general_tab = QWidget()
        general_layout = QFormLayout()
        self.lang_cb = QComboBox()
        self.lang_cb.setMinimumWidth(150) 
        self.lang_cb.addItems(["English", "Persian", "Russian", "French", "Italian"])
        self.lang_cb.setCurrentText(current_config.get("language", "English"))
        
        self.start_os_cb = QCheckBox("Open the app when system starts")
        self.start_os_cb.setChecked(current_config.get("start_with_os", False))
        
        self.start_min_cb = QCheckBox("Open as minimized")
        self.start_min_cb.setChecked(current_config.get("start_minimized", False))
        
        self.close_tray_cb = QCheckBox("Send app to tray when closing the app")
        self.close_tray_cb.setChecked(current_config.get("close_to_tray", True))

        self.clip_cb = QCheckBox("Enable Clipboard Monitor")
        self.clip_cb.setChecked(current_config.get("clipboard_monitor", False))

        self.sound_cb = QCheckBox("Play sound/notification on download complete")
        self.sound_cb.setChecked(current_config.get("sound_on_complete", False))

        general_layout.addRow("Interface Language:", self.lang_cb)
        general_layout.addRow(self.start_os_cb)
        general_layout.addRow(self.start_min_cb)
        general_layout.addRow(self.close_tray_cb)
        general_layout.addRow(self.clip_cb)
        general_layout.addRow(self.sound_cb)
        general_tab.setLayout(general_layout)
        
        network_tab = QWidget()
        network_layout = QFormLayout()
        self.proxy_input = QLineEdit(current_config.get("proxy", ""))
        self.proxy_input.setPlaceholderText("http://user:password@proxy.server:port")
        self.dns_input = QLineEdit(current_config.get("dns", ""))
        self.dns_input.setPlaceholderText("8.8.8.8, 1.1.1.1")
        self.segment_spin = QSpinBox()
        self.segment_spin.setRange(1, 64)
        self.segment_spin.setValue(int(current_config.get("segments", 8)))
        network_layout.addRow("Custom Proxy:", self.proxy_input)
        network_layout.addRow("Custom DNS:", self.dns_input)
        network_layout.addRow("Max Segments per File:", self.segment_spin)
        network_tab.setLayout(network_layout)
        
        cat_tab = QWidget()
        cat_layout = QVBoxLayout()
        self.cat_table = QTableWidget(0, 2)
        self.cat_table.setHorizontalHeaderLabels(["Category Path", "Extensions (comma separated)"])
        self.cat_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        categories = current_config.get("categories", DEFAULT_CONFIG["categories"])
        for cat, exts in categories.items():
            self.add_cat_row(cat, exts)
            
        btn_layout = QHBoxLayout()
        btn_add = QPushButton("Add Category")
        btn_add.clicked.connect(lambda: self.add_cat_row("New Category", "ext1, ext2"))
        btn_rem = QPushButton("Remove Selected")
        btn_rem.clicked.connect(self.remove_cat_row)
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_rem)
        
        cat_layout.addWidget(self.cat_table)
        cat_layout.addLayout(btn_layout)
        cat_tab.setLayout(cat_layout)
        
        tabs.addTab(general_tab, "General")
        tabs.addTab(network_tab, "Network")
        tabs.addTab(cat_tab, "Categories")
        layout.addWidget(tabs)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def add_cat_row(self, category, extensions):
        row = self.cat_table.rowCount()
        self.cat_table.insertRow(row)
        self.cat_table.setItem(row, 0, QTableWidgetItem(category))
        self.cat_table.setItem(row, 1, QTableWidgetItem(extensions))

    def remove_cat_row(self):
        selected = self.cat_table.selectedItems()
        if selected:
            row = selected[0].row()
            self.cat_table.removeRow(row)

    def get_updated_config(self):
        updated_cats = {}
        for row in range(self.cat_table.rowCount()):
            cat_item = self.cat_table.item(row, 0)
            ext_item = self.cat_table.item(row, 1)
            if cat_item and ext_item:
                c_text = cat_item.text().strip()
                if c_text:
                    updated_cats[c_text] = ext_item.text().strip()
                
        return {
            "language": self.lang_cb.currentText(),
            "start_with_os": self.start_os_cb.isChecked(),
            "start_minimized": self.start_min_cb.isChecked(),
            "close_to_tray": self.close_tray_cb.isChecked(),
            "clipboard_monitor": self.clip_cb.isChecked(),
            "sound_on_complete": self.sound_cb.isChecked(),
            "proxy": self.proxy_input.text().strip(),
            "dns": self.dns_input.text().strip(),
            "segments": self.segment_spin.value(),
            "categories": updated_cats
        }

class SpiderThread(QThread):
    found_link = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, start_url, extract_images, extract_videos):
        super().__init__()
        self.start_url = start_url
        self.extract_images = extract_images
        self.extract_videos = extract_videos

    def run(self):
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(self.start_url, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            if self.extract_videos:
                for video in soup.find_all('video'):
                    src = video.get('src') or (video.find('source') and video.find('source').get('src'))
                    if src: self.found_link.emit(urljoin(self.start_url, src))
            
            if self.extract_images:
                for img in soup.find_all('img', src=True):
                    self.found_link.emit(urljoin(self.start_url, img['src']))
                    
            for a in soup.find_all('a', href=True):
                href = a['href']
                if href.endswith(('.zip', '.rar', '.exe', '.pdf', '.mp4', '.mp3', '.dmg', '.pkg', '.apk', '.sh')):
                    self.found_link.emit(urljoin(self.start_url, href))
                    
        except Exception as e:
            logging.error(f"Spider error: {e}")
        self.finished.emit()

class UDMManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config_mgr = ConfigManager()
        self.active_workers = {}
        self.bulk_spider = None
        self.tray_icon = None
        
        set_system_startup(self.config_mgr.config.get("start_with_os", False))
        
        self.initUI()
        self.setAcceptDrops(True)
        self.retranslate_ui()

        if self.config_mgr.config.get("start_minimized", False):
            QTimer.singleShot(100, self.hide)

        if self.config_mgr.config.get("clipboard_monitor", False):
            self.setup_clipboard_monitor()

    def setup_clipboard_monitor(self):
        self.clipboard = QApplication.clipboard()
        self.clipboard.dataChanged.connect(self.on_clipboard_change)
        self.last_clipboard_text = ""

    def on_clipboard_change(self):
        if not self.config_mgr.config.get("clipboard_monitor", False):
            return
        text = self.clipboard.text().strip()
        if not text or text == self.last_clipboard_text or not text.startswith("http"):
            return
            
        self.last_clipboard_text = text
        extensions = (".zip", ".rar", ".mp4", ".mp3", ".pdf", ".exe", ".dmg", ".pkg", ".iso", ".mkv", ".7z", ".gz", ".tar")
        parsed = urlparse(text)
        
        if parsed.path.lower().endswith(extensions):
            self.clipboard.blockSignals(True) 
            reply = QMessageBox.question(self, "Download Detected", 
                                         f"Detected a file link in clipboard:\n{text}\n\nAdd to downloads?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.add_to_downloads(text)
            self.clipboard.blockSignals(False)

    def initUI(self):
        self.resize(1000, 650)
        self.setStyleSheet(DARK_STYLESHEET)
        
        if os.path.exists("logo.png"):
            app_icon = QIcon("logo.png")
            self.setWindowIcon(app_icon)
            QApplication.setWindowIcon(app_icon)
            
            if QSystemTrayIcon.isSystemTrayAvailable():
                self.tray_icon = QSystemTrayIcon(app_icon, self)
                tray_menu = QMenu()
                
                show_action = QAction("Show / Hide", self)
                show_action.triggered.connect(self.toggle_window_visibility)
                tray_menu.addAction(show_action)
                
                quit_action = QAction("Quit", self)
                quit_action.triggered.connect(self.quit_app)
                tray_menu.addAction(quit_action)
                
                self.tray_icon.setContextMenu(tray_menu)
                self.tray_icon.activated.connect(self.on_tray_icon_activated)
                if self.config_mgr.config.get("close_to_tray", True):
                    self.tray_icon.show()

        self.create_toolbar()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(splitter)

        self.queue_tree = QTreeWidget()
        self.queue_tree.setHeaderHidden(True)
        self.queue_tree.setMinimumWidth(200)
        self.setup_queues()
        splitter.addWidget(self.queue_tree)

        self.tabs = QTabWidget()
        self.setup_downloads_tab()
        self.setup_torrents_tab()
        self.setup_grabber_tab()
        self.setup_bulk_tab()
        splitter.addWidget(self.tabs)
        
        splitter.setSizes([200, 800])

    def toggle_window_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_window_visibility()

    def closeEvent(self, event):
        close_to_tray = self.config_mgr.config.get("close_to_tray", True)
        if close_to_tray and self.tray_icon and self.tray_icon.isVisible():
            self.hide()
            event.ignore()
        else:
            if self.tray_icon:
                self.tray_icon.hide()
            event.accept()
            QApplication.quit()

    def quit_app(self):
        if self.tray_icon:
            self.tray_icon.hide()
        QApplication.quit()

    def create_toolbar(self):
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setIconSize(QSize(24, 24))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.addToolBar(self.toolbar)

        style = self.style()
        self.act_add = QAction(style.standardIcon(QStyle.StandardPixmap.SP_FileIcon), "", self)
        self.act_resume = QAction(style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay), "", self)
        self.act_stop = QAction(style.standardIcon(QStyle.StandardPixmap.SP_MediaPause), "", self)
        self.act_stop_all = QAction(style.standardIcon(QStyle.StandardPixmap.SP_MediaStop), "", self)
        self.act_delete = QAction(style.standardIcon(QStyle.StandardPixmap.SP_TrashIcon), "", self)
        self.act_del_comp = QAction(style.standardIcon(QStyle.StandardPixmap.SP_DialogDiscardButton), "", self)
        self.act_sched = QAction(style.standardIcon(QStyle.StandardPixmap.SP_DriveNetIcon), "", self)
        self.act_opts = QAction(style.standardIcon(QStyle.StandardPixmap.SP_ComputerIcon), "", self)
        self.act_grabber = QAction(style.standardIcon(QStyle.StandardPixmap.SP_BrowserReload), "", self)

        self.toolbar.addActions([self.act_add, self.act_resume, self.act_stop, self.act_stop_all, self.act_delete, self.act_del_comp])
        self.toolbar.addSeparator()
        self.toolbar.addActions([self.act_sched, self.act_opts, self.act_grabber])

        self.act_add.triggered.connect(self.prompt_add_url)
        self.act_resume.triggered.connect(self.resume_selected)
        self.act_stop.triggered.connect(self.pause_selected)
        self.act_stop_all.triggered.connect(self.stop_all)
        self.act_delete.triggered.connect(self.delete_selected)
        self.act_del_comp.triggered.connect(self.delete_completed)
        self.act_sched.triggered.connect(self.show_scheduler)
        self.act_grabber.triggered.connect(lambda: self.tabs.setCurrentIndex(2)) 
        self.act_opts.triggered.connect(self.show_options)

    def setup_queues(self):
        self.root_queues = QTreeWidgetItem(self.queue_tree, [""])
        self.main_q = QTreeWidgetItem(self.root_queues, [""])
        self.main_q.setIcon(0, create_queue_icon("yellow", 3))
        self.main_sync = QTreeWidgetItem(self.root_queues, [""])
        self.main_sync.setIcon(0, create_queue_icon("green", 3))
        self.root_queues.setExpanded(True)

    def setup_downloads_tab(self):
        self.tab_dl = QWidget()
        layout = QVBoxLayout()
        self.dl_table = QTableWidget(0, 6)
        self.dl_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.dl_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.dl_table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.dl_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.dl_table.customContextMenuRequested.connect(self.show_download_context_menu)
        
        layout.addWidget(self.dl_table)
        self.tab_dl.setLayout(layout)
        self.tabs.addTab(self.tab_dl, "")

    def setup_torrents_tab(self):
        self.tab_torrents = QWidget()
        layout = QVBoxLayout()
        
        control_layout = QHBoxLayout()
        self.magnet_input = QLineEdit()
        self.btn_add_magnet = QPushButton()
        self.btn_add_magnet.clicked.connect(self.add_magnet_link)
        
        self.btn_load_torrent = QPushButton()
        self.btn_load_torrent.clicked.connect(self.prompt_load_torrent_file)
        
        control_layout.addWidget(self.magnet_input)
        control_layout.addWidget(self.btn_add_magnet)
        control_layout.addWidget(self.btn_load_torrent)
        
        self.torrent_table = QTableWidget(0, 6)
        self.torrent_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.torrent_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.torrent_table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        
        layout.addLayout(control_layout)
        layout.addWidget(self.torrent_table)
        self.tab_torrents.setLayout(layout)
        self.tabs.addTab(self.tab_torrents, "")

    def setup_grabber_tab(self):
        self.tab_grabber = QWidget()
        layout = QVBoxLayout()
        
        input_layout = QHBoxLayout()
        self.grab_url = QLineEdit()
        self.btn_grab = QPushButton()
        self.btn_grab.clicked.connect(self.start_grabber)
        input_layout.addWidget(self.grab_url)
        input_layout.addWidget(self.btn_grab)
        
        filter_layout = QHBoxLayout()
        self.grab_filter = QLineEdit()
        self.grab_filter.textChanged.connect(self.apply_grab_filter)
        self.lbl_filter = QLabel("Filter:")
        filter_layout.addWidget(self.lbl_filter)
        filter_layout.addWidget(self.grab_filter)
        
        action_layout = QHBoxLayout()
        self.btn_select_all = QPushButton()
        self.btn_select_all.clicked.connect(self.grabber_select_all)
        self.btn_transfer = QPushButton()
        self.btn_transfer.clicked.connect(self.grabber_transfer)
        
        action_layout.addWidget(self.btn_select_all)
        action_layout.addWidget(self.btn_transfer)
        
        self.grab_results = QTableWidget(0, 1)
        self.grab_results.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.grab_results.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.grab_results.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        
        layout.addLayout(input_layout)
        layout.addLayout(filter_layout)
        layout.addLayout(action_layout)
        layout.addWidget(self.grab_results)
        self.tab_grabber.setLayout(layout)
        self.tabs.addTab(self.tab_grabber, "")

    def setup_bulk_tab(self):
        self.tab_bulk = QWidget()
        layout = QVBoxLayout()
        
        form_layout = QFormLayout()
        self.bulk_url_input = QLineEdit()
        self.bulk_url_input.setPlaceholderText("https://example.com/folder/")
        
        self.bulk_ext_input = QLineEdit()
        self.bulk_ext_input.setPlaceholderText("zip, exe, pdf (comma separated)")
        
        form_layout.addRow("Base URL:", self.bulk_url_input)
        form_layout.addRow("Extensions:", self.bulk_ext_input)
        
        btn_layout = QHBoxLayout()
        self.btn_bulk_start = QPushButton("Start Bulk Recursive Download")
        self.btn_bulk_start.clicked.connect(self.start_bulk_download)
        
        self.btn_bulk_stop = QPushButton("Stop")
        self.btn_bulk_stop.setEnabled(False)
        self.btn_bulk_stop.clicked.connect(self.stop_bulk_download)
        
        btn_layout.addWidget(self.btn_bulk_start)
        btn_layout.addWidget(self.btn_bulk_stop)

        self.bulk_progress = QProgressBar()
        self.bulk_progress.setValue(0)
        
        self.bulk_results_table = QTableWidget(0, 1)
        self.bulk_results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.bulk_results_table.setHorizontalHeaderLabels(["Discovered Recursive URLs"])
        
        btn_bulk_queue = QPushButton("Transfer All to Queue (Paused)")
        btn_bulk_queue.clicked.connect(self.bulk_transfer_to_queue)
        
        layout.addLayout(form_layout)
        layout.addLayout(btn_layout)
        layout.addWidget(self.bulk_progress)
        layout.addWidget(self.bulk_results_table)
        layout.addWidget(btn_bulk_queue)
        
        self.tab_bulk.setLayout(layout)
        self.tabs.addTab(self.tab_bulk, "Bulk Recursive")

    def start_bulk_download(self):
        url = self.bulk_url_input.text().strip()
        exts_text = self.bulk_ext_input.text().strip()
        if not url or not exts_text:
            QMessageBox.warning(self, "Input Error", "Please provide both a Base URL and extensions.")
            return
            
        extensions = exts_text.split(',')
        self.bulk_results_table.setRowCount(0)
        self.bulk_progress.setValue(0)
        self.btn_bulk_start.setEnabled(False)
        self.btn_bulk_stop.setEnabled(True)
        
        self.bulk_spider = BulkRecursiveSpiderThread(url, extensions)
        self.bulk_spider.found_link.connect(self.on_bulk_link_found)
        self.bulk_spider.progress_signal.connect(self.bulk_progress.setValue)
        self.bulk_spider.finished.connect(self.on_bulk_finished)
        self.bulk_spider.start()

    def stop_bulk_download(self):
        if self.bulk_spider and self.bulk_spider.isRunning():
            self.bulk_spider.cancel()
            self.btn_bulk_stop.setEnabled(False)

    def on_bulk_link_found(self, link):
        row = self.bulk_results_table.rowCount()
        self.bulk_results_table.insertRow(row)
        item = QTableWidgetItem(link)
        item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        item.setCheckState(Qt.CheckState.Checked)
        self.bulk_results_table.setItem(row, 0, item)

    def on_bulk_finished(self, total):
        self.btn_bulk_start.setEnabled(True)
        self.btn_bulk_stop.setEnabled(False)
        self.bulk_progress.setValue(100)
        QMessageBox.information(self, "Bulk Scan Complete", f"Recursively discovered {total} matching files.")

    def bulk_transfer_to_queue(self):
        transferred = 0
        for row in range(self.bulk_results_table.rowCount()):
            item = self.bulk_results_table.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                self.add_to_downloads(item.text(), start_paused=True)
                transferred += 1
        if transferred > 0:
            QMessageBox.information(self, "Transferred", f"Transferred {transferred} recursive items to the download queue (Paused).")
        else:
            QMessageBox.warning(self, "Warning", "No checked items found to transfer.")

    def retranslate_ui(self):
        lang = self.config_mgr.config.get("language", "English")
        t = TRANSLATIONS.get(lang, TRANSLATIONS["English"])
        
        self.setWindowTitle(t["title"])
        self.act_add.setText(t["add_url"])
        self.act_resume.setText(t["resume"])
        self.act_stop.setText(t["stop"])
        self.act_stop_all.setText(t["stop_all"])
        self.act_delete.setText(t["delete"])
        self.act_del_comp.setText(t["del_comp"])
        self.act_sched.setText(t["scheduler"])
        self.act_opts.setText(t["options"])
        self.act_grabber.setText(t["grabber"])
        
        self.root_queues.setText(0, t["q_queues"])
        self.main_q.setText(0, t["q_main"])
        self.main_sync.setText(0, t["q_sync"])
        
        self.tabs.setTabText(0, t["tab_dl"])
        self.tabs.setTabText(1, t["tab_torrents"])
        self.tabs.setTabText(2, t["tab_grabber"])
        self.tabs.setTabText(3, t["tab_bulk"])
        
        self.dl_table.setHorizontalHeaderLabels(t["dl_headers"])
        self.torrent_table.setHorizontalHeaderLabels(t["tor_headers"])
        self.grab_results.setHorizontalHeaderLabels(t["grab_headers"])
        
        self.btn_add_magnet.setText(t["btn_add_mag"])
        self.btn_load_torrent.setText(t["btn_load_tor"])
        self.magnet_input.setPlaceholderText(t["mag_ph"])
        
        self.btn_grab.setText(t["btn_spider"])
        self.grab_url.setPlaceholderText(t["url_ph"])
        self.grab_filter.setPlaceholderText(t["filter_ph"])
        
        self.btn_select_all.setText(t["btn_sel_all"])
        self.btn_transfer.setText(t["btn_trans"])
        
        if lang == "Persian":
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        else:
            self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

    def prompt_add_url(self):
        url, ok = QInputDialog.getText(self, "Add URL", "Enter URL:")
        if ok and url:
            self.add_to_downloads(url)

    def add_to_downloads(self, url, start_paused=False, schedule_idx=None):
        url = url.strip()
        fname = os.path.basename(urlparse(url).path) or "downloaded_file"
        target_dir = self.config_mgr.get_category_path(fname)
        save_path = os.path.join(target_dir, fname)
        
        row = self.dl_table.rowCount()
        self.dl_table.insertRow(row)
        
        dl_id = f"dl_{row}_{int(os.urandom(2).hex(), 16)}"
        name_item = QTableWidgetItem(fname)
        name_item.setData(Qt.ItemDataRole.UserRole, dl_id)
        
        if schedule_idx is not None and 0 <= schedule_idx < len(SCHEDULE_COLORS):
            name_item.setBackground(QBrush(QColor(SCHEDULE_COLORS[schedule_idx])))
            name_item.setData(Qt.ItemDataRole.UserRole + 1, schedule_idx)
        
        self.dl_table.setItem(row, 0, name_item)
        self.dl_table.setItem(row, 1, QTableWidgetItem("0%"))
        status = "Paused" if start_paused else "Downloading"
        self.dl_table.setItem(row, 2, QTableWidgetItem(status))
        self.dl_table.setItem(row, 5, QTableWidgetItem(f"Saved to: {target_dir}"))
        
        if not start_paused:
            self.start_worker(dl_id, url, save_path, row)

    def start_worker(self, dl_id, url, save_path, row):
        segments = int(self.config_mgr.config.get("segments", 8))
        proxy = self.config_mgr.config.get("proxy", "").strip() or None
        
        worker = PurePythonDownloadWorker(dl_id, url, save_path, segments=segments, proxy=proxy)
        worker.progress_signal.connect(self.on_worker_progress)
        worker.finished_signal.connect(self.on_worker_finished)
        self.active_workers[dl_id] = (worker, row)
        worker.start()

    def on_worker_progress(self, dl_id, pct, speed, status):
        if dl_id in self.active_workers:
            worker, row = self.active_workers[dl_id]
            self.dl_table.setItem(row, 1, QTableWidgetItem(f"{pct}%"))
            self.dl_table.setItem(row, 2, QTableWidgetItem(status))
            self.dl_table.setItem(row, 4, QTableWidgetItem(speed))

    def on_worker_finished(self, dl_id, success, message):
        if dl_id in self.active_workers:
            worker, row = self.active_workers[dl_id]
            st = "Completed" if success else f"Failed: {message}"
            self.dl_table.setItem(row, 2, QTableWidgetItem(st))
            
            if success and self.config_mgr.config.get("sound_on_complete", False):
                if self.tray_icon:
                    self.tray_icon.showMessage("UDM Download Complete", f"Successfully finished: {self.dl_table.item(row, 0).text()}", QSystemTrayIcon.MessageIcon.Information, 3000)

            del self.active_workers[dl_id]

    def show_scheduler(self):
        schedules = self.config_mgr.config.get("schedules", DEFAULT_CONFIG["schedules"])
        dialog = SchedulerDialog(schedules, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_scheds = dialog.get_updated_schedules()
            self.config_mgr.config["schedules"] = new_scheds
            self.config_mgr.save_config(self.config_mgr.config)
            QMessageBox.information(self, "Scheduler Updated", "Schedules saved successfully.")

    def show_download_context_menu(self, pos):
        menu = QMenu(self)
        lang = self.config_mgr.config.get("language", "English")
        t = TRANSLATIONS.get(lang, TRANSLATIONS["English"])
        
        sched_menu = menu.addMenu(t["ctx_sched"])
        schedules = self.config_mgr.config.get("schedules", DEFAULT_CONFIG["schedules"])
        
        for i, sched in enumerate(schedules):
            act = QAction(f"{sched['name']} ({sched.get('start_time', '00:00')} - {sched.get('end_time', '06:00')})", self)
            act.triggered.connect(lambda checked, idx=i: self.assign_schedule_to_selected(idx))
            sched_menu.addAction(act)
            
        menu.exec(self.dl_table.viewport().mapToGlobal(pos))

    def assign_schedule_to_selected(self, sched_idx):
        for dl_id, row, table in self.get_selected_rows_and_ids():
            item = table.item(row, 0)
            if item:
                item.setBackground(QBrush(QColor(SCHEDULE_COLORS[sched_idx % len(SCHEDULE_COLORS)])))
                item.setData(Qt.ItemDataRole.UserRole + 1, sched_idx)

    def add_magnet_link(self):
        QMessageBox.information(self, "Torrent Info", "Native torrent/magnet downloading requires libtorrent or external client support.")

    def prompt_load_torrent_file(self):
        QMessageBox.information(self, "Torrent Info", "Native torrent/magnet downloading requires libtorrent or external client support.")

    def get_active_table(self):
        idx = self.tabs.currentIndex()
        if idx == 0:
            return self.dl_table
        elif idx == 1:
            return self.torrent_table
        return None

    def get_selected_rows_and_ids(self):
        table = self.get_active_table()
        if not table:
            return []
        
        selected_indexes = table.selectionModel().selectedRows()
        results = []
        for index in selected_indexes:
            row = index.row()
            dl_id = table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            results.append((dl_id, row, table))
        return results

    def pause_selected(self):
        for dl_id, row, table in self.get_selected_rows_and_ids():
            if dl_id and dl_id in self.active_workers:
                worker, _ = self.active_workers[dl_id]
                worker.pause()
            table.setItem(row, 2, QTableWidgetItem("Paused"))

    def resume_selected(self):
        for dl_id, row, table in self.get_selected_rows_and_ids():
            if dl_id and dl_id in self.active_workers:
                worker, _ = self.active_workers[dl_id]
                worker.resume()
                table.setItem(row, 2, QTableWidgetItem("Downloading"))

    def stop_all(self):
        for dl_id, (worker, row) in self.active_workers.items():
            worker.pause()
            self.dl_table.setItem(row, 2, QTableWidgetItem("Paused"))

    def delete_selected(self):
        for dl_id, row, table in self.get_selected_rows_and_ids():
            if dl_id and dl_id in self.active_workers:
                worker, _ = self.active_workers[dl_id]
                worker.cancel()
                del self.active_workers[dl_id]
            table.removeRow(row)
            
    def delete_completed(self):
        for table in [self.dl_table, self.torrent_table]:
            rows_to_delete = []
            for row in range(table.rowCount()):
                status_item = table.item(row, 2)
                if status_item and status_item.text() == "Completed":
                    rows_to_delete.append(row)
            for row in reversed(rows_to_delete):
                table.removeRow(row)

    def start_grabber(self):
        url = self.grab_url.text().strip()
        if not url: return
        self.grab_results.setRowCount(0)
        self.btn_grab.setEnabled(False)
        
        self.spider = SpiderThread(url, extract_images=True, extract_videos=True)
        self.spider.found_link.connect(self.on_spider_link)
        self.spider.finished.connect(lambda: self.btn_grab.setEnabled(True))
        self.spider.start()

    def on_spider_link(self, link):
        row = self.grab_results.rowCount()
        self.grab_results.insertRow(row)
        
        item = QTableWidgetItem(link)
        item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        item.setCheckState(Qt.CheckState.Unchecked)
        
        self.grab_results.setItem(row, 0, item)
        self.apply_grab_filter()

    def apply_grab_filter(self):
        filter_text = self.grab_filter.text().strip().lower()
        
        for row in range(self.grab_results.rowCount()):
            item = self.grab_results.item(row, 0)
            if item:
                link = item.text().lower()
                if not filter_text or filter_text in link:
                    self.grab_results.setRowHidden(row, False)
                else:
                    self.grab_results.setRowHidden(row, True)

    def grabber_select_all(self):
        all_checked = True
        for row in range(self.grab_results.rowCount()):
            if not self.grab_results.isRowHidden(row):
                item = self.grab_results.item(row, 0)
                if item and item.checkState() == Qt.CheckState.Unchecked:
                    all_checked = False
                    break
                    
        new_state = Qt.CheckState.Unchecked if all_checked else Qt.CheckState.Checked
        
        for row in range(self.grab_results.rowCount()):
            if not self.grab_results.isRowHidden(row):
                item = self.grab_results.item(row, 0)
                if item:
                    item.setCheckState(new_state)

    def grabber_transfer(self):
        transferred = 0
        for row in range(self.grab_results.rowCount()):
            item = self.grab_results.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                url = item.text()
                self.add_to_downloads(url, start_paused=True)
                item.setCheckState(Qt.CheckState.Unchecked)
                transferred += 1
                
        if transferred > 0:
            QMessageBox.information(self, "Transferred", f"Transferred {transferred} items to the download queue (Paused).")
        else:
            QMessageBox.warning(self, "Transfer Failed", "No links were selected.")

    def show_options(self):
        dialog = OptionsDialog(self.config_mgr.config, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_config = dialog.get_updated_config()
            self.config_mgr.save_config(new_config)
            
            set_system_startup(new_config.get("start_with_os", False))
            
            if new_config.get("close_to_tray", True):
                if self.tray_icon:
                    self.tray_icon.show()
            else:
                if self.tray_icon:
                    self.tray_icon.hide()

            if new_config.get("clipboard_monitor", False) and not hasattr(self, "clipboard"):
                self.setup_clipboard_monitor()
                
            self.retranslate_ui()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasText():
            text = event.mimeData().text().strip()
            if text.startswith("http"):
                self.add_to_downloads(text)
            event.acceptProposedAction()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('macOS')
    app.setQuitOnLastWindowClosed(True)
    window = UDMManager()
    window.show()
    sys.exit(app.exec())