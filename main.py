import sys
import threading
import os
import time
import shutil
import json
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QSystemTrayIcon, QMenu, QListWidget, QListWidgetItem, QPushButton, QHBoxLayout, QLabel, QDialog, QLineEdit, QFormLayout
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QSize, QTimer, QStandardPaths
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QKeySequence
from pynput import keyboard

# Define app metadata for QStandardPaths
APP_NAME = "DittoKiller"
ORG_NAME = "SaumonDeluxe"

# Default Config
DEFAULT_CONFIG = {
    "hotkey": "<ctrl>+<alt>+<shift>+v",
    "retention_days": 7
}

class ConfigManager:
    def __init__(self, data_dir):
        self.config_file = os.path.join(data_dir, "config.json")
        self.config = DEFAULT_CONFIG.copy()
        self.load_config()

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.config.update(data)
            except Exception as e:
                print(f"Error loading config: {e}")

    def save_config(self):
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, key):
        return self.config.get(key, DEFAULT_CONFIG.get(key))

    def set(self, key, value):
        self.config[key] = value
        self.save_config()

class SignalHandler(QObject):
    toggle_visibility = pyqtSignal()
    quit_app = pyqtSignal()
    update_clipboard = pyqtSignal(dict)
    restart_hotkey = pyqtSignal()

class SettingsDialog(QDialog):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("Settings")
        self.setFixedSize(300, 150)
        self.setStyleSheet("background-color: #2e2e2e; color: white;")
        
        layout = QVBoxLayout()
        
        form_layout = QFormLayout()
        
        self.hotkey_input = QLineEdit()
        self.hotkey_input.setText(self.config_manager.get("hotkey"))
        self.hotkey_input.setPlaceholderText("e.g. <ctrl>+<alt>+v")
        self.hotkey_input.setStyleSheet("background-color: #1e1e1e; border: 1px solid #555; padding: 5px;")
        
        form_layout.addRow("Global Hotkey:", self.hotkey_input)
        
        layout.addLayout(form_layout)
        
        save_btn = QPushButton("Save && Restart Hotkey")
        save_btn.setStyleSheet("background-color: #007acc; padding: 8px; border: none; border-radius: 4px;")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)
        
        self.setLayout(layout)

    def save_settings(self):
        new_hotkey = self.hotkey_input.text()
        self.config_manager.set("hotkey", new_hotkey)
        signal_handler.restart_hotkey.emit()
        self.accept()

