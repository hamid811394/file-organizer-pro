import os
import sys
import shutil
import datetime
import threading
import logging
import time
import hashlib
import base64
import mimetypes
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set, Union, Callable
from functools import partial, lru_cache
from concurrent.futures import ThreadPoolExecutor

# For encryption
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes

# For UI
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QFileDialog, QTreeView, QCheckBox, 
    QLineEdit, QProgressBar, QTabWidget, QSplitter, QFrame, 
    QListWidget, QListWidgetItem, QAbstractItemView, QMessageBox,
    QComboBox, QGroupBox, QRadioButton, QButtonGroup, QScrollArea,
    QSizePolicy, QStackedWidget, QToolButton, QMenu, QAction,
    QTextEdit, QDialog, QDialogButtonBox, QGridLayout, QSpacerItem,
    QGraphicsDropShadowEffect, QDesktopWidget, QStyle, QStyleOption,
    QListView, QFileSystemModel, QToolBar, QStatusBar, QInputDialog
)
from PyQt5.QtGui import (
    QIcon, QPixmap, QPalette, QColor, QFont, QFontDatabase, 
    QStandardItemModel, QStandardItem, QCursor, QKeySequence,
    QDragEnterEvent, QDropEvent, QPainter, QBrush, QLinearGradient,
    QGradient, QPen, QFontMetrics, QPainterPath, QImage
)
from PyQt5.QtCore import (
    Qt, QSize, QThread, pyqtSignal, QModelIndex, QDir, QFile, 
    QFileInfo, QUrl, QMimeData, QRect, QPoint, QTimer, QEvent,
    QPropertyAnimation, QEasingCurve, QByteArray, QBuffer, QIODevice,
    QSortFilterProxyModel
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("FileOrganizer")

# Constants
APP_NAME = "FileOrganizer Pro"
APP_VERSION = "1.0.0"
DEFAULT_ENCRYPTION_EXTENSION = ".encrypted"
BUFFER_SIZE = 65536  # 64kb chunks for file operations
MAX_WORKERS = min(8, os.cpu_count() or 4)  # Maximum number of worker threads for parallel processing

# File type categories and their extensions
FILE_CATEGORIES = {
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".svg", ".ico", ".heic"],
    "Videos": [".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv", ".webm", ".m4v", ".3gp", ".mpeg"],
    "Audio": [".mp3", ".wav", ".ogg", ".flac", ".aac", ".wma", ".m4a", ".opus"],
    "Documents": [".doc", ".docx", ".odt"],
    "PDF": [".pdf"],
    "Excel": [".xls", ".xlsx", ".csv", ".ods"],
    "PowerPoint": [".ppt", ".pptx", ".odp", ".key"],
    "Text": [".txt", ".rtf", ".md"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso"],
    "Code": [".py", ".js", ".html", ".css", ".java", ".cpp", ".c", ".h", ".php", ".rb", ".go", ".ts", ".json", ".xml"],
    "Executables": [".exe", ".msi", ".app", ".dmg", ".deb", ".rpm"],
    "APK": [".apk"],
    "OneNote": [".one", ".onetoc2"],
    "Encrypted": [".encrypted", ".enc", ".aes"],
    "Others": []  # Will catch anything not in the above categories
}

# Theme colors based on Teamify dashboard
class AppTheme:
    # ===== CUSTOMIZABLE: THEME COLORS =====
    # Main colors - Modify these values to change the color scheme
    DARK_BG = "#1E1E1E"        # Main background color
    DARKER_BG = "#171717"      # Darker background for inputs and secondary elements
    CARD_BG = "#252525"        # Card and panel background color
    PRIMARY = "#6C5CE7"        # Primary accent color
    PRIMARY_LIGHT = "#8A7EF2"  # Lighter version of primary color for hover states
    PRIMARY_DARK = "#5849D1"   # Darker version of primary color for pressed states
    ACCENT = "#00D2D3"         # Secondary accent color
    SUCCESS = "#00B894"        # Success color for positive actions
    WARNING = "#FDCB6E"        # Warning color for caution actions
    DANGER = "#FF7675"         # Danger color for destructive actions
    TEXT_PRIMARY = "#FFFFFF"   # Main text color
    TEXT_SECONDARY = "#B2B2B2" # Secondary text color
    BORDER = "#000000"         # Border color
    
    # Gradients
    GRADIENT_START = "#6C5CE7"  # Gradient start color
    GRADIENT_END = "#00D2D3"    # Gradient end color
    
    # Shadows
    SHADOW = "0px 4px 6px rgba(0, 0, 0, 0.1)"  # Shadow effect for elements
    
    # ===== CUSTOMIZABLE: FONT SETTINGS =====
    # Fonts - Modify these values to change the font settings
    FONT_FAMILY = "Segoe UI"    # Main font family
    FONT_SIZE_SMALL = 12        # Small text size
    FONT_SIZE_NORMAL = 14       # Normal text size
    FONT_SIZE_LARGE = 16        # Large text size
    FONT_SIZE_XLARGE = 20       # Extra large text size
    
    @staticmethod
    def setup_application_style(app: QApplication) -> None:
        """Apply the application-wide stylesheet"""
        app.setStyle("Fusion")
        
        # Create a dark palette
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(AppTheme.DARK_BG))
        palette.setColor(QPalette.WindowText, QColor(AppTheme.TEXT_PRIMARY))
        palette.setColor(QPalette.Base, QColor(AppTheme.CARD_BG))
        palette.setColor(QPalette.AlternateBase, QColor(AppTheme.DARKER_BG))
        palette.setColor(QPalette.ToolTipBase, QColor(AppTheme.DARK_BG))
        palette.setColor(QPalette.ToolTipText, QColor(AppTheme.TEXT_PRIMARY))
        palette.setColor(QPalette.Text, QColor(AppTheme.TEXT_PRIMARY))
        palette.setColor(QPalette.Button, QColor(AppTheme.CARD_BG))
        palette.setColor(QPalette.ButtonText, QColor(AppTheme.TEXT_PRIMARY))
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(AppTheme.PRIMARY))
        palette.setColor(QPalette.Highlight, QColor(AppTheme.PRIMARY))
        palette.setColor(QPalette.HighlightedText, QColor(AppTheme.TEXT_PRIMARY))
        
        app.setPalette(palette)
        
        # Load custom fonts if available
        try:
            QFontDatabase.addApplicationFont(":/fonts/segoe-ui.ttf")
        except:
            pass
        
        # ===== CUSTOMIZABLE: APPLICATION STYLESHEET =====
        # Set application-wide stylesheet - Modify these values to change the appearance of UI elements
        stylesheet = f"""
        QWidget {{
            font-family: "{AppTheme.FONT_FAMILY}";
            font-size: {AppTheme.FONT_SIZE_NORMAL}px;
            color: {AppTheme.TEXT_PRIMARY};
        }}
        
        QMainWindow, QDialog {{
            background-color: {AppTheme.DARK_BG};
        }}
        
        QTabWidget::pane {{
            border: 1px solid {AppTheme.BORDER};
            background-color: {AppTheme.CARD_BG};
            border-radius: 4px;
        }}
        
        QTabBar::tab {{
            background-color: {AppTheme.DARKER_BG};
            color: {AppTheme.TEXT_SECONDARY};
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            padding: 10px 20px;  /* CUSTOMIZABLE: Tab padding (vertical, horizontal) */
            margin-right: 2px;   /* CUSTOMIZABLE: Space between tabs */
            font-size: {AppTheme.FONT_SIZE_NORMAL}px;
        }}
        
        QTabBar::tab:selected {{
            background-color: {AppTheme.PRIMARY};
            color: {AppTheme.TEXT_PRIMARY};
        }}
        
        QPushButton {{
            background-color: {AppTheme.PRIMARY};
            color: {AppTheme.TEXT_PRIMARY};
            border: none;
            border-radius: 4px;  /* CUSTOMIZABLE: Button corner radius */
            padding: 10px 20px;  /* CUSTOMIZABLE: Button padding (vertical, horizontal) */
            font-weight: bold;
            font-size: {AppTheme.FONT_SIZE_NORMAL}px;
        }}
        
        QPushButton:hover {{
            background-color: {AppTheme.PRIMARY_LIGHT};
        }}
        
        QPushButton:pressed {{
            background-color: {AppTheme.PRIMARY_DARK};
        }}
        
        QPushButton:disabled {{
            background-color: {AppTheme.CARD_BG};
            color: {AppTheme.TEXT_SECONDARY};
        }}
        
        QPushButton#dangerButton {{
            background-color: {AppTheme.DANGER};
        }}
        
        QPushButton#dangerButton:hover {{
            background-color: #FF8B8B;
        }}
        
        QPushButton#successButton {{
            background-color: {AppTheme.SUCCESS};
        }}
        
        QPushButton#successButton:hover {{
            background-color: #00D1A7;
        }}
        
        QPushButton#optionButton {{
            background-color: {AppTheme.DARKER_BG};
            color: {AppTheme.TEXT_SECONDARY};
            border: 1px solid {AppTheme.BORDER};
            padding: 12px 24px;  /* CUSTOMIZABLE: Option button padding */
            font-size: {AppTheme.FONT_SIZE_NORMAL}px;
        }}
        
        QPushButton#optionButton:checked {{
            background-color: {AppTheme.PRIMARY};
            color: {AppTheme.TEXT_PRIMARY};
            border: none;
        }}
        
        QPushButton#sidebarButton {{
            background-color: transparent;
            color: {AppTheme.TEXT_SECONDARY};
            border: none;
            border-radius: 0;
            padding: 12px 16px;  /* CUSTOMIZABLE: Sidebar button padding */
            text-align: left;
            font-size: {AppTheme.FONT_SIZE_LARGE}px;
        }}
        
        QPushButton#sidebarButton:hover {{
            background-color: rgba(108, 92, 231, 0.2);
            color: {AppTheme.TEXT_PRIMARY};
        }}
        
        QPushButton#sidebarButton:checked {{
            background-color: {AppTheme.PRIMARY};
            color: {AppTheme.TEXT_PRIMARY};
        }}
        
        QLineEdit, QTextEdit, QComboBox {{
            background-color: {AppTheme.DARKER_BG};
            border: 1px solid {AppTheme.BORDER};
            border-radius: 4px;  /* CUSTOMIZABLE: Input field corner radius */
            padding: 10px;       /* CUSTOMIZABLE: Input field padding */
            color: {AppTheme.TEXT_PRIMARY};
            font-size: {AppTheme.FONT_SIZE_NORMAL}px;
        }}
        
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
            border: 1px solid {AppTheme.PRIMARY};
        }}
        
        QTreeView, QListWidget, QListView {{
            background-color: {AppTheme.CARD_BG};
            border: 1px solid {AppTheme.BORDER};
            border-radius: 4px;  /* CUSTOMIZABLE: List view corner radius */
            padding: 4px;        /* CUSTOMIZABLE: List view padding */
            outline: none;
            font-size: {AppTheme.FONT_SIZE_NORMAL}px;
        }}
        
        QTreeView::item, QListWidget::item, QListView::item {{
            padding: 8px;        /* CUSTOMIZABLE: List item padding */
            border-radius: 2px;  /* CUSTOMIZABLE: List item corner radius */
        }}
        
        QTreeView::item:selected, QListWidget::item:selected, QListView::item:selected {{
            background-color: {AppTheme.PRIMARY};
            color: {AppTheme.TEXT_PRIMARY};
        }}
        
        QTreeView::item:hover, QListWidget::item:hover, QListView::item:hover {{
            background-color: rgba(108, 92, 231, 0.2);
        }}
        
        QCheckBox {{
            spacing: 80px;        /* CUSTOMIZABLE: Space between checkbox and text */
            font-size: {AppTheme.FONT_SIZE_NORMAL}px;
        }}
        
        QCheckBox::indicator {{
            width: 20px;         /* CUSTOMIZABLE: Checkbox width */
            height: 20px;        /* CUSTOMIZABLE: Checkbox height */
            border-radius: 3px;  /* CUSTOMIZABLE: Checkbox corner radius */
            border: 1px solid {AppTheme.BORDER};
        }}
        
        QCheckBox::indicator:unchecked {{
            background-color: {AppTheme.DARKER_BG};
        }}
        
        QCheckBox::indicator:checked {{
            background-color: {AppTheme.PRIMARY};
            image: url(:/icons/check.png);
        }}
        
        QProgressBar {{
            border: 1px solid {AppTheme.BORDER};
            border-radius: 4px;  /* CUSTOMIZABLE: Progress bar corner radius */
            background-color: {AppTheme.DARKER_BG};
            text-align: center;
            color: {AppTheme.TEXT_PRIMARY};
            font-size: {AppTheme.FONT_SIZE_NORMAL}px;
            min-height: 24px;    /* CUSTOMIZABLE: Progress bar height */
        }}
        
        QProgressBar::chunk {{
            background-color: {AppTheme.PRIMARY};
            border-radius: 3px;  /* CUSTOMIZABLE: Progress chunk corner radius */
        }}
        
        QGroupBox {{
            border: 1px solid {AppTheme.BORDER};
            border-radius: 4px;  /* CUSTOMIZABLE: Group box corner radius */
            margin-top: 20px;    /* CUSTOMIZABLE: Group box top margin */
            padding-top: 20px;   /* CUSTOMIZABLE: Group box top padding */
            font-size: {AppTheme.FONT_SIZE_NORMAL}px;
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top center;
            padding: 0 8px;      /* CUSTOMIZABLE: Group box title padding */
            color: {AppTheme.TEXT_PRIMARY};
            font-size: {AppTheme.FONT_SIZE_NORMAL}px;
        }}
        
        QScrollBar:vertical {{
            border: none;
            background-color: {AppTheme.DARKER_BG};
            width: 12px;         /* CUSTOMIZABLE: Vertical scrollbar width */
            margin: 0px;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {AppTheme.PRIMARY};
            border-radius: 6px;  /* CUSTOMIZABLE: Scrollbar handle radius */
            min-height: 20px;    /* CUSTOMIZABLE: Minimum scrollbar handle height */
        }}
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        
        QScrollBar:horizontal {{
            border: none;
            background-color: {AppTheme.DARKER_BG};
            height: 12px;        /* CUSTOMIZABLE: Horizontal scrollbar height */
            margin: 0px;
        }}
        
        QScrollBar::handle:horizontal {{
            background-color: {AppTheme.PRIMARY};
            border-radius: 6px;  /* CUSTOMIZABLE: Scrollbar handle radius */
            min-width: 20px;     /* CUSTOMIZABLE: Minimum scrollbar handle width */
        }}
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
        
        QSplitter::handle {{
            background-color: {AppTheme.BORDER};
        }}
        
        QToolTip {{
            background-color: {AppTheme.DARK_BG};
            color: {AppTheme.TEXT_PRIMARY};
            border: 1px solid {AppTheme.BORDER};
            border-radius: 4px;  /* CUSTOMIZABLE: Tooltip corner radius */
            padding: 6px;        /* CUSTOMIZABLE: Tooltip padding */
            font-size: {AppTheme.FONT_SIZE_NORMAL}px;
        }}
        
        QMenu {{
            background-color: {AppTheme.CARD_BG};
            border: 1px solid {AppTheme.BORDER};
            border-radius: 4px;  /* CUSTOMIZABLE: Menu corner radius */
            font-size: {AppTheme.FONT_SIZE_NORMAL}px;
        }}
        
        QMenu::item {{
            padding: 8px 24px 8px 16px;  /* CUSTOMIZABLE: Menu item padding */
        }}
        
        QMenu::item:selected {{
            background-color: {AppTheme.PRIMARY};
            color: {AppTheme.TEXT_PRIMARY};
        }}
        
        QComboBox QAbstractItemView {{
            background-color: {AppTheme.CARD_BG};
            border: 1px solid {AppTheme.BORDER};
            selection-background-color: {AppTheme.PRIMARY};
            selection-color: {AppTheme.TEXT_PRIMARY};
            outline: none;
            font-size: {AppTheme.FONT_SIZE_NORMAL}px;
        }}
        
        QLabel#headerLabel {{
            font-size: {AppTheme.FONT_SIZE_XLARGE}px;
            font-weight: bold;
            color: {AppTheme.TEXT_PRIMARY};
        }}
        
        QLabel#subHeaderLabel {{
            font-size: {AppTheme.FONT_SIZE_LARGE}px;
            color: {AppTheme.TEXT_SECONDARY};
        }}
        
        QLabel#tileLabel {{
            font-size: {AppTheme.FONT_SIZE_NORMAL}px;
            color: {AppTheme.TEXT_PRIMARY};
            padding: 4px;        /* CUSTOMIZABLE: Tile label padding */
            qproperty-alignment: AlignCenter;
        }}
        
        QFrame#card {{
            background-color: {AppTheme.CARD_BG};
            border-radius: 8px;  /* CUSTOMIZABLE: Card corner radius */
        }}
        
        QFrame#separator {{
            background-color: {AppTheme.BORDER};
            max-height: 1px;     /* CUSTOMIZABLE: Separator height */
        }}
        
        QFrame#sidebar {{
            background-color: {AppTheme.DARKER_BG};
            border-right: 1px solid {AppTheme.BORDER};
        }}
        
        QFrame#tile {{
            background-color: {AppTheme.CARD_BG};
            border: 1px solid {AppTheme.BORDER};
            border-radius: 8px;  /* CUSTOMIZABLE: Tile corner radius */
        }}
        
        QFrame#tile:hover {{
            border: 1px solid {AppTheme.PRIMARY};
        }}
        
        QStatusBar {{
            background-color: {AppTheme.DARKER_BG};
            color: {AppTheme.TEXT_SECONDARY};
            font-size: {AppTheme.FONT_SIZE_NORMAL}px;
        }}
        
        QToolBar {{
            background-color: {AppTheme.DARKER_BG};
            border-bottom: 1px solid {AppTheme.BORDER};
            spacing: 6px;        /* CUSTOMIZABLE: Toolbar item spacing */
        }}
        
        QToolButton {{
            background-color: transparent;
            border: none;
            border-radius: 4px;  /* CUSTOMIZABLE: Tool button corner radius */
            padding: 6px;        /* CUSTOMIZABLE: Tool button padding */
        }}
        
        QToolButton:hover {{
            background-color: rgba(108, 92, 231, 0.2);
        }}
        
        QToolButton:pressed {{
            background-color: rgba(108, 92, 231, 0.3);
        }}
        
        QFrame#propertiesPanel {{
            background-color: {AppTheme.CARD_BG};
            border-radius: 8px;  /* CUSTOMIZABLE: Properties panel corner radius */
            padding: 10px;       /* CUSTOMIZABLE: Properties panel padding */
        }}
        
        /* Style for the browse button */
        QToolButton#browseButton {{
            background-color: {AppTheme.CARD_BG};
            border: 1px solid {AppTheme.BORDER};
            border-radius: 4px;  /* CUSTOMIZABLE: Browse button corner radius */
            padding: 8px;        /* CUSTOMIZABLE: Browse button padding */
            font-weight: bold;
        }}
        
        QToolButton#browseButton:hover {{
            background-color: {AppTheme.PRIMARY};
        }}
        
        /* Style for the back button */
        QToolButton#backButton {{
            background-color: {AppTheme.CARD_BG};
            border: 1px solid {AppTheme.BORDER};
            border-radius: 4px;  /* CUSTOMIZABLE: Back button corner radius */
            padding: 8px;        /* CUSTOMIZABLE: Back button padding */
            font-weight: bold;
        }}
        
        QToolButton#backButton:hover {{
            background-color: {AppTheme.PRIMARY};
        }}
        
        /* Style for window control buttons */
        QToolButton#windowControlButton {{
            background-color: transparent;
            border: none;
            border-radius: 0;
            padding: 8px;
        }}
        
        QToolButton#windowControlButton:hover {{
            background-color: rgba(255, 255, 255, 0.1);
        }}
        
        QToolButton#closeButton:hover {{
            background-color: #FF5555;
        }}
        
        QFrame#titleBar {{
            background-color: {AppTheme.DARKER_BG};
            border-bottom: 1px solid {AppTheme.BORDER};
        }}
        """
        
        app.setStyleSheet(stylesheet)

