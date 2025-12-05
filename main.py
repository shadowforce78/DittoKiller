import sys
import threading
import os
import time
import shutil
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QSystemTrayIcon, QMenu, QListWidget, QListWidgetItem
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QSize, QTimer
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QImage
from pynput import keyboard

DATA_DIR = "data"
RETENTION_SECONDS = 60 * 60 * 24 * 7 # 1 week

class SignalHandler(QObject):
    toggle_visibility = pyqtSignal()
    quit_app = pyqtSignal()
    update_clipboard = pyqtSignal(dict)

class OverlayWindow(QWidget):
    def __init__(self):
        super().__init__()
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
        return os.path.join(DATA_DIR, date_str)

    def load_history(self):
        self.history = []
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
            return

        # Walk through all date folders
        for date_folder in os.listdir(DATA_DIR):
            full_date_folder = os.path.join(DATA_DIR, date_folder)
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
            # Image is already saved in 'images/' by clipboard_changed, we need to move it or save it to data/
            # The clipboard_changed function saves to IMAGES_DIR. We should change that logic or move it here.
            # Let's assume clipboard_changed passes a temp path or we handle it.
            # Actually, let's update clipboard_changed to just pass data and we save here?
            # Or clipboard_changed saves to a temp location.
            # For now, let's move the file from the path provided in item_dict to our structure.
            
            src_path = item_dict['path']
            filename = f"{timestamp}_image.png"
            dest_path = os.path.join(folder, filename)
            
            if src_path != dest_path:
                shutil.move(src_path, dest_path)
                
            item_dict['path'] = dest_path
            item_dict['timestamp'] = timestamp

    def cleanup_items(self):
        current_time = int(time.time() * 1000)
        retention_ms = RETENTION_SECONDS * 1000
        
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
        if os.path.exists(DATA_DIR):
            for date_folder in os.listdir(DATA_DIR):
                full_date_folder = os.path.join(DATA_DIR, date_folder)
                if os.path.isdir(full_date_folder):
                    if not os.listdir(full_date_folder):
                        try:
                            os.rmdir(full_date_folder)
                        except Exception as e:
                            print(f"Error removing folder {full_date_folder}: {e}")

    def add_to_history(self, item_dict):
        if not item_dict:
            return
        
        # Deduplication (move to top if exists)
        # We need to check content for text, or maybe just treat every new copy as new?
        # User asked for deduplication before.
        # If we move to top, we should update its timestamp to NOW, so it stays for another minute.
        
        current_timestamp = int(time.time() * 1000)
        item_dict['timestamp'] = current_timestamp
        
        to_remove = None
        for existing in self.history:
            if existing['type'] == item_dict['type']:
                if existing['type'] == 'text' and existing['content'] == item_dict['content']:
                    to_remove = existing
                    break
                # For images, hard to compare content without hashing. 
                # If the user copies the same image, it comes as a new bitmap from clipboard.
                # So it will be a new file. We can't easily deduplicate images without hashing.
                # We'll skip image deduplication for now unless we implement hashing.
        
        if to_remove:
            self.history.remove(to_remove)
            # Should we delete the old file? Yes, because we are creating a new one with new timestamp.
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

def start_global_listener():
    try:
        with keyboard.GlobalHotKeys({
            '<ctrl>+ù': on_activate
        }) as h:    
            h.join()
    except Exception as e:
        print(f"Error in hotkey listener: {e}")

def clipboard_changed():
    clipboard = QApplication.clipboard()
    mime_data = clipboard.mimeData()
    
    # We need to pass data to main thread to save it properly with timestamp
    # For images, we need to save it temporarily or pass the QImage?
    # QImage cannot be passed through signal easily if it's across threads, but here we are in main thread (Qt signal).
    # So we can save it to a temp file or just pass the object?
    # Actually, let's just save it to a temp file in /tmp or just use the old images dir as temp.
    
    if mime_data.hasImage():
        image = clipboard.image()
        if not image.isNull():
            # Save to temp location
            timestamp = int(time.time() * 1000)
            # Use a temp dir
            temp_dir = "temp_images"
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            
            filename = f"temp_{timestamp}.png"
            path = os.path.join(temp_dir, filename)
            image.save(path, "PNG")
            
            signal_handler.update_clipboard.emit({"type": "image", "path": path})
            
    elif mime_data.hasText():
        text = clipboard.text()
        if text:
            signal_handler.update_clipboard.emit({"type": "text", "content": text})

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Signal handler to communicate between thread and GUI
    signal_handler = SignalHandler()
    
    window = OverlayWindow()
    
    # Connect signals
    signal_handler.toggle_visibility.connect(window.toggle)
    signal_handler.update_clipboard.connect(window.add_to_history)

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

    # Start hotkey listener in a separate thread
    listener_thread = threading.Thread(target=start_global_listener, daemon=True)
    listener_thread.start()

    # Start hidden (do not call window.show())
    
    sys.exit(app.exec())