class OverlayWindow(QWidget):
    def __init__(self, data_dir, config_manager):
        super().__init__()
        self.data_dir = data_dir
        self.config_manager = config_manager
        self.history = []
        self.load_history()
        self.initUI()
        
        # Timer for auto-cleanup
        self.cleanup_timer = QTimer(self)
        self.cleanup_timer.timeout.connect(self.cleanup_items)
        self.cleanup_timer.start(10000) # Check every 10 seconds

    def initUI(self):
        # Window flags for frameless and always on top
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Set size and position (center of screen, small)
        self.resize(400, 500)
        screen_geometry = QApplication.primaryScreen().geometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)

        # Styling
        self.setStyleSheet("background-color: rgba(0, 0, 0, 200); border-radius: 10px;")

        # Layout and content
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header with Settings button
        header_layout = QHBoxLayout()
        header_layout.addStretch()
        
        settings_btn = QPushButton("⚙") # Gear icon
        settings_btn.setFixedSize(30, 30)
        settings_btn.setStyleSheet("background-color: transparent; color: white; font-size: 18px; border: none;")
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.clicked.connect(self.open_settings)
        header_layout.addWidget(settings_btn)
        
        layout.addLayout(header_layout)
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: rgba(46, 46, 46, 0.8);
                color: white;
                border: none;
                font-size: 16px;
                font-weight: bold;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid rgba(255, 255, 255, 20);
            }
            QListWidget::item:selected {
                background-color: rgba(255, 255, 255, 30);
                border-radius: 5px;
            }
        """)
        self.list_widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff) # Hide scrollbar for cleaner look
        self.list_widget.itemClicked.connect(self.copy_item)
        self.list_widget.itemActivated.connect(self.copy_item)
        self.list_widget.setIconSize(QSize(100, 100))
        
        layout.addWidget(self.list_widget)
        self.setLayout(layout)
        
        self.update_list()

    def open_settings(self):
        dlg = SettingsDialog(self.config_manager, self)
        dlg.exec()

    def toggle(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.activateWindow()
            self.list_widget.setFocus()
            if self.list_widget.count() > 0:
                self.list_widget.setCurrentRow(0)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)

    def get_day_folder(self, timestamp):
        date_str = datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d')
        return os.path.join(self.data_dir, date_str)

    def load_history(self):
        self.history = []
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            return

        # Walk through all date folders
        for date_folder in os.listdir(self.data_dir):
            full_date_folder = os.path.join(self.data_dir, date_folder)
            if not os.path.isdir(full_date_folder):
                continue
            
            for filename in os.listdir(full_date_folder):
                filepath = os.path.join(full_date_folder, filename)
                try:
                    # Filename format: TIMESTAMP_type.ext
                    parts = filename.split('_')
                    if len(parts) < 2:
                        continue
                    
                    timestamp = int(parts[0])
                    type_ext = parts[1] # text.txt or image.png
                    
                    item = {
                        "timestamp": timestamp,
                        "path": filepath
                    }

                    if "text.txt" in filename:
                        item["type"] = "text"
                        with open(filepath, 'r') as f:
                            item["content"] = f.read()
                    elif "image.png" in filename:
                        item["type"] = "image"
                    else:
                        continue
                    
                    self.history.append(item)
                except Exception as e:
                    print(f"Error loading file {filename}: {e}")

        # Sort by timestamp descending
        self.history.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Initial cleanup
        self.cleanup_items()

    def save_item(self, item_dict):
        timestamp = item_dict.get('timestamp', int(time.time() * 1000))
        folder = self.get_day_folder(timestamp)
        if not os.path.exists(folder):
            os.makedirs(folder)
            
        if item_dict['type'] == 'text':
            filename = f"{timestamp}_text.txt"
            filepath = os.path.join(folder, filename)
            with open(filepath, 'w') as f:
                f.write(item_dict['content'])
            item_dict['path'] = filepath
            item_dict['timestamp'] = timestamp
            
        elif item_dict['type'] == 'image':
            src_path = item_dict['path']
            filename = f"{timestamp}_image.png"
            dest_path = os.path.join(folder, filename)
            
            if src_path != dest_path:
                shutil.move(src_path, dest_path)
                
            item_dict['path'] = dest_path
            item_dict['timestamp'] = timestamp

    def cleanup_items(self):
        current_time = int(time.time() * 1000)
        # Using config or global fallback
        retention_days = self.config_manager.get("retention_days")
        retention_ms = retention_days * 24 * 60 * 60 * 1000
        
        items_to_remove = []
        
        # Check in-memory history
        for item in self.history:
            if current_time - item['timestamp'] > retention_ms:
                items_to_remove.append(item)
                # Delete file
                if os.path.exists(item['path']):
                    try:
                        os.remove(item['path'])
                    except Exception as e:
                        print(f"Error deleting file {item['path']}: {e}")
        
        for item in items_to_remove:
            self.history.remove(item)
            
        if items_to_remove:
            self.update_list()
            
        # Clean empty folders
        if os.path.exists(self.data_dir):
            for date_folder in os.listdir(self.data_dir):
                full_date_folder = os.path.join(self.data_dir, date_folder)
                if os.path.isdir(full_date_folder):
                    if not os.listdir(full_date_folder):
                        try:
                            os.rmdir(full_date_folder)
                        except Exception as e:
                            print(f"Error removing folder {full_date_folder}: {e}")

    def add_to_history(self, item_dict):
        if not item_dict:
            return
        
        current_timestamp = int(time.time() * 1000)
        item_dict['timestamp'] = current_timestamp
        
        to_remove = None
        for existing in self.history:
            if existing['type'] == item_dict['type']:
                if existing['type'] == 'text' and existing['content'] == item_dict['content']:
                    to_remove = existing
                    break
        
        if to_remove:
            self.history.remove(to_remove)
            if os.path.exists(to_remove['path']):
                os.remove(to_remove['path'])

        self.save_item(item_dict)
        self.history.insert(0, item_dict)
        
        self.update_list()

    def create_badge(self):
        pixmap = QPixmap(10, 10)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#00FF00")) # Green
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, 10, 10)
        painter.end()
        return QIcon(pixmap)

    def update_list(self):
        self.list_widget.clear()
        badge = self.create_badge()
        
        for i, item in enumerate(self.history):
            if item['type'] == 'text':
                display_text = item['content'].replace('\n', ' ')
                if len(display_text) > 50:
                    display_text = display_text[:47] + "..."
                list_item = QListWidgetItem(display_text)
                list_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                list_item.setToolTip(item['content'])
            elif item['type'] == 'image':
                list_item = QListWidgetItem()
                # Load image thumbnail
                pixmap = QPixmap(item['path'])
                if not pixmap.isNull():
                    # Scale for thumbnail
                    icon = QIcon(pixmap)
                    list_item.setIcon(icon)
                    list_item.setText(f"[Image] {os.path.basename(item['path'])}")
                else:
                    list_item.setText("[Image Not Found]")
                list_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Add badge to the first item (current clipboard)
            if i == 0:
                if item['type'] == 'image':
                    current_icon = list_item.icon()
                    if not current_icon.isNull():
                        # Composite
                        base_pixmap = current_icon.pixmap(100, 100)
                        painter = QPainter(base_pixmap)
                        badge_pixmap = badge.pixmap(10, 10)
                        painter.drawPixmap(0, 0, badge_pixmap)
                        painter.end()
                        list_item.setIcon(QIcon(base_pixmap))
                else:
                    list_item.setIcon(badge)
            
            self.list_widget.addItem(list_item)

    def copy_item(self, item):
        index = self.list_widget.row(item)
        if 0 <= index < len(self.history):
            entry = self.history[index]
            
            clipboard = QApplication.clipboard()
            
            if entry['type'] == 'text':
                clipboard.setText(entry['content'])
            elif entry['type'] == 'image':
                pixmap = QPixmap(entry['path'])
                if not pixmap.isNull():
                    clipboard.setPixmap(pixmap)
            
            self.hide()


def on_activate():
    # Emit signal to toggle window in main thread
    signal_handler.toggle_visibility.emit()

class HotkeyListener(threading.Thread):
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        self.listener = None
        self.running = True
        self.active_hotkey = None

    def run(self):
        while self.running:
            hotkey_str = self.config_manager.get("hotkey")
            if hotkey_str != self.active_hotkey:
                if self.listener:
                    self.listener.stop()
                    self.listener = None
                
                self.active_hotkey = hotkey_str
                try:
                    self.listener = keyboard.GlobalHotKeys({
                        hotkey_str: on_activate
                    })
                    self.listener.start()
                    print(f"Hotkey listener started with: {hotkey_str}")
                except Exception as e:
                    print(f"Failed to start hotkey listener with {hotkey_str}: {e}")
                    self.active_hotkey = None # Retry or wait
            
            time.sleep(1) # Check for changes or just wait

    def stop(self):
        self.running = False
        if self.listener:
            self.listener.stop()

# Helper to restart hotkey via signal
def restart_hotkey_listener():
    # In this design, the thread checks periodically/active_hotkey.
    # But to force immediate update, we can perhaps just have the thread loop faster
    # or handle it better.
    # Actually, simplest is to just rely on the loop checking or improve the thread.
    # Let's improve the thread to wake up on signal ideally, or just polling 1s is fine.
    # But wait, pynput listener blocks? No, start() is non-blocking.
    pass

hotkey_thread = None

def run_hotkey_manager(config_manager):
    global hotkey_thread
    current_hotkey = config_manager.get("hotkey")
    listener = None
    
    while True:
        try:
            # Create new listener if hotkey changed
            new_hotkey = config_manager.get("hotkey")
            
            if new_hotkey != current_hotkey or listener is None:
                if listener:
                    listener.stop()
                    # listener.join() # Might block?
                
                print(f"Starting hotkey listener: {new_hotkey}")
                try:
                    listener = keyboard.GlobalHotKeys({
                        new_hotkey: on_activate
                    })
                    listener.start()
                    current_hotkey = new_hotkey
                except Exception as e:
                    print(f"Error starting hotkey: {e}")
                    listener = None
                    
            # Wait for restart signal
            # This is a bit hacky for a thread. 
            # A better way is: Main thread receives signal -> sets a flag -> Thread checks flag.
            # Or assume we just restart the whole thread? No.
            # Let's simple polling for now in the thread loop.
            time.sleep(1)
            
        except Exception as e:
            print(f"Hotkey manager error: {e}")
            time.sleep(1)


def clipboard_changed():
    clipboard = QApplication.clipboard()
    mime_data = clipboard.mimeData()
    
    if mime_data.hasImage():
        image = clipboard.image()
        if not image.isNull():
            # Save to temp location using QStandardPaths or tempfile
            timestamp = int(time.time() * 1000)
            
            # Use CacheLocation for temporary images
            temp_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation)
            if not temp_dir:
                temp_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.TempLocation)
                
            temp_images_dir = os.path.join(temp_dir, "temp_images")
            if not os.path.exists(temp_images_dir):
                os.makedirs(temp_images_dir)
            
            filename = f"temp_{timestamp}.png"
            path = os.path.join(temp_images_dir, filename)
            image.save(path, "PNG")
            
            signal_handler.update_clipboard.emit({"type": "image", "path": path})
            
    elif mime_data.hasText():
        try:
            text = clipboard.text()
            if text:
                signal_handler.update_clipboard.emit({"type": "text", "content": text})
        except Exception:
            pass

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)

    # Determine data directory
    base_data_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
    data_dir = os.path.join(base_data_path, "data")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    print(f"Data storage: {data_dir}")

    # Config
    config_manager = ConfigManager(base_data_path)

    # Signal handler to communicate between thread and GUI
    signal_handler = SignalHandler()
    
    window = OverlayWindow(data_dir, config_manager)
    
    # Connect signals
    signal_handler.toggle_visibility.connect(window.toggle)
    signal_handler.update_clipboard.connect(window.add_to_history)
    
    # We need to restart hotkey manager when signal received
    # But hotkey manager is in a loop.
    # Ideally we just update the config_manager (already done in dialog) and the loop picks it up.
    
    # Clipboard monitoring
    clipboard = app.clipboard()
    clipboard.dataChanged.connect(clipboard_changed)

    # System Tray Icon
    tray_icon = QSystemTrayIcon(QIcon.fromTheme("applications-system"), app)
    tray_icon.setToolTip("Overlay App")

    menu = QMenu()
    
    toggle_action = QAction("Toggle Overlay", parent=menu)
    toggle_action.triggered.connect(window.toggle)
    menu.addAction(toggle_action)

    quit_action = QAction("Quit", parent=menu)
    quit_action.triggered.connect(app.quit)
    menu.addAction(quit_action)

    tray_icon.setContextMenu(menu)
    tray_icon.show()

    # Start hotkey listener/manager
    hotkey_thread = threading.Thread(target=run_hotkey_manager, args=(config_manager,), daemon=True)
    hotkey_thread.start()

    # Start hidden (do not call window.show())
    
    sys.exit(app.exec())