# Create icons for file types
class FileIcons:
    """Class to manage file type icons"""
    
    # Cache for icons to improve performance
    _icon_cache = {}
    
    @staticmethod
    def create_folder_icon():
        """Create a proper folder icon"""
        cache_key = "folder"
        if cache_key in FileIcons._icon_cache:
            return FileIcons._icon_cache[cache_key]
            
        pixmap = QPixmap(64, 64)  # CUSTOMIZABLE: Folder icon size
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw folder base
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#0984E3"))  # CUSTOMIZABLE: Folder base color
        painter.drawRoundedRect(4, 12, 56, 44, 4, 4)  # CUSTOMIZABLE: Folder base dimensions and corner radius
        
        # Draw folder top
        painter.setBrush(QColor("#74B9FF"))  # CUSTOMIZABLE: Folder top color
        path = QPainterPath()
        path.moveTo(4, 12)
        path.lineTo(24, 12)
        path.lineTo(30, 6)
        path.lineTo(56, 6)
        path.lineTo(60, 12)
        path.lineTo(60, 20)
        path.lineTo(4, 20)
        path.closeSubpath()
        painter.drawPath(path)
        
        painter.end()
        
        icon = QIcon(pixmap)
        FileIcons._icon_cache[cache_key] = icon
        return icon
    
    @staticmethod
    def create_back_icon():
        """Create a back arrow icon"""
        cache_key = "back"
        if cache_key in FileIcons._icon_cache:
            return FileIcons._icon_cache[cache_key]
            
        pixmap = QPixmap(24, 24)  # CUSTOMIZABLE: Back icon size
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw arrow
        painter.setPen(QPen(QColor(AppTheme.TEXT_PRIMARY), 2))  # CUSTOMIZABLE: Arrow line thickness
        
        # Arrow pointing left
        path = QPainterPath()
        path.moveTo(18, 4)
        path.lineTo(8, 12)
        path.lineTo(18, 20)
        painter.drawPath(path)
        
        painter.end()
        
        icon = QIcon(pixmap)
        FileIcons._icon_cache[cache_key] = icon
        return icon
    
    @staticmethod
    def create_icon(color, text):
        """Create an icon with the given color and text"""
        cache_key = f"{color}_{text}"
        if cache_key in FileIcons._icon_cache:
            return FileIcons._icon_cache[cache_key]
            
        pixmap = QPixmap(64, 64)  # CUSTOMIZABLE: File icon size
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw rounded rectangle
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(color))
        painter.drawRoundedRect(4, 4, 56, 56, 8, 8)  # CUSTOMIZABLE: Icon dimensions and corner radius
        
        # Draw text
        painter.setPen(QColor("white"))
        font = QFont("Arial", 14, QFont.Bold)  # CUSTOMIZABLE: Icon text font and size
        painter.setFont(font)
        painter.drawText(QRect(4, 4, 56, 56), Qt.AlignCenter, text)
        
        painter.end()
        
        icon = QIcon(pixmap)
        FileIcons._icon_cache[cache_key] = icon
        return icon
    
    @staticmethod
    def get_file_icon(file_path):
        """Get an appropriate icon for a file based on its type"""
        # Check if we already have this icon cached by path
        if file_path in FileIcons._icon_cache:
            return FileIcons._icon_cache[file_path]
            
        if os.path.isdir(file_path):
            # Use proper folder icon for directories
            icon = FileIcons.create_folder_icon()
        else:
            category = get_file_category(file_path)
            
            if category == "Images":
                icon = FileIcons.create_icon("#FF7675", "IMG")
            elif category == "Videos":
                icon = FileIcons.create_icon("#6C5CE7", "VID")
            elif category == "Audio":
                icon = FileIcons.create_icon("#00B894", "AUD")
            elif category == "Documents":
                icon = FileIcons.create_icon("#0984E3", "DOC")
            elif category == "PDF":
                icon = FileIcons.create_icon("#E84393", "PDF")
            elif category == "Excel":
                icon = FileIcons.create_icon("#00B894", "XLS")
            elif category == "PowerPoint":
                icon = FileIcons.create_icon("#E84393", "PPT")
            elif category == "Text":
                icon = FileIcons.create_icon("#74B9FF", "TXT")
            elif category == "Archives":
                icon = FileIcons.create_icon("#A29BFE", "ZIP")
            elif category == "Code":
                icon = FileIcons.create_icon("#00CEC9", "CODE")
            elif category == "Executables":
                icon = FileIcons.create_icon("#FD79A8", "EXE")
            elif category == "APK":
                icon = FileIcons.create_icon("#55EFC4", "APK")
            elif category == "Encrypted":
                icon = FileIcons.create_icon("#636E72", "ENC")
            else:
                icon = FileIcons.create_icon("#B2BEC3", "FILE")
        
        # Cache the icon by path
        FileIcons._icon_cache[file_path] = icon
        return icon

# Utility functions
@lru_cache(maxsize=1024)
def get_file_category(file_path: str) -> str:
    """Determine the category of a file based on its extension"""
    ext = os.path.splitext(file_path)[1].lower()
    
    for category, extensions in FILE_CATEGORIES.items():
        if ext in extensions:
            return category
    
    return "Others"

def get_file_date(file_path: str, date_type: str = "modified") -> datetime.datetime:
    """Get the creation or modification date of a file"""
    if date_type == "created":
        timestamp = os.path.getctime(file_path)
    else:  # modified
        timestamp = os.path.getmtime(file_path)
    
    return datetime.datetime.fromtimestamp(timestamp)

def format_size(size_bytes: int) -> str:
    """Format file size from bytes to human-readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

def derive_key_from_password(password: str, salt: bytes = None) -> Tuple[bytes, bytes]:
    """Derive an encryption key from a password"""
    if salt is None:
        salt = get_random_bytes(16)
    
    # Use PBKDF2 to derive a key from the password
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000, 32)
    
    return key, salt

def get_file_thumbnail(file_path: str, size: int = 64) -> QPixmap:
    """Generate a thumbnail for a file"""
    # Check if we have a cached thumbnail
    cache_key = f"thumb_{file_path}_{size}"
    if cache_key in FileIcons._icon_cache:
        return FileIcons._icon_cache[cache_key].pixmap(size, size)
    
    default_icon = FileIcons.get_file_icon(file_path)
    default_pixmap = default_icon.pixmap(size, size)
    
    # For images, try to load the actual image
    if get_file_category(file_path) == "Images":
        try:
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                # Cache the thumbnail
                FileIcons._icon_cache[cache_key] = QIcon(scaled_pixmap)
                return scaled_pixmap
        except:
            pass
    
    # For videos, we could add video thumbnail generation here
    # This would require additional libraries like OpenCV
    
    return default_pixmap

def get_user_home_dir() -> str:
    """Get the user's home directory"""
    return os.path.expanduser("~")

def open_file(file_path: str) -> bool:
    """Open a file with the default application"""
    try:
        if sys.platform == 'win32':
            os.startfile(file_path)
        elif sys.platform == 'darwin':  # macOS
            subprocess.call(['open', file_path])
        else:  # Linux
            subprocess.call(['xdg-open', file_path])
        return True
    except Exception as e:
        logger.error(f"Error opening file {file_path}: {str(e)}")
        return False

def open_file_location(file_path: str) -> bool:
    """Open the containing folder of a file"""
    try:
        folder_path = os.path.dirname(file_path)
        if sys.platform == 'win32':
            subprocess.Popen(f'explorer /select,"{file_path}"')
        elif sys.platform == 'darwin':  # macOS
            subprocess.call(['open', folder_path])
        else:  # Linux
            subprocess.call(['xdg-open', folder_path])
        return True
    except Exception as e:
        logger.error(f"Error opening file location {file_path}: {str(e)}")
        return False

def get_directory_size(path: str) -> int:
    """Calculate the total size of a directory"""
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.exists(fp):
                    total_size += os.path.getsize(fp)
    except Exception as e:
        logger.error(f"Error calculating directory size: {str(e)}")
    return total_size

# Worker threads for background operations
class FileOrganizerWorker(QThread):
    """Worker thread for organizing files"""
    progress_updated = pyqtSignal(int, int)  # current, total
    status_updated = pyqtSignal(str)
    operation_completed = pyqtSignal(bool, str)  # success, message
    file_processed = pyqtSignal(str, str)  # source, destination
    
    def __init__(self, 
                 files: List[str], 
                 destination: str, 
                 organize_by: str,
                 remove_originals: bool = False):
        super().__init__()
        self.files = files
        self.destination = destination
        self.organize_by = organize_by  # "type", "date", or "both"
        self.remove_originals = remove_originals
        self.is_cancelled = False
    
    def run(self):
        try:
            total_files = len(self.files)
            processed = 0
            
            # Create main organization folders
            if self.organize_by == "type" or self.organize_by == "both":
                type_folder = os.path.join(self.destination, "Organized by Type")
                os.makedirs(type_folder, exist_ok=True)
            
            if self.organize_by == "date" or self.organize_by == "both":
                date_folder = os.path.join(self.destination, "Organized by Date")
                os.makedirs(date_folder, exist_ok=True)
            
            # Use ThreadPoolExecutor for parallel processing
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                # Create a list to store futures
                futures = []
                
                for file_path in self.files:
                    if self.is_cancelled:
                        break
                    
                    # Skip directories
                    if os.path.isdir(file_path):
                        processed += 1
                        self.progress_updated.emit(processed, total_files)
                        continue
                    
                    # Submit task to executor
                    future = executor.submit(
                        self._process_file, 
                        file_path, 
                        type_folder if self.organize_by in ["type", "both"] else None,
                        date_folder if self.organize_by in ["date", "both"] else None
                    )
                    futures.append(future)
                
                # Process results as they complete
                for i, future in enumerate(futures):
                    if self.is_cancelled:
                        break
                    
                    try:
                        result = future.result()
                        if result:
                            source, dest = result
                            self.file_processed.emit(source, dest)
                    except Exception as e:
                        logger.error(f"Error in worker thread: {str(e)}")
                    
                    processed += 1
                    self.progress_updated.emit(processed, total_files)
            
            if self.is_cancelled:
                self.operation_completed.emit(False, "Operation cancelled")
            else:
                self.operation_completed.emit(True, f"Successfully processed {processed} of {total_files} files")
            
        except Exception as e:
            logger.error(f"Organization error: {str(e)}")
            self.operation_completed.emit(False, f"Error: {str(e)}")
    
    def _process_file(self, file_path, type_folder, date_folder):
        """Process a single file (to be run in a worker thread)"""
        try:
            filename = os.path.basename(file_path)
            dest_path = None
            
            # Process by type
            if type_folder:
                category = get_file_category(file_path)
                category_folder = os.path.join(type_folder, category)
                os.makedirs(category_folder, exist_ok=True)
                
                dest_path = os.path.join(category_folder, filename)
                
                # Handle duplicate filenames
                counter = 1
                name, ext = os.path.splitext(filename)
                while os.path.exists(dest_path):
                    new_filename = f"{name}_{counter}{ext}"
                    dest_path = os.path.join(category_folder, new_filename)
                    counter += 1
                
                # Copy the file
                shutil.copy2(file_path, dest_path)
                self.status_updated.emit(f"Copied to Type: {filename}")
            
            # Process by date
            if date_folder:
                date = get_file_date(file_path)
                # Use yyyy-mm-dd format
                date_subfolder = date.strftime("%Y-%m-%d")
                day_folder = os.path.join(date_folder, date_subfolder)
                os.makedirs(day_folder, exist_ok=True)
                
                dest_path = os.path.join(day_folder, filename)
                
                # Handle duplicate filenames
                counter = 1
                name, ext = os.path.splitext(filename)
                while os.path.exists(dest_path):
                    new_filename = f"{name}_{counter}{ext}"
                    dest_path = os.path.join(day_folder, new_filename)
                    counter += 1
                
                # Copy the file
                shutil.copy2(file_path, dest_path)
                self.status_updated.emit(f"Copied to Date: {filename}")
            
            # Remove original if requested
            if self.remove_originals:
                os.remove(file_path)
                self.status_updated.emit(f"Removed original: {filename}")
            
            return (file_path, dest_path)
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            self.status_updated.emit(f"Error: {filename} - {str(e)}")
            return None
    
    def cancel(self):
        self.is_cancelled = True

class EncryptionWorker(QThread):
    """Worker thread for encrypting/decrypting files"""
    progress_updated = pyqtSignal(int, int)  # current, total
    status_updated = pyqtSignal(str)
    operation_completed = pyqtSignal(bool, str)  # success, message
    file_processed = pyqtSignal(str, str)  # source, destination
    
    def __init__(self, 
                 files: List[str], 
                 password: str,
                 operation: str,  # "encrypt" or "decrypt"
                 remove_originals: bool = False):
        super().__init__()
        self.files = files
        self.password = password
        self.operation = operation
        self.remove_originals = remove_originals
        self.is_cancelled = False
    
    def run(self):
        try:
            total_files = len(self.files)
            processed = 0
            
            # Use ThreadPoolExecutor for parallel processing
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                # Create a list to store futures
                futures = []
                
                for file_path in self.files:
                    if self.is_cancelled:
                        break
                    
                    # Submit task to executor
                    future = executor.submit(
                        self._process_file, 
                        file_path
                    )
                    futures.append(future)
                
                # Process results as they complete
                for i, future in enumerate(futures):
                    if self.is_cancelled:
                        break
                    
                    try:
                        result = future.result()
                        if result:
                            source, dest = result
                            self.file_processed.emit(source, dest)
                    except Exception as e:
                        logger.error(f"Error in worker thread: {str(e)}")
                    
                    processed += 1
                    self.progress_updated.emit(processed, total_files)
            
            if self.is_cancelled:
                self.operation_completed.emit(False, "Operation cancelled")
            else:
                self.operation_completed.emit(True, f"Successfully {self.operation}ed {processed} of {total_files} files/folders")
            
        except Exception as e:
            logger.error(f"Encryption error: {str(e)}")
            self.operation_completed.emit(False, f"Error: {str(e)}")
    
    def _process_file(self, file_path):
        """Process a single file or directory (to be run in a worker thread)"""
        try:
            filename = os.path.basename(file_path)
            self.status_updated.emit(f"{self.operation.capitalize()}ing: {filename}")
            
            # Handle directories
            if os.path.isdir(file_path):
                if self.operation == "encrypt":
                    output_path = file_path + DEFAULT_ENCRYPTION_EXTENSION
                    self._encrypt_directory(file_path, output_path)
                else:  # decrypt
                    if file_path.endswith(DEFAULT_ENCRYPTION_EXTENSION):
                        output_path = file_path[:-len(DEFAULT_ENCRYPTION_EXTENSION)]
                    else:
                        dir_path = os.path.dirname(file_path)
                        base_name = os.path.basename(file_path)
                        output_path = os.path.join(dir_path, f"decrypted_{base_name}")
                    
                    self._decrypt_directory(file_path, output_path)
            else:
                # Handle files
                # Determine output path
                if self.operation == "encrypt":
                    output_path = file_path + DEFAULT_ENCRYPTION_EXTENSION
                else:  # decrypt
                    if file_path.endswith(DEFAULT_ENCRYPTION_EXTENSION):
                        output_path = file_path[:-len(DEFAULT_ENCRYPTION_EXTENSION)]
                    else:
                        # If not our standard extension, create a "decrypted_" prefix
                        dir_path = os.path.dirname(file_path)
                        base_name = os.path.basename(file_path)
                        output_path = os.path.join(dir_path, f"decrypted_{base_name}")
                
                # Handle duplicate filenames
                counter = 1
                while os.path.exists(output_path):
                    if self.operation == "encrypt":
                        name, ext = os.path.splitext(file_path)
                        output_path = f"{name}_{counter}{ext}{DEFAULT_ENCRYPTION_EXTENSION}"
                    else:
                        dir_path = os.path.dirname(output_path)
                        name, ext = os.path.splitext(os.path.basename(output_path))
                        if name.startswith("decrypted_"):
                            name = f"decrypted_{counter}_{name[10:]}"
                        else:
                            name = f"decrypted_{counter}_{name}"
                        output_path = os.path.join(dir_path, f"{name}{ext}")
                    counter += 1
                
                # Process the file
                if self.operation == "encrypt":
                    self._encrypt_file(file_path, output_path)
                else:
                    self._decrypt_file(file_path, output_path)
            
            # Remove original if requested
            if self.remove_originals:
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                else:
                    os.remove(file_path)
            
            return (file_path, output_path)
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            self.status_updated.emit(f"Error: {filename} - {str(e)}")
            return None
    
    def _encrypt_file(self, input_path: str, output_path: str):
        """Encrypt a file using AES-256"""
        # Generate a random salt
        salt = get_random_bytes(16)
        # Derive key from password
        key, _ = derive_key_from_password(self.password, salt)
        # Generate a random IV (initialization vector)
        iv = get_random_bytes(16)
        # Create cipher
        cipher = AES.new(key, AES.MODE_CBC, iv)
        
        with open(input_path, 'rb') as infile, open(output_path, 'wb') as outfile:
            # Write salt and IV to the output file
            outfile.write(salt)
            outfile.write(iv)
            
            # Process file in chunks
            while True:
                chunk = infile.read(BUFFER_SIZE)
                if len(chunk) == 0:
                    break
                
                # If this is the last chunk, pad it
                if len(chunk) % 16 != 0:
                    chunk = pad(chunk, 16)
                
                # Encrypt and write the chunk
                encrypted_chunk = cipher.encrypt(chunk)
                outfile.write(encrypted_chunk)
    
    def _decrypt_file(self, input_path: str, output_path: str):
        """Decrypt a file using AES-256"""
        with open(input_path, 'rb') as infile:
            # Read salt and IV from the file
            salt = infile.read(16)
            iv = infile.read(16)
            
            # Derive key from password and salt
            key, _ = derive_key_from_password(self.password, salt)
            
            # Create cipher
            cipher = AES.new(key, AES.MODE_CBC, iv)
            
            # Read all encrypted data
            encrypted_data = infile.read()
            
            # Decrypt the data
            try:
                decrypted_data = cipher.decrypt(encrypted_data)
                # Unpad the data
                decrypted_data = unpad(decrypted_data, 16)
                
                # Write decrypted data to output file
                with open(output_path, 'wb') as outfile:
                    outfile.write(decrypted_data)
            except ValueError as e:
                # If unpadding fails, it might not be properly encrypted
                raise ValueError("Invalid padding or incorrect password")
    
    def _encrypt_directory(self, input_dir: str, output_path: str):
        """Encrypt a directory by creating an encrypted archive"""
        # Create a temporary directory to store the encrypted files
        temp_dir = output_path + "_temp"
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            # Walk through the directory and encrypt each file
            for root, dirs, files in os.walk(input_dir):
                # Create relative path
                rel_path = os.path.relpath(root, input_dir)
                if rel_path == ".":
                    rel_path = ""
                
                # Create corresponding directory in temp_dir
                if rel_path:
                    os.makedirs(os.path.join(temp_dir, rel_path), exist_ok=True)
                
                # Encrypt each file
                for file in files:
                    src_file = os.path.join(root, file)
                    dst_file = os.path.join(temp_dir, rel_path, file + DEFAULT_ENCRYPTION_EXTENSION)
                    self._encrypt_file(src_file, dst_file)
            
            # Create a metadata file with directory structure
            metadata_path = os.path.join(temp_dir, "directory_structure.json")
            with open(metadata_path, 'w') as f:
                import json
                structure = {"type": "directory", "name": os.path.basename(input_dir)}
                json.dump(structure, f)
            
            # Create the final encrypted directory
            shutil.make_archive(output_path, 'zip', temp_dir)
            os.rename(output_path + ".zip", output_path)
            
        finally:
            # Clean up temporary directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
    
    def _decrypt_directory(self, input_path: str, output_dir: str):
        """Decrypt a directory from an encrypted archive"""
        # Create a temporary directory to extract the encrypted files
        temp_dir = input_path + "_temp"
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            # Rename to zip for extraction
            temp_zip = input_path + ".zip"
            shutil.copy2(input_path, temp_zip)
            
            # Extract the encrypted files
            import zipfile
            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Create the output directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Check for metadata file
            metadata_path = os.path.join(temp_dir, "directory_structure.json")
            if os.path.exists(metadata_path):
                # This is a directory we encrypted
                # Walk through the temp directory and decrypt each file
                for root, dirs, files in os.walk(temp_dir):
                    # Skip metadata file
                    if "directory_structure.json" in files:
                        files.remove("directory_structure.json")
                    
                    # Create relative path
                    rel_path = os.path.relpath(root, temp_dir)
                    if rel_path == ".":
                        rel_path = ""
                    
                    # Create corresponding directory in output_dir
                    if rel_path:
                        os.makedirs(os.path.join(output_dir, rel_path), exist_ok=True)
                    
                    # Decrypt each file
                    for file in files:
                        if file.endswith(DEFAULT_ENCRYPTION_EXTENSION):
                            src_file = os.path.join(root, file)
                            dst_file = os.path.join(output_dir, rel_path, file[:-len(DEFAULT_ENCRYPTION_EXTENSION)])
                            self._decrypt_file(src_file, dst_file)
            else:
                # This might be a regular zip file, just extract it
                shutil.rmtree(output_dir)
                shutil.copytree(temp_dir, output_dir)
            
        except Exception as e:
            raise ValueError(f"Failed to decrypt directory: {str(e)}")
        
        finally:
            # Clean up temporary files
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            if os.path.exists(temp_zip):
                os.remove(temp_zip)
    
    def cancel(self):
        self.is_cancelled = True

# Custom UI Components
class ProgressDialog(QDialog):
    """Dialog showing operation progress"""
    def __init__(self, parent=None, title="Operation Progress"):
        super().__init__(parent)
        self.setWindowTitle(title)
        # CUSTOMIZABLE: Progress dialog dimensions
        self.setMinimumSize(400, 150)  # Width, height
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        
        layout = QVBoxLayout(self)
        # CUSTOMIZABLE: Progress dialog padding
        layout.setContentsMargins(20, 20, 20, 20)  # Left, top, right, bottom
        layout.setSpacing(16)  # CUSTOMIZABLE: Spacing between elements
        
        # Status label
        self.status_label = QLabel("Processing files...")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        layout.addWidget(self.progress_bar)
        
        # Progress text
        self.progress_text = QLabel("0 / 0 files")
        self.progress_text.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.progress_text)
        
        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("dangerButton")
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(self.cancel_button)
    
    def update_progress(self, current: int, total: int):
        """Update the progress bar and text"""
        percentage = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(percentage)
        self.progress_text.setText(f"{current} / {total} files")
    
    def update_status(self, status: str):
        """Update the status label"""
        self.status_label.setText(status)

class SidebarButton(QPushButton):
    """Custom button for the sidebar"""
    def __init__(self, text, parent=None, icon=None):
        super().__init__(text, parent)
        self.setObjectName("sidebarButton")
        self.setCheckable(True)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        
        if icon:
            self.setIcon(icon)
            # CUSTOMIZABLE: Sidebar button icon size
            self.setIconSize(QSize(32, 32))  # Width, height

class OptionButton(QPushButton):
    """Custom button for options"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setObjectName("optionButton")
        self.setCheckable(True)
        self.setCursor(QCursor(Qt.PointingHandCursor))

class PasswordLineEdit(QLineEdit):
    """Custom line edit for passwords with show/hide toggle"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEchoMode(QLineEdit.Password)
        
        # Create the show/hide button
        self.toggle_button = QToolButton(self)
        self.toggle_button.setCursor(Qt.PointingHandCursor)
        
        # Create eye icons for show/hide
        self.show_icon = QIcon()
        self.hide_icon = QIcon()
        
        # Create eye icon (show password)
        # CUSTOMIZABLE: Password toggle icon size
        show_pixmap = QPixmap(24, 24)  # Width, height
        show_pixmap.fill(Qt.transparent)
        show_painter = QPainter(show_pixmap)
        show_painter.setRenderHint(QPainter.Antialiasing)
        show_painter.setPen(QPen(QColor(AppTheme.TEXT_PRIMARY), 2))
        show_painter.setBrush(Qt.NoBrush)
        show_painter.drawEllipse(4, 8, 16, 8)
        show_painter.drawEllipse(10, 8, 4, 8)
        show_painter.end()
        self.show_icon = QIcon(show_pixmap)
        
        # Create eye-off icon (hide password)
        hide_pixmap = QPixmap(24, 24)
        hide_pixmap.fill(Qt.transparent)
        hide_painter = QPainter(hide_pixmap)
        hide_painter.setRenderHint(QPainter.Antialiasing)
        hide_painter.setPen(QPen(QColor(AppTheme.TEXT_PRIMARY), 2))
        hide_painter.setBrush(Qt.NoBrush)
        hide_painter.drawEllipse(4, 8, 16, 8)
        hide_painter.drawEllipse(10, 8, 4, 8)
        hide_painter.drawLine(4, 4, 20, 20)
        hide_painter.end()
        self.hide_icon = QIcon(hide_pixmap)
        
        # Set initial icon
        self.toggle_button.setIcon(self.show_icon)
        self.toggle_button.setToolTip("Show Password")
        self.toggle_button.setStyleSheet("background: transparent; border: none;")
        
        # Position the button
        self.toggle_button.clicked.connect(self.toggle_password_visibility)
        
        # Add button to layout
        layout = QHBoxLayout(self)
        # CUSTOMIZABLE: Password toggle button position
        layout.setContentsMargins(0, 0, 5, 0)  # Left, top, right, bottom
        layout.addStretch()
        layout.addWidget(self.toggle_button)
        
        self.setLayout(layout)
    
    def toggle_password_visibility(self):
        """Toggle password visibility"""
        if self.echoMode() == QLineEdit.Password:
            self.setEchoMode(QLineEdit.Normal)
            self.toggle_button.setIcon(self.hide_icon)
            self.toggle_button.setToolTip("Hide Password")
        else:
            self.setEchoMode(QLineEdit.Password)
            self.toggle_button.setIcon(self.show_icon)
            self.toggle_button.setToolTip("Show Password")

class FilePreviewPanel(QFrame):
    """Panel for previewing files and showing properties"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        
        layout = QVBoxLayout(self)
        # CUSTOMIZABLE: Preview panel padding
        layout.setContentsMargins(10, 10, 10, 10)  # Left, top, right, bottom
        layout.setSpacing(10)  # CUSTOMIZABLE: Spacing between elements
        
        # Preview section
        preview_section = QVBoxLayout()
        
        # Preview title
        self.title_label = QLabel("File Preview")
        self.title_label.setObjectName("headerLabel")
        preview_section.addWidget(self.title_label)
        
        # Preview content
        self.preview_content = QLabel("Select a file to preview")
        self.preview_content.setAlignment(Qt.AlignCenter)
        # CUSTOMIZABLE: Preview content height
        self.preview_content.setMinimumHeight(150)
        preview_section.addWidget(self.preview_content)
        
        layout.addLayout(preview_section)
        
        # Separator
        separator = QFrame()
        separator.setObjectName("separator")
        separator.setFrameShape(QFrame.HLine)
        layout.addWidget(separator)
        
        # Properties section
        properties_section = QVBoxLayout()
        
        # Properties title
        self.properties_title = QLabel("File Properties")
        self.properties_title.setObjectName("subHeaderLabel")
        properties_section.addWidget(self.properties_title)
        
        # Properties content
        self.properties_content = QTextEdit()
        self.properties_content.setReadOnly(True)
        # CUSTOMIZABLE: Properties content height
        self.properties_content.setMinimumHeight(150)
        properties_section.addWidget(self.properties_content)
        
        layout.addLayout(properties_section)
        
        # Current file path
        self.current_file = None
    
    def set_file(self, file_path):
        """Set the file to preview and show properties"""
        self.current_file = file_path
        
        if not file_path or not os.path.exists(file_path):
            self.preview_content.setText("No file selected")
            self.properties_content.setText("No file selected")
            return
        
        try:
            # Get file information for properties
            file_name = os.path.basename(file_path)
            created_date = get_file_date(file_path, "created")
            modified_date = get_file_date(file_path, "modified")
            
            properties_text = f"<b>Name:</b> {file_name}<br>"
            properties_text += f"<b>Path:</b> {file_path}<br>"
            properties_text += f"<b>Created:</b> {created_date.strftime('%Y-%m-%d %H:%M:%S')}<br>"
            properties_text += f"<b>Modified:</b> {modified_date.strftime('%Y-%m-%d %H:%M:%S')}<br>"
            
            if os.path.isdir(file_path):
                # Count items in directory
                try:
                    items = os.listdir(file_path)
                    num_files = len([i for i in items if os.path.isfile(os.path.join(file_path, i))])
                    num_dirs = len([i for i in items if os.path.isdir(os.path.join(file_path, i))])
                    
                    # Calculate directory size
                    dir_size = get_directory_size(file_path)
                    
                    properties_text += f"<b>Type:</b> Folder<br>"
                    properties_text += f"<b>Size:</b> {format_size(dir_size)}<br>"
                    properties_text += f"<b>Contents:</b> {len(items)} items ({num_files} files, {num_dirs} folders)<br>"
                    
                    # Show folder icon for preview
                    icon = FileIcons.get_file_icon(file_path)
                    pixmap = icon.pixmap(128, 128)
                    self.preview_content.setPixmap(pixmap)
                except:
                    properties_text += f"<b>Type:</b> Folder<br>"
                    properties_text += f"<b>Contents:</b> Unable to read folder contents<br>"
                    
                    # Show folder icon for preview
                    icon = FileIcons.get_file_icon(file_path)
                    pixmap = icon.pixmap(128, 128)
                    self.preview_content.setPixmap(pixmap)
            else:
                # File properties
                file_size = os.path.getsize(file_path)
                file_type = get_file_category(file_path)
                
                properties_text += f"<b>Type:</b> {file_type}<br>"
                properties_text += f"<b>Size:</b> {format_size(file_size)}<br>"
                
                # Add file extension
                _, ext = os.path.splitext(file_path)
                if ext:
                    properties_text += f"<b>Extension:</b> {ext}<br>"
                
                # Update preview based on file type
                if file_type == "Images":
                    try:
                        pixmap = QPixmap(file_path)
                        if not pixmap.isNull():
                            # Scale to fit while maintaining aspect ratio
                            pixmap = pixmap.scaled(
                                self.preview_content.width(), 
                                self.preview_content.height(),
                                Qt.KeepAspectRatio, 
                                Qt.SmoothTransformation
                            )
                            self.preview_content.setPixmap(pixmap)
                        else:
                            # If image loading fails, show icon
                            icon = FileIcons.get_file_icon(file_path)
                            pixmap = icon.pixmap(128, 128)
                            self.preview_content.setPixmap(pixmap)
                    except:
                        # If image loading fails, show icon
                        icon = FileIcons.get_file_icon(file_path)
                        pixmap = icon.pixmap(128, 128)
                        self.preview_content.setPixmap(pixmap)
                else:
                    # For non-image files, show icon
                    icon = FileIcons.get_file_icon(file_path)
                    pixmap = icon.pixmap(128, 128)
                    self.preview_content.setPixmap(pixmap)
            
            # Set the properties text
            self.properties_content.setHtml(properties_text)
            
        except Exception as e:
            self.properties_content.setText(f"Error getting properties: {str(e)}")
            
            # Show default icon for preview
            icon = FileIcons.get_file_icon(file_path)
            pixmap = icon.pixmap(128, 128)
            self.preview_content.setPixmap(pixmap)

class FileTileWidget(QFrame):
    """Widget for displaying a file as a tile"""
    clicked = pyqtSignal(str)  # Signal emitted when tile is clicked
    double_clicked = pyqtSignal(str)  # Signal emitted when tile is double-clicked
    right_clicked = pyqtSignal(str, QPoint)  # Signal emitted when tile is right-clicked
    
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setObjectName("tile")
        # CUSTOMIZABLE: File tile size
        self.setFixedSize(150, 150)  # Width, height
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.selected = False
        
        layout = QVBoxLayout(self)
        # CUSTOMIZABLE: Tile internal padding
        layout.setContentsMargins(8, 8, 8, 8)  # Left, top, right, bottom
        layout.setSpacing(4)  # CUSTOMIZABLE: Spacing between tile elements
        layout.setAlignment(Qt.AlignCenter)
        
        # File icon/thumbnail
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        
        # Set thumbnail based on file type
        pixmap = get_file_thumbnail(file_path)
        self.icon_label.setPixmap(pixmap)
        
        layout.addWidget(self.icon_label)
        
        # File name (truncated if too long)
        file_name = os.path.basename(file_path)
        display_name = file_name
        if len(file_name) > 18:
            display_name = file_name[:18] + "..."
        
        self.name_label = QLabel(display_name)
        self.name_label.setObjectName("tileLabel")
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setWordWrap(True)
        self.name_label.setToolTip(file_name)  # Show full name on hover
        
        layout.addWidget(self.name_label)
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        # CUSTOMIZABLE: Tile shadow properties
        shadow.setBlurRadius(10)  # Shadow blur radius
        shadow.setColor(QColor(0, 0, 0, 80))  # Shadow color and opacity
        shadow.setOffset(0, 2)  # Shadow offset (x, y)
        self.setGraphicsEffect(shadow)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.file_path)
        elif event.button() == Qt.RightButton:
            self.right_clicked.emit(self.file_path, event.globalPos())
        super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit(self.file_path)
        super().mouseDoubleClickEvent(event)
    
    def set_selected(self, selected):
        """Set the selected state of the tile"""
        self.selected = selected
        if selected:
             
            self.setStyleSheet("QFrame#tile { border: 2px solid #6C5CE7; background-color: rgba(108, 92, 231, 0.2); }")
        else:
            self.setStyleSheet("")

class FileTileView(QScrollArea):
    """Widget for displaying files as tiles in a grid"""
    file_clicked = pyqtSignal(str)  # Signal emitted when a file is clicked
    file_double_clicked = pyqtSignal(str)  # Signal emitted when a file is double-clicked
    file_right_clicked = pyqtSignal(str, QPoint)  # Signal emitted when a file is right-clicked
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Container widget
        self.container = QWidget()
        self.setWidget(self.container)
        
        # Grid layout for tiles
        self.grid_layout = QGridLayout(self.container)
        # CUSTOMIZABLE: Grid layout margins
        self.grid_layout.setContentsMargins(16, 16, 16, 16)  # Left, top, right, bottom
        self.grid_layout.setSpacing(16)  # CUSTOMIZABLE: Spacing between tiles
        
        # List of files
        self.files = []
        self.filtered_files = []
        self.current_category = "All Files"
        self.search_text = ""
        self.show_files = True
        self.show_folders = True
        
        # Selected files
        self.selected_files = set()
        self.tile_widgets = {}  # Map of file paths to tile widgets
        
        # Accept drops
        self.setAcceptDrops(True)
        
        # Timer to prevent flashing during drag and drop
        self.update_timer = QTimer(self)
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self._update_layout)
        
        # Install event filter to handle keyboard events
        self.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """Event filter to handle keyboard events"""
        if event.type() == QEvent.KeyPress:
            # Check if backspace key is pressed
            if event.key() == Qt.Key_Backspace:
                # Emit a signal that can be caught by the main window
                if hasattr(self, 'parent') and self.parent():
                    # Find the main window
                    main_window = self.parent()
                    while main_window and not isinstance(main_window, QMainWindow):
                        main_window = main_window.parent()
                    
                    if main_window and hasattr(main_window, 'navigate_to_parent_folder'):
                        main_window.navigate_to_parent_folder()
                        return True
        
        return super().eventFilter(obj, event)
    
    def clear(self):
        """Clear all tiles"""
        # Remove all widgets from the layout
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.files = []
        self.filtered_files = []
        self.selected_files.clear()
        self.tile_widgets.clear()
    
    def add_file(self, file_path):
        """Add a file to the view"""
        if file_path in self.files:
            return
        
        self.files.append(file_path)
        self._apply_filters()
        # Use timer to batch updates and prevent flashing
        self.update_timer.start(100)
    
    def add_files(self, file_paths):
        """Add multiple files to the view"""
        added = False
        for file_path in file_paths:
            if file_path not in self.files:
                self.files.append(file_path)
                added = True
        
        if added:
            self._apply_filters()
            # Use timer to batch updates and prevent flashing
            self.update_timer.start(100)
    
    def remove_file(self, file_path):
        """Remove a file from the view"""
        if file_path in self.files:
            self.files.remove(file_path)
            if file_path in self.selected_files:
                self.selected_files.remove(file_path)
            self._apply_filters()
            # Use timer to batch updates and prevent flashing
            self.update_timer.start(100)
    
    def set_category_filter(self, category):
        """Set the category filter"""
        self.current_category = category
        self._apply_filters()
        self.update_timer.start(100)
    
    def set_search_filter(self, search_text):
        """Set the search filter"""
        self.search_text = search_text.lower()
        self._apply_filters()
        self.update_timer.start(100)
    
    def set_file_folder_filter(self, show_files, show_folders):
        """Set whether to show files and/or folders"""
        self.show_files = show_files
        self.show_folders = show_folders
        self._apply_filters()
        self.update_timer.start(100)
    
    def _apply_filters(self):
        """Apply category and search filters to the file list"""
        # Start with all files
        filtered = []
        
        # Apply file/folder filter
        for f in self.files:
            try:
                is_dir = os.path.isdir(f)
                if (is_dir and self.show_folders) or (not is_dir and self.show_files):
                    filtered.append(f)
            except Exception as e:
                logger.error(f"Error checking if path is directory: {f}, {str(e)}")
        
        # Apply category filter
        if self.current_category != "All Files" and self.current_category not in ["Files", "Folders"]:
            filtered = [f for f in filtered if not os.path.isdir(f) and get_file_category(f) == self.current_category]
        elif self.current_category == "Files":
            filtered = [f for f in filtered if not os.path.isdir(f)]
        elif self.current_category == "Folders":
            filtered = [f for f in filtered if os.path.isdir(f)]
        
        # Apply search filter
        if self.search_text:
            filtered = [f for f in filtered if self.search_text in os.path.basename(f).lower()]
        
        self.filtered_files = filtered
    
    def _update_layout(self):
        """Update the grid layout with current files"""
        # Clear the layout
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
        # Clear the tile widgets dictionary
        self.tile_widgets.clear()
    
        # Calculate number of columns based on container width
        container_width = self.viewport().width()
        tile_width = 150 + self.grid_layout.spacing()  # CUSTOMIZABLE: Tile width calculation
        columns = max(1, container_width // tile_width)
    
        # Add tiles to the layout
        for i, file_path in enumerate(self.filtered_files):
            row = i // columns
            col = i % columns
        
            # Create the tile widget
            tile = FileTileWidget(file_path)
        
            # Connect signals before adding to dictionary to avoid race conditions
            tile.clicked.connect(self._on_tile_clicked)
            tile.double_clicked.connect(self.file_double_clicked.emit)
            tile.right_clicked.connect(self.file_right_clicked.emit)
        
            # Add to layout
            self.grid_layout.addWidget(tile, row, col)
        
            # Add to dictionary after adding to layout
            self.tile_widgets[file_path] = tile
        
            # Set selected state if applicable
            if file_path in self.selected_files:
                tile.set_selected(True)
    
    def _on_tile_clicked(self, file_path):
        """Handle tile click with selection support"""
        # Check if Ctrl key is pressed for multi-select
        modifiers = QApplication.keyboardModifiers()
        
        # First check if the file_path exists in the tile_widgets dictionary
        if file_path not in self.tile_widgets:
            # Log the issue but don't crash - just return early
            logger.warning(f"Tile widget for {file_path} not found in tile_widgets dictionary")
            # Try to find the file in our files list and add it to the selection if it exists
            if file_path in self.files:
                self.selected_files.add(file_path)
                # Still emit the clicked signal so the file gets previewed
                self.file_clicked.emit(file_path)
            return
    
        if modifiers == Qt.ControlModifier:
            # Toggle selection
            if file_path in self.selected_files:
                self.selected_files.remove(file_path)
                self.tile_widgets[file_path].set_selected(False)
            else:
                self.selected_files.add(file_path)
                self.tile_widgets[file_path].set_selected(True)
        elif modifiers == Qt.ShiftModifier and self.selected_files:
            # Range selection
            last_selected = list(self.selected_files)[-1]
            # Make sure both files are in the filtered_files list
            if last_selected in self.filtered_files and file_path in self.filtered_files:
                start_idx = self.filtered_files.index(last_selected)
                end_idx = self.filtered_files.index(file_path)
            
                # Swap if needed to ensure start_idx <= end_idx
                if start_idx > end_idx:
                    start_idx, end_idx = end_idx, start_idx
            
                # Select all files in the range
                for i in range(start_idx, end_idx + 1):
                    file_to_select = self.filtered_files[i]
                    self.selected_files.add(file_to_select)
                    # Check if the file_to_select exists in tile_widgets before setting it as selected
                    if file_to_select in self.tile_widgets:
                        self.tile_widgets[file_to_select].set_selected(True)
        else:
            # Clear previous selection
            for f in list(self.selected_files):  # Create a copy of the set to avoid modification during iteration
                if f in self.tile_widgets:
                    self.tile_widgets[f].set_selected(False)
        
            self.selected_files.clear()
            self.selected_files.add(file_path)
            self.tile_widgets[file_path].set_selected(True)
    
        # Emit the clicked signal
        self.file_clicked.emit(file_path)
    
    def get_selected_files(self):
        """Get the list of selected files"""
        return list(self.selected_files)
    
    def resizeEvent(self, event):
        """Handle resize events to update the layout"""
        super().resizeEvent(event)
        # Use timer to batch updates and prevent flashing
        self.update_timer.start(100)
    
    def dragEnterEvent(self, event):
        """Handle drag enter events"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dragMoveEvent(self, event):
        """Handle drag move events"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        """Handle drop events"""
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
            
            file_paths = []
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    file_paths.append(file_path)
            
            self.add_files(file_paths)

# Main application window
class MainWindow(QMainWindow):
    """Main application window"""
    def __init__(self):
        super().__init__()
        
        # Remove default window frame and set frameless window
        self.setWindowFlags(Qt.FramelessWindowHint)
        
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        # CUSTOMIZABLE: Main window minimum size
        self.setMinimumSize(1200, 800)  # Width, height
        
        # Initialize workers
        self.organizer_worker = None
        self.encryption_worker = None
        
        # Navigation history
        self.path_history = []
        self.current_path_index = -1
        
        # Set up the UI
        self.setup_ui()
        
        # Connect signals and slots
        self.connect_signals()
        
        # Navigate to user's desktop by default
        desktop_path = os.path.join(get_user_home_dir(), "Desktop")
        if os.path.exists(desktop_path):
            self.path_input.setText(desktop_path)
            self.navigate_to_path()
        
        # Show window maximized
        self.showMaximized()
        
        # Variables for window dragging
        self.dragging = False
        self.drag_position = None
    
    def setup_ui(self):
        """Set up the main UI components"""
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Add custom title bar
        self.setup_title_bar(main_layout)
        
        # Content layout
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # ===== CUSTOMIZABLE: SIDEBAR =====
        # Sidebar - Made wider as requested
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(280)  # CUSTOMIZABLE: Sidebar width
        
        sidebar_layout = QVBoxLayout(sidebar)
        # CUSTOMIZABLE: Sidebar padding
        sidebar_layout.setContentsMargins(0, 20, 0, 20)  # Left, top, right, bottom
        sidebar_layout.setSpacing(2)  # CUSTOMIZABLE: Spacing between sidebar items
        
        # App title in sidebar
        app_title = QLabel(APP_NAME)
        app_title.setObjectName("headerLabel")
        app_title.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(app_title)
        sidebar_layout.addSpacing(20)  # CUSTOMIZABLE: Space after title
        
        # Category buttons with icons
        self.category_buttons = []
        
        # All button with icon
        all_button = SidebarButton("All Files", icon=FileIcons.create_folder_icon())
        all_button.setChecked(True)
        sidebar_layout.addWidget(all_button)
        self.category_buttons.append(all_button)
        
        # Files and Folders buttons
        files_button = SidebarButton("Files", icon=FileIcons.create_icon("#FFA500", "FILE"))
        sidebar_layout.addWidget(files_button)
        self.category_buttons.append(files_button)
        
        folders_button = SidebarButton("Folders", icon=FileIcons.create_folder_icon())
        sidebar_layout.addWidget(folders_button)
        self.category_buttons.append(folders_button)
        
        # Add a separator
        separator = QFrame()
        separator.setObjectName("separator")
        separator.setFrameShape(QFrame.HLine)
        sidebar_layout.addWidget(separator)
        
        # Category buttons with icons - made bigger
        for category in FILE_CATEGORIES.keys():
            # Create icon with category-specific color
            if category == "Images":
                icon = FileIcons.create_icon("#FF7675", "IMG")
            elif category == "Videos":
                icon = FileIcons.create_icon("#6C5CE7", "VID")
            elif category == "Audio":
                icon = FileIcons.create_icon("#00B894", "AUD")
            elif category == "Documents":
                icon = FileIcons.create_icon("#0984E3", "DOC")
            elif category == "PDF":
                icon = FileIcons.create_icon("#E84393", "PDF")
            elif category == "Excel":
                icon = FileIcons.create_icon("#00B894", "XLS")
            elif category == "PowerPoint":
                icon = FileIcons.create_icon("#E84393", "PPT")
            elif category == "Text":
                icon = FileIcons.create_icon("#74B9FF", "TXT")
            elif category == "Archives":
                icon = FileIcons.create_icon("#A29BFE", "ZIP")
            elif category == "Code":
                icon = FileIcons.create_icon("#00CEC9", "CODE")
            elif category == "Executables":
                icon = FileIcons.create_icon("#FD79A8", "EXE")
            elif category == "APK":
                icon = FileIcons.create_icon("#55EFC4", "APK")
            elif category == "Encrypted":
                icon = FileIcons.create_icon("#636E72", "ENC")
            else:
                icon = FileIcons.create_icon("#B2BEC3", "FILE")
            
            button = SidebarButton(category, icon=icon)
            sidebar_layout.addWidget(button)
            self.category_buttons.append(button)
        
        sidebar_layout.addStretch()
        
        # Add to content layout
        content_layout.addWidget(sidebar)
        
        # ===== CUSTOMIZABLE: CONTENT AREA =====
        # Content area
        content_widget = QWidget()
        content_area_layout = QVBoxLayout(content_widget)
        # CUSTOMIZABLE: Content area padding
        content_area_layout.setContentsMargins(20, 20, 20, 20)  # Left, top, right, bottom
        content_area_layout.setSpacing(20)  # CUSTOMIZABLE: Spacing between content sections
        
        # Toolbar
        toolbar_widget = QWidget()
        toolbar_layout = QVBoxLayout(toolbar_widget)
        toolbar_layout.setContentsMargins(0, 0, 0, 10)
        toolbar_layout.setSpacing(10)  # CUSTOMIZABLE: Spacing between toolbar elements
        
        # Top toolbar with buttons
        top_toolbar = QHBoxLayout()
        
        # Add files button
        add_files_btn = QPushButton("Add Files")
        add_files_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_FileDialogNewFolder))
        top_toolbar.addWidget(add_files_btn)
        self.add_files_btn = add_files_btn
        
        # Add folder button
        add_folder_btn = QPushButton("Add Folder")
        add_folder_btn.setIcon(FileIcons.create_folder_icon())
        top_toolbar.addWidget(add_folder_btn)
        self.add_folder_btn = add_folder_btn
        
        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("dangerButton")
        clear_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_DialogDiscardButton))
        top_toolbar.addWidget(clear_btn)
        self.clear_btn = clear_btn
        
        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_BrowserReload))
        top_toolbar.addWidget(refresh_btn)
        self.refresh_btn = refresh_btn
        
        top_toolbar.addStretch()
        
        toolbar_layout.addLayout(top_toolbar)
        
        # Bottom toolbar with path and search
        bottom_toolbar = QHBoxLayout()
        
        # Back button - NEW
        self.back_btn = QToolButton()
        self.back_btn.setIcon(FileIcons.create_back_icon())
        self.back_btn.setToolTip("Go to parent folder")
        self.back_btn.setObjectName("backButton")
        # CUSTOMIZABLE: Back button size
        self.back_btn.setFixedSize(40, 38)  # Width, height
        bottom_toolbar.addWidget(self.back_btn)
        
        # Path bar (editable) with integrated browse button
        path_container = QFrame()
        path_container_layout = QHBoxLayout(path_container)
        path_container_layout.setContentsMargins(0, 0, 0, 0)
        path_container_layout.setSpacing(50)
        
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Enter path to navigate...")
        
        # Three-dot button for folder selection with improved styling - Moved to the left
        self.browse_path_btn = QToolButton()
        self.browse_path_btn.setText("〣")
        self.browse_path_btn.setToolTip("Browse for folder")
        self.browse_path_btn.setObjectName("browseButton")
       
        
        # CUSTOMIZABLE: Browse button size
        self.browse_path_btn.setFixedSize(40, 38)  # Width, height
        
        path_container_layout.addWidget(self.path_input)
        path_container_layout.addWidget(self.browse_path_btn)
        
        bottom_toolbar.addWidget(path_container)
        
        # Search bar - Moved to the left after path bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search files...")
        # CUSTOMIZABLE: Search bar width
        self.search_input.setFixedWidth(250)
        bottom_toolbar.addWidget(self.search_input, 0, Qt.AlignLeft)
        
        bottom_toolbar.addStretch()
        
        toolbar_layout.addLayout(bottom_toolbar)
        
        content_area_layout.addWidget(toolbar_widget)
        
        # ===== CUSTOMIZABLE: MAIN CONTENT AREA =====
        # Main content area with preview panel and file view
        main_content = QSplitter(Qt.Horizontal)
        
        # File view
        self.file_view = FileTileView()
        
        # Right side panels
        right_panel = QSplitter(Qt.Vertical)
        
        # Combined preview and properties panel - Moved to the top
        self.preview_panel = FilePreviewPanel()
        
        # Operation tabs
        tabs = QTabWidget()
        
        # Organize tab
        organize_tab = QWidget()
        organize_layout = QVBoxLayout(organize_tab)
        # CUSTOMIZABLE: Organize tab padding
        organize_layout.setContentsMargins(20, 20, 20, 20)  # Left, top, right, bottom
        organize_layout.setSpacing(20)  # CUSTOMIZABLE: Spacing between organize tab elements
        
        # Organization options
        organize_options_group = QGroupBox("Organization Options")
        organize_options_layout = QVBoxLayout(organize_options_group)
        # CUSTOMIZABLE: Organization options group padding
        organize_options_layout.setContentsMargins(20, 30, 20, 20)  # Left, top, right, bottom
        organize_options_layout.setSpacing(20)  # CUSTOMIZABLE: Spacing between organization options
        
        # Organize by options
        organize_by_label = QLabel("Organize by:")
        organize_by_label.setObjectName("subHeaderLabel")
        organize_options_layout.addWidget(organize_by_label)
        
        organize_buttons_layout = QHBoxLayout()
        organize_buttons_layout.setSpacing(10)  # CUSTOMIZABLE: Spacing between organize buttons
        
        self.organize_by_type_btn = OptionButton("File Type")
        self.organize_by_type_btn.setChecked(True)
        organize_buttons_layout.addWidget(self.organize_by_type_btn)
        
        self.organize_by_date_btn = OptionButton("Date")
        organize_buttons_layout.addWidget(self.organize_by_date_btn)
        
        self.organize_by_both_btn = OptionButton("Both")
        organize_buttons_layout.addWidget(self.organize_by_both_btn)
        
        organize_options_layout.addLayout(organize_buttons_layout)
        
        # Create button group for mutual exclusivity
        self.organize_button_group = QButtonGroup(self)
        self.organize_button_group.addButton(self.organize_by_type_btn)
        self.organize_button_group.addButton(self.organize_by_date_btn)
        self.organize_button_group.addButton(self.organize_by_both_btn)
        self.organize_button_group.setExclusive(True)
        
        # Destination folder
        dest_folder_label = QLabel("Destination Folder:")
        dest_folder_label.setObjectName("subHeaderLabel")
        organize_options_layout.addWidget(dest_folder_label)
        
        dest_folder_layout = QHBoxLayout()
        self.dest_folder_input = QLineEdit()
        self.dest_folder_input.setPlaceholderText("Same as source folder")
        
        self.browse_dest_btn = QPushButton("Browse...")
        
        dest_folder_layout.addWidget(self.dest_folder_input)
        dest_folder_layout.addWidget(self.browse_dest_btn)
        
        organize_options_layout.addLayout(dest_folder_layout)
        
        # Additional options
        self.remove_originals_check = QCheckBox("Remove original files after organizing")
        organize_options_layout.addWidget(self.remove_originals_check)
        
        organize_options_layout.addStretch()
        
        # Organize button
        self.organize_btn = QPushButton("Organize Files")
        self.organize_btn.setObjectName("successButton")
        self.organize_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_DialogApplyButton))
        organize_options_layout.addWidget(self.organize_btn)
        
        organize_layout.addWidget(organize_options_group)
        organize_layout.addStretch()
        
        # Encrypt tab - Modified to have separate encrypt and decrypt buttons
        encrypt_tab = QWidget()
        encrypt_layout = QVBoxLayout(encrypt_tab)
        # CUSTOMIZABLE: Encrypt tab padding
        encrypt_layout.setContentsMargins(20, 20, 20, 20)  # Left, top, right, bottom
        encrypt_layout.setSpacing(20)  # CUSTOMIZABLE: Spacing between encrypt tab elements
        
        # Encryption options
        encrypt_options_group = QGroupBox("Encryption Options")
        encrypt_options_layout = QVBoxLayout(encrypt_options_group)
        # CUSTOMIZABLE: Encryption options group padding
        encrypt_options_layout.setContentsMargins(20, 30, 20, 20)  # Left, top, right, bottom
        encrypt_options_layout.setSpacing(20)  # CUSTOMIZABLE: Spacing between encryption options
        
        # Password
        password_label = QLabel("Password:")
        password_label.setObjectName("subHeaderLabel")
        encrypt_options_layout.addWidget(password_label)
        
        self.password_input = PasswordLineEdit()
        self.password_input.setPlaceholderText("Enter password")
        encrypt_options_layout.addWidget(self.password_input)
        
        confirm_label = QLabel("Confirm Password:")
        confirm_label.setObjectName("subHeaderLabel")
        encrypt_options_layout.addWidget(confirm_label)
        
        self.confirm_password_input = PasswordLineEdit()
        self.confirm_password_input.setPlaceholderText("Confirm password")
        encrypt_options_layout.addWidget(self.confirm_password_input)
        
        # Additional options
        self.remove_after_encrypt_check = QCheckBox("Remove original files after encryption/decryption")
        encrypt_options_layout.addWidget(self.remove_after_encrypt_check)
        
        encrypt_options_layout.addStretch()
        
        # Separate Encrypt and Decrypt buttons
        buttons_layout = QHBoxLayout()
        
        # Encrypt button
        self.encrypt_btn = QPushButton("Encrypt Files")
        self.encrypt_btn.setObjectName("successButton")
        buttons_layout.addWidget(self.encrypt_btn)
        
        # Decrypt button
        self.decrypt_btn = QPushButton("Decrypt Files")
        self.decrypt_btn.setObjectName("dangerButton")
        buttons_layout.addWidget(self.decrypt_btn)
        
        encrypt_options_layout.addLayout(buttons_layout)
        
        encrypt_layout.addWidget(encrypt_options_group)
        encrypt_layout.addStretch()
        
        # Add tabs
        tabs.addTab(organize_tab, "Organize")
        tabs.addTab(encrypt_tab, "Encrypt/Decrypt")
        
        # Add panels to right side - Preview panel is already at the top
        right_panel.addWidget(self.preview_panel)
        right_panel.addWidget(tabs)
        # CUSTOMIZABLE: Panel size ratio
        right_panel.setSizes([350, 450])  # Adjusted sizes to give more space to operation panels
        
        # Add file view and right panel to main content
        main_content.addWidget(self.file_view)
        main_content.addWidget(right_panel)
        # CUSTOMIZABLE: Main content panel ratio
        main_content.setSizes([700, 500])  # Initial sizes
        
        content_area_layout.addWidget(main_content)
        
        # Add to content layout
        content_layout.addWidget(content_widget)
        
        # Add content layout to main layout
        main_layout.addLayout(content_layout)
        
        # Status bar
        self.statusBar()
        
        # Context menu for file operations
        self.file_context_menu = QMenu(self)
        self.open_action = QAction("Open", self)
        self.open_location_action = QAction("Open Location", self)
        self.rename_action = QAction("Rename", self)
        self.move_action = QAction("Move", self)
        self.copy_action = QAction("Copy", self)
        self.delete_action = QAction("Delete", self)
        
        self.file_context_menu.addAction(self.open_action)
        self.file_context_menu.addAction(self.open_location_action)
        self.file_context_menu.addAction(self.rename_action)
        self.file_context_menu.addAction(self.move_action)
        self.file_context_menu.addAction(self.copy_action)
        self.file_context_menu.addAction(self.delete_action)
    
    def setup_title_bar(self, main_layout):
        """Set up custom title bar with window controls"""
        title_bar = QFrame()
        title_bar.setObjectName("titleBar")
        title_bar.setFixedHeight(40)  # CUSTOMIZABLE: Title bar height
        
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(10, 0, 10, 0)  # CUSTOMIZABLE: Title bar padding
        
        # App title
        title_label = QLabel(f"{APP_NAME} v{APP_VERSION}")
        title_label.setObjectName("headerLabel")
        title_layout.addWidget(title_label)
        
        title_layout.addStretch()
        
        # Window control buttons
        minimize_btn = QToolButton()
        minimize_btn.setObjectName("windowControlButton")
        minimize_btn.setText("—")
        minimize_btn.setToolTip("Minimize")
        minimize_btn.clicked.connect(self.showMinimized)
        
        maximize_btn = QToolButton()
        maximize_btn.setObjectName("windowControlButton")
        maximize_btn.setText("□")
        maximize_btn.setToolTip("Maximize")
        maximize_btn.clicked.connect(self.toggle_maximize)
        
        close_btn = QToolButton()
        close_btn.setObjectName("closeButton windowControlButton")
        close_btn.setText("✕")
        close_btn.setToolTip("Close")
        close_btn.clicked.connect(self.close)
        
        title_layout.addWidget(minimize_btn)
        title_layout.addWidget(maximize_btn)
        title_layout.addWidget(close_btn)
        
        main_layout.addWidget(title_bar)
        
        # Make title bar draggable
        title_bar.mousePressEvent = self.title_bar_mouse_press
        title_bar.mouseMoveEvent = self.title_bar_mouse_move
        title_bar.mouseReleaseEvent = self.title_bar_mouse_release
    
    def title_bar_mouse_press(self, event):
        """Handle mouse press events on the title bar"""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def title_bar_mouse_move(self, event):
        """Handle mouse move events on the title bar"""
        if event.buttons() == Qt.LeftButton and self.dragging:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
    
    def title_bar_mouse_release(self, event):
        """Handle mouse release events on the title bar"""
        self.dragging = False
    
    def toggle_maximize(self):
        """Toggle between maximized and normal window state"""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
    
    def connect_signals(self):
        """Connect signals and slots"""
        # File browser buttons
        self.add_files_btn.clicked.connect(self.add_files)
        self.add_folder_btn.clicked.connect(self.add_folder)
        self.clear_btn.clicked.connect(self.clear_files)
        self.refresh_btn.clicked.connect(self.refresh_files)
        
        # Path input and browse button
        self.path_input.returnPressed.connect(self.navigate_to_path)
        self.browse_path_btn.clicked.connect(self.browse_path)
        
        # Back button - NEW
        self.back_btn.clicked.connect(self.navigate_to_parent_folder)
        
        # Search input
        self.search_input.textChanged.connect(self.search_files)
        
        # Organize tab
        self.browse_dest_btn.clicked.connect(self.browse_destination)
        self.organize_btn.clicked.connect(self.start_organize)
        
        # Encrypt/Decrypt tab - Modified for separate buttons
        self.encrypt_btn.clicked.connect(lambda: self.start_encryption("encrypt"))
        self.decrypt_btn.clicked.connect(lambda: self.start_encryption("decrypt"))
        
        # Category buttons
        for button in self.category_buttons:
            button.clicked.connect(self.filter_by_category)
        
        # File view
        self.file_view.file_clicked.connect(self.preview_file)
        self.file_view.file_double_clicked.connect(self.open_file)
        self.file_view.file_right_clicked.connect(self.show_file_context_menu)
        
        # Context menu actions
        self.open_action.triggered.connect(self.open_selected_file)
        self.open_location_action.triggered.connect(self.open_selected_file_location)
        self.rename_action.triggered.connect(self.rename_selected_file)
        self.move_action.triggered.connect(self.move_selected_file)
        self.copy_action.triggered.connect(self.copy_selected_file)
        self.delete_action.triggered.connect(self.delete_selected_file)
    
    def add_files(self):
        """Add files to the view"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Files", "", "All Files (*.*)"
        )
        
        if files:
            self.file_view.add_files(files)
            self.statusBar().showMessage(f"Added {len(files)} files")
    
    def add_folder(self):
        """Add all files from a folder to the view"""
        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder", "", QFileDialog.ShowDirsOnly
        )
        
        if folder:
            self.path_input.setText(folder)
            self.navigate_to_path()
    
    def clear_files(self):
        """Clear the file view"""
        self.file_view.clear()
        self.statusBar().showMessage("Cleared file list")
        self.preview_panel.set_file(None)
    
    def refresh_files(self):
        """Refresh the current view"""
        current_path = self.path_input.text().strip()
        if current_path and os.path.exists(current_path):
            self.navigate_to_path()
            self.statusBar().showMessage(f"Refreshed: {current_path}")
        else:
            self.statusBar().showMessage("Nothing to refresh")
    
    def navigate_to_path(self):
        """Navigate to the path entered in the path input"""
        path = self.path_input.text().strip()
        if not path:
            return
        
        if not os.path.exists(path):
            QMessageBox.warning(self, "Invalid Path", f"The path '{path}' does not exist.")
            return
        
        # Clear current files
        self.file_view.clear()
        
        if os.path.isdir(path):
            # Add files and folders from the directory
            items = []
            try:
                for item in os.listdir(path):
                    item_path = os.path.join(path, item)
                    items.append(item_path)
            
                self.file_view.add_files(items)
                self.statusBar().showMessage(f"Navigated to: {path}")
            
                # Reset category filter to "All Files" when opening a new folder
                for button in self.category_buttons:
                    if button.text() == "All Files":
                        button.setChecked(True)
                    else:
                        button.setChecked(False)
                self.file_view.set_category_filter("All Files")
                self.file_view.set_file_folder_filter(True, True)
            
                # Add to navigation history
                # If we're not at the end of the history, truncate it
                if self.current_path_index < len(self.path_history) - 1:
                    self.path_history = self.path_history[:self.current_path_index + 1]
            
                # Add the new path to history if it's different from the current one
                if not self.path_history or self.path_history[-1] != path:
                    self.path_history.append(path)
                    self.current_path_index = len(self.path_history) - 1
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not read directory: {str(e)}")
                logger.error(f"Error reading directory {path}: {str(e)}")
        else:
            # It's a file, add it to the view
            self.file_view.add_file(path)
            self.statusBar().showMessage(f"Added file: {path}")
    
    def navigate_to_parent_folder(self):
        """Navigate to the parent folder of the current path"""
        current_path = self.path_input.text().strip()
        if not current_path or not os.path.exists(current_path):
            return
        
        # Get the parent directory
        parent_dir = os.path.dirname(current_path)
        
        # If we're already at the root, do nothing
        if parent_dir == current_path:
            return
        
        # Navigate to the parent directory
        self.path_input.setText(parent_dir)
        self.navigate_to_path()
        self.statusBar().showMessage(f"Navigated to parent: {parent_dir}")
    
    def browse_path(self):
        """Browse for a folder to navigate to"""
        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder", self.path_input.text(), QFileDialog.ShowDirsOnly
        )
        
        if folder:
            self.path_input.setText(folder)
            self.navigate_to_path()
    
    def search_files(self, text):
        """Search for files matching the search text"""
        self.file_view.set_search_filter(text)
        
        if not text:
            self.statusBar().showMessage("Search cleared")
        else:
            self.statusBar().showMessage(f"Searching for: {text}")
    
    def browse_destination(self):
        """Browse for destination folder"""
        folder = QFileDialog.getExistingDirectory(
            self, "Select Destination Folder", "", QFileDialog.ShowDirsOnly
        )
        
        if folder:
            self.dest_folder_input.setText(folder)
    
    def filter_by_category(self):
        """Filter files by category"""
        # Get the selected category
        sender = self.sender()
        if not sender:
            return
        
        # Uncheck all other buttons
        for button in self.category_buttons:
            if button != sender:
                button.setChecked(False)
        
        # Set the category filter
        category = sender.text()
        self.file_view.set_category_filter(category)
        
        # Set file/folder filter based on selection
        if category == "Files":
            self.file_view.set_file_folder_filter(True, False)
        elif category == "Folders":
            self.file_view.set_file_folder_filter(False, True)
        else:
            self.file_view.set_file_folder_filter(True, True)
        
        self.statusBar().showMessage(f"Filtering by category: {category}")
    
    def preview_file(self, file_path):
        """Preview a file"""
        # Check if the file still exists before previewing
        if not file_path or not os.path.exists(file_path):
            self.statusBar().showMessage(f"File not found: {file_path}")
            return
        
        self.preview_panel.set_file(file_path)
        self.selected_file = file_path
    
    def open_file(self, file_path):
        """Open a file with the default application or navigate to folder"""
        try:
            if os.path.isdir(file_path):
                # If it's a directory, navigate to it
                self.path_input.setText(file_path)
                self.navigate_to_path()
            else:
                # If it's a file, open it with default application
                if open_file(file_path):
                    self.statusBar().showMessage(f"Opened: {os.path.basename(file_path)}")
                else:
                    self.statusBar().showMessage(f"Failed to open: {os.path.basename(file_path)}")
        except Exception as e:
            logger.error(f"Error opening file {file_path}: {str(e)}")
            QMessageBox.warning(self, "Error", f"Could not open file: {str(e)}")
    
    def show_file_context_menu(self, file_path, position):
        """Show context menu for a file"""
        self.selected_file = file_path
        self.file_context_menu.exec_(position)
    
    def open_selected_file(self):
        """Open the selected file"""
        if hasattr(self, 'selected_file'):
            self.open_file(self.selected_file)
    
    def open_selected_file_location(self):
        """Open the location of the selected file"""
        if hasattr(self, 'selected_file'):
            if open_file_location(self.selected_file):
                self.statusBar().showMessage(f"Opened location: {os.path.dirname(self.selected_file)}")
            else:
                self.statusBar().showMessage(f"Failed to open location")
    
    def rename_selected_file(self):
        """Rename the selected file"""
        if not hasattr(self, 'selected_file'):
            return
        
        file_path = self.selected_file
        old_name = os.path.basename(file_path)
        parent_dir = os.path.dirname(file_path)
        
        new_name, ok = QInputDialog.getText(
            self, "Rename File", "Enter new name:", text=old_name
        )
        
        if ok and new_name and new_name != old_name:
            new_path = os.path.join(parent_dir, new_name)
            
            try:
                # Check if the new name already exists
                if os.path.exists(new_path):
                    QMessageBox.warning(
                        self, "File Exists", 
                        f"A file named '{new_name}' already exists in this location."
                    )
                    return
                
                # Rename the file
                os.rename(file_path, new_path)
                
                # Update the view
                self.file_view.remove_file(file_path)
                self.file_view.add_file(new_path)
                
                # Update preview if needed
                if self.preview_panel.current_file == file_path:
                    self.preview_panel.set_file(new_path)
                
                self.selected_file = new_path
                self.statusBar().showMessage(f"Renamed: {old_name} to {new_name}")
                
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to rename file: {str(e)}"
                )
    
    def move_selected_file(self):
        """Move the selected file to a new location"""
        selected_files = self.file_view.get_selected_files()
        if not selected_files:
            if hasattr(self, 'selected_file'):
                selected_files = [self.selected_file]
            else:
                return
        
        # Get destination folder
        dest_dir = QFileDialog.getExistingDirectory(
            self, "Select Destination Folder", "", QFileDialog.ShowDirsOnly
        )
        
        if not dest_dir:
            return
        
        moved_count = 0
        for file_path in selected_files:
            file_name = os.path.basename(file_path)
            dest_path = os.path.join(dest_dir, file_name)
            
            # Check if destination already exists
            if os.path.exists(dest_path):
                response = QMessageBox.question(
                    self, "File Exists",
                    f"A file named '{file_name}' already exists in the destination. Overwrite?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                
                if response == QMessageBox.No:
                    continue
            
            try:
                # Move the file
                shutil.move(file_path, dest_path)
                
                # Update the view
                self.file_view.remove_file(file_path)
                
                # Update preview if needed
                if self.preview_panel.current_file == file_path:
                    self.preview_panel.set_file(None)
                
                moved_count += 1
                
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to move file {file_name}: {str(e)}"
                )
        
        if moved_count > 0:
            self.statusBar().showMessage(f"Moved {moved_count} files to {dest_dir}")
    
    def copy_selected_file(self):
        """Copy the selected file to a new location"""
        selected_files = self.file_view.get_selected_files()
        if not selected_files:
            if hasattr(self, 'selected_file'):
                selected_files = [self.selected_file]
            else:
                return
        
        # Get destination folder
        dest_dir = QFileDialog.getExistingDirectory(
            self, "Select Destination Folder", "", QFileDialog.ShowDirsOnly
        )
        
        if not dest_dir:
            return
        
        copied_count = 0
        for file_path in selected_files:
            file_name = os.path.basename(file_path)
            dest_path = os.path.join(dest_dir, file_name)
            
            # Check if destination already exists
            if os.path.exists(dest_path):
                response = QMessageBox.question(
                    self, "File Exists",
                    f"A file named '{file_name}' already exists in the destination. Overwrite?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                
                if response == QMessageBox.No:
                    continue
            
            try:
                # Copy the file
                if os.path.isdir(file_path):
                    shutil.copytree(file_path, dest_path)
                else:
                    shutil.copy2(file_path, dest_path)
                
                copied_count += 1
                
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to copy file {file_name}: {str(e)}"
                )
        
        if copied_count > 0:
            self.statusBar().showMessage(f"Copied {copied_count} files to {dest_dir}")
    
    def delete_selected_file(self):
        """Delete the selected file"""
        selected_files = self.file_view.get_selected_files()
        if not selected_files:
            if hasattr(self, 'selected_file'):
                selected_files = [self.selected_file]
            else:
                return
        
        # Confirm deletion
        if len(selected_files) == 1:
            file_name = os.path.basename(selected_files[0])
            message = f"Are you sure you want to delete '{file_name}'?"
        else:
            message = f"Are you sure you want to delete {len(selected_files)} items?"
        
        response = QMessageBox.question(
            self, "Confirm Delete", message,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if response == QMessageBox.No:
            return
        
        deleted_count = 0
        for file_path in selected_files:
            try:
                # Delete the file or directory
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                else:
                    os.remove(file_path)
                
                # Update the view
                self.file_view.remove_file(file_path)
                
                # Update preview if needed
                if self.preview_panel.current_file == file_path:
                    self.preview_panel.set_file(None)
                
                deleted_count += 1
                
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to delete {os.path.basename(file_path)}: {str(e)}"
                )
        
        if deleted_count > 0:
            self.statusBar().showMessage(f"Deleted {deleted_count} items")
    
    def start_organize(self):
        """Start the file organization process"""
        selected_files = self.file_view.get_selected_files()
        if not selected_files:
            selected_files = self.file_view.files
        
        if not selected_files:
            QMessageBox.warning(self, "No Files", "Please add files to organize.")
            return
        
        # Get destination folder
        destination = self.dest_folder_input.text().strip()
        if not destination:
            # Use the first file's directory as default
            destination = os.path.dirname(selected_files[0])
        
        # Check if destination exists
        if not os.path.isdir(destination):
            try:
                os.makedirs(destination)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create destination folder: {str(e)}")
                return
        
        # Get organization method
        if self.organize_by_type_btn.isChecked():
            organize_by = "type"
        elif self.organize_by_date_btn.isChecked():
            organize_by = "date"
        else:
            organize_by = "both"
        
        # Get remove originals option
        remove_originals = self.remove_originals_check.isChecked()
        
        # Create progress dialog
        progress_dialog = ProgressDialog(self, "Organizing Files")
        
        # Create and start worker
        self.organizer_worker = FileOrganizerWorker(
            selected_files, destination, organize_by, remove_originals
        )
        
        # Connect signals
        self.organizer_worker.progress_updated.connect(progress_dialog.update_progress)
        self.organizer_worker.status_updated.connect(progress_dialog.update_status)
        self.organizer_worker.operation_completed.connect(
            lambda success, message: self.on_operation_completed(success, message, progress_dialog)
        )
        
        # Connect cancel button
        progress_dialog.rejected.connect(self.organizer_worker.cancel)
        
        # Start worker
        self.organizer_worker.start()
        
        # Show dialog
        progress_dialog.exec_()
    
    def start_encryption(self, operation):
        """Start the encryption/decryption process"""
        selected_files = self.file_view.get_selected_files()
        if not selected_files:
            selected_files = self.file_view.files
        
        if not selected_files:
            QMessageBox.warning(self, "No Files", "Please add files to process.")
            return
        
        # Get password
        password = self.password_input.text()
        if not password:
            QMessageBox.warning(self, "No Password", "Please enter a password.")
            return
        
        # For encryption, check password confirmation
        if operation == "encrypt":
            confirm_password = self.confirm_password_input.text()
            if password != confirm_password:
                QMessageBox.warning(self, "Password Mismatch", "Passwords do not match.")
                return
        
        # Get remove originals option
        remove_originals = self.remove_after_encrypt_check.isChecked()
        
        # Create progress dialog
        progress_dialog = ProgressDialog(self, f"{operation.capitalize()}ing Files")
        
        # Create and start worker
        self.encryption_worker = EncryptionWorker(
            selected_files, password, operation, remove_originals
        )
        
        # Connect signals
        self.encryption_worker.progress_updated.connect(progress_dialog.update_progress)
        self.encryption_worker.status_updated.connect(progress_dialog.update_status)
        self.encryption_worker.operation_completed.connect(
            lambda success, message: self.on_operation_completed(success, message, progress_dialog)
        )
        
        # Connect cancel button
        progress_dialog.rejected.connect(self.encryption_worker.cancel)
        
        # Start worker
        self.encryption_worker.start()
        
        # Show dialog
        progress_dialog.exec_()
    
    def on_operation_completed(self, success: bool, message: str, dialog: QDialog):
        """Handle operation completion"""
        # Close the progress dialog
        dialog.accept()
        
        # Show message box
        if success:
            QMessageBox.information(self, "Operation Complete", message)
            # Refresh the file view if needed
            self.refresh_files()
        else:
            QMessageBox.critical(self, "Operation Failed", message)
        
        # Update status bar
        self.statusBar().showMessage(message)
    
    def keyPressEvent(self, event):
        """Handle key press events"""
        # Check if backspace key is pressed and we're not in a text field
        if event.key() == Qt.Key_Backspace:
            focused_widget = QApplication.focusWidget()
            if not isinstance(focused_widget, QLineEdit) and not isinstance(focused_widget, QTextEdit):
                self.navigate_to_parent_folder()
                return
        
        super().keyPressEvent(event)

# Application entry point
def main():
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    
    # Set up theme
    AppTheme.setup_application_style(app)
    
    try:
        # Create and show main window
        window = MainWindow()
        window.show()
        
        # Run application
        sys.exit(app.exec_())
    except Exception as e:
        # Log any unhandled exceptions
        logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        # Show error message
        error_dialog = QMessageBox()
        error_dialog.setIcon(QMessageBox.Critical)
        error_dialog.setText("An unexpected error occurred")
        error_dialog.setInformativeText(str(e))
        error_dialog.setWindowTitle("Error")
        error_dialog.exec_()
        sys.exit(1)

if __name__ == "__main__":
    main()