import sys
import os
import re
import shutil
import stat  # For chmod
from pathlib import Path # For easier path manipulation
from functools import partial # For connecting signals with arguments

from PySide6.QtWidgets import (
    QApplication, QDialog, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLineEdit, QLabel, QComboBox, QPlainTextEdit, QCheckBox,
    QGroupBox, QFileDialog, QMessageBox, QStyleFactory, QFormLayout,
    QSizePolicy, QRadioButton, QButtonGroup, QListWidget, QListWidgetItem,
    QAbstractItemView # For selection mode
)
from PySide6.QtCore import (
    Qt, QStandardPaths, QDir, QFile, QSaveFile, QIODevice, QFileInfo, QProcess,
    QSize, # For icon scaling
    QSettings # Added for history
)
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont

# --- Configuration ---
APP_NAME = "Desktop Link Creator"
ORG_NAME = "YourOrg" # Or leave blank if no settings needed yet
SETTINGS_INTERPRETER_HISTORY = "interpreterHistory"
MAX_INTERPRETER_HISTORY = 15 # Limit history size

# --- Standard Freedesktop Categories (add more if needed) ---
DESKTOP_CATEGORIES = [
    "AudioVideo", "Audio", "Video", "Development", "Education", "Game",
    "Graphics", "Network", "Office", "Science", "Settings", "System",
    "Utility", "Accessibility", "Documentation", "Core", "GTK", "Qt", "KDE",
    "GNOME", "ConsoleOnly", "WebBrowser"
]
DESKTOP_CATEGORIES.sort()

# --- Helper Functions ---
# (sanitize_filename, find_executable_on_path, get_best_icon_path remain the same)
def sanitize_filename(name):
    """Creates a safe filename base from the application name."""
    name = name.lower()
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'\s+', '-', name).strip('-')
    return name if name else "unnamed-app"

def find_executable_on_path(name):
    """Checks if an executable exists in the system's PATH."""
    return QStandardPaths.findExecutable(name)

def get_best_icon_path(icon_base_name, icon_ext, size=64):
    """Determines the target path within the user's icon directory."""
    base_icon_dir = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.GenericDataLocation)) / "icons" / "hicolor"
    target_name = f"{icon_base_name}{icon_ext}"

    if icon_ext.lower() == ".svg":
        size_dir = "scalable"
    else:
        standard_sizes = [16, 22, 24, 32, 48, 64, 96, 128, 256, 512]
        closest_size = min(standard_sizes, key=lambda s: abs(s - size))
        size_dir = f"{closest_size}x{closest_size}"

    target_dir = base_icon_dir / size_dir / "apps"
    return target_dir, target_name

# --- Main Application Dialog ---

class DesktopLinkerApp(QDialog):
    def __init__(self):
        super().__init__()
        self.settings = QSettings(ORG_NAME, APP_NAME) # Use QSettings
        self.setWindowTitle(APP_NAME)
        self.setMinimumWidth(650)

        self.script_path = ""
        self.icon_path = ""

        self.init_ui()
        self.load_settings()
        self.connect_signals()
        self.apply_stylesheet()
        self.update_interpreter_state()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)

        form_layout = QFormLayout()
        form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.setHorizontalSpacing(10)
        form_layout.setVerticalSpacing(12)

        # --- Application Name ---
        self.name_edit = QLineEdit()
        self.name_edit.setObjectName("nameEdit")
        self.name_edit.setPlaceholderText("e.g., My Cool App")
        form_layout.addRow("Application &Name:", self.name_edit)

        # --- Script/Program ---
        script_layout = QHBoxLayout()
        self.script_edit = QLineEdit()
        self.script_edit.setObjectName("scriptEdit")
        self.script_edit.setPlaceholderText("Path to the main script or executable")
        self.script_edit.setReadOnly(True)
        self.script_browse_button = QPushButton(QIcon.fromTheme("document-open"), "&Browse...")
        self.script_browse_button.setObjectName("scriptBrowseButton")
        script_layout.addWidget(self.script_edit, 1)
        script_layout.addWidget(self.script_browse_button)
        form_layout.addRow("Script/Program:", script_layout)

        # --- Execution Method ---
        exec_group = QGroupBox("Execution Method")
        exec_group.setObjectName("execGroup")
        exec_layout = QVBoxLayout(exec_group)
        exec_layout.setSpacing(6)
        self.exec_button_group = QButtonGroup(self)
        # (Radio buttons rb_direct, rb_python, etc. added here as before)
        self.rb_direct = QRadioButton("&Direct Executable")
        self.rb_direct.setToolTip("Runs the script/program directly (requires execute permission)")
        self.rb_python = QRadioButton("P&ython3 Script")
        self.rb_python.setToolTip("Runs using 'python3' (found in PATH or specified below)")
        self.rb_java = QRadioButton("&Java JAR")
        self.rb_java.setToolTip("Runs using 'java -jar' (found in PATH or specified below)")
        self.rb_bash = QRadioButton("&Bash Script")
        self.rb_bash.setToolTip("Runs using 'bash' (found in PATH or specified below)")
        self.rb_custom = QRadioButton("C&ustom Command Prefix")
        self.rb_custom.setToolTip("Provide the command/interpreter yourself (e.g., /opt/myprog/run)")
        self.exec_button_group.addButton(self.rb_direct, 0)
        self.exec_button_group.addButton(self.rb_python, 1)
        self.exec_button_group.addButton(self.rb_java, 2)
        self.exec_button_group.addButton(self.rb_bash, 3)
        self.exec_button_group.addButton(self.rb_custom, 4)
        exec_layout.addWidget(self.rb_direct)
        exec_layout.addWidget(self.rb_python)
        exec_layout.addWidget(self.rb_java)
        exec_layout.addWidget(self.rb_bash)
        exec_layout.addWidget(self.rb_custom)
        self.rb_python.setChecked(True) # Default

        # --- Interpreter/Command Prefix (Using QComboBox) ---
        interp_layout = QHBoxLayout()
        self.interpreter_combo = QComboBox()
        self.interpreter_combo.setObjectName("interpreterCombo")
        self.interpreter_combo.setEditable(True)
        self.interpreter_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.interpreter_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.interpreter_browse_button = QPushButton(QIcon.fromTheme("document-open"), "B&rowse...")
        self.interpreter_browse_button.setObjectName("interpreterBrowseButton")
        interp_layout.addWidget(self.interpreter_combo, 1)
        interp_layout.addWidget(self.interpreter_browse_button)
        self.interpreter_label = QLabel("Interpreter/Command Prefix:")
        exec_layout.addSpacing(10)
        exec_layout.addWidget(self.interpreter_label)
        exec_layout.addLayout(interp_layout)
        form_layout.addRow(exec_group)

        # --- Icon ---
        icon_row_layout = QHBoxLayout()
        icon_input_layout = QHBoxLayout()
        self.icon_edit = QLineEdit()
        self.icon_edit.setObjectName("iconEdit")
        self.icon_edit.setPlaceholderText("Path to .png or .svg icon file")
        self.icon_edit.setReadOnly(True)
        self.icon_browse_button = QPushButton(QIcon.fromTheme("preferences-setIcon", QIcon.fromTheme("image-x-generic")), "Icon...")
        self.icon_browse_button.setObjectName("iconBrowseButton")
        icon_input_layout.addWidget(self.icon_edit, 1)
        icon_input_layout.addWidget(self.icon_browse_button)
        self.icon_preview_label = QLabel()
        self.icon_preview_label.setObjectName("iconPreviewLabel")
        self.icon_preview_label.setFixedSize(48, 48)
        self.icon_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_preview_label.setFrameShape(QLabel.Shape.StyledPanel)
        self.icon_preview_label.setToolTip("Selected icon preview")
        icon_row_layout.addLayout(icon_input_layout, 1)
        icon_row_layout.addWidget(self.icon_preview_label)
        form_layout.addRow("Icon File:", icon_row_layout)

        # --- Options ---
        options_group = QGroupBox("Optional Details")
        options_group.setObjectName("optionsGroup")
        options_layout = QFormLayout(options_group)
        # (Other options layout setup as before)
        options_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        options_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        options_layout.setHorizontalSpacing(10)
        options_layout.setVerticalSpacing(12)

        self.terminal_checkbox = QCheckBox("Run in Terminal")
        self.terminal_checkbox.setToolTip("Check this if the application requires a terminal window (e.g., console output)")
        options_layout.addRow(self.terminal_checkbox)

        self.comment_edit = QLineEdit()
        self.comment_edit.setObjectName("commentEdit")
        self.comment_edit.setPlaceholderText("e.g., A utility to manage files")
        options_layout.addRow("C&omment:", self.comment_edit)

        self.categories_list = QListWidget()
        self.categories_list.setObjectName("categoriesList")
        # (List setup as before)
        self.categories_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.categories_list.setToolTip("Select one or more categories (Ctrl+Click or Shift+Click)")
        self.categories_list.setMinimumHeight(120)
        self.categories_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        for category in DESKTOP_CATEGORIES:
            self.categories_list.addItem(QListWidgetItem(category))
        options_layout.addRow(QLabel("Ca&tegories:"), self.categories_list)

        form_layout.addRow(options_group)

        main_layout.addLayout(form_layout)
        main_layout.addStretch(1)

        # --- Bottom Actions (Checkbox + Buttons) ---
        bottom_actions_layout = QVBoxLayout()
        bottom_actions_layout.setSpacing(10)

        # --- NEW: Copy to Desktop Checkbox ---
        self.copy_to_desktop_checkbox = QCheckBox("Copy shortcut file to Desktop folder (~/Desktop)")
        self.copy_to_desktop_checkbox.setObjectName("copyToDesktopCheckbox")
        self.copy_to_desktop_checkbox.setChecked(True) # <--- ADD THIS LINE
        checkbox_layout = QHBoxLayout() # Layout to center checkbox
        checkbox_layout.addStretch(1)
        checkbox_layout.addWidget(self.copy_to_desktop_checkbox)
        checkbox_layout.addStretch(1)
        bottom_actions_layout.addLayout(checkbox_layout)
        # ------------------------------------

        # --- Generate / Clear Buttons ---
        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        self.clear_button = QPushButton(QIcon.fromTheme("edit-clear"), "&Clear All")
        self.clear_button.setObjectName("clearButton")
        self.generate_button = QPushButton(QIcon.fromTheme("document-save"), "&Generate .desktop File")
        self.generate_button.setObjectName("generateButton")
        button_layout.addWidget(self.clear_button)
        button_layout.addSpacing(20)
        button_layout.addWidget(self.generate_button)
        button_layout.addStretch(1)
        bottom_actions_layout.addLayout(button_layout) # Add buttons below checkbox

        main_layout.addLayout(bottom_actions_layout) # Add the combined bottom actions


    def apply_stylesheet(self):
        # (Stylesheet remains the same as the previous colorful version)
        primary_color = "#007AD9" # Vivid Blue
        secondary_color = "#F5F5F5" # Very Light Gray Background
        accent_color = "#1ED760" # Spotify-like Green Accent
        text_color = "#222222" # Dark Gray Text
        border_color = "#D1D1D1" # Light Gray Borders
        button_hover_bg = "#0088F0"
        button_pressed_bg = "#006BBF"
        group_bg = "#FFFFFF" # White Group Background
        group_title_color = "#005AAA" # Darker Blue Title
        input_bg = "#FFFFFF"
        selection_color = primary_color
        selection_text_color = "#FFFFFF"
        font_size = "11pt"

        self.setStyleSheet(f"""
            QDialog {{ background-color: {secondary_color}; }}
            QGroupBox {{ font-weight: bold; border: 1px solid {border_color}; border-radius: 6px; margin-top: 0.7em; padding: 12px 12px 15px 12px; background-color: {group_bg}; }}
            QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; padding: 3px 8px; left: 12px; color: {group_title_color}; background-color: {secondary_color}; border: 1px solid {border_color}; border-bottom: none; border-top-left-radius: 5px; border-top-right-radius: 5px; }}
            QPushButton {{ padding: 8px 16px; border: 1px solid {primary_color}; border-radius: 5px; background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {primary_color}, stop:1 {button_pressed_bg}); color: white; font-weight: bold; min-width: 100px; }}
            QPushButton:hover {{ background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {button_hover_bg}, stop:1 {primary_color}); border-color: {button_pressed_bg}; }}
            QPushButton:pressed {{ background-color: {button_pressed_bg}; border-color: {group_title_color}; }}
            QPushButton:disabled {{ background-color: #B0BEC5; border-color: #90A4AE; color: #607D8B; }}
            QPushButton#scriptBrowseButton, QPushButton#iconBrowseButton, QPushButton#interpreterBrowseButton, QPushButton#clearButton {{ min-width: 80px; padding: 7px 10px; font-weight: normal; background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFFFFF, stop:1 #E0E0E0); border: 1px solid #BDBDBD; color: {text_color}; }}
            QPushButton#scriptBrowseButton:hover, QPushButton#iconBrowseButton:hover, QPushButton#interpreterBrowseButton:hover, QPushButton#clearButton:hover {{ background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #F5F5F5, stop:1 #D5D5D5); border-color: #9E9E9E; }}
            QPushButton#scriptBrowseButton:pressed, QPushButton#iconBrowseButton:pressed, QPushButton#interpreterBrowseButton:pressed, QPushButton#clearButton:pressed {{ background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #D5D5D5, stop:1 #F5F5F5); }}
            QLineEdit, QComboBox {{ padding: 6px; border: 1px solid {border_color}; border-radius: 4px; background-color: {input_bg}; color: {text_color}; }}
            QLineEdit:read-only {{ background-color: #E0E0E0; color: #757575; }}
            QComboBox::drop-down {{ border-left: 1px solid {border_color}; padding-right: 5px; }}
            QComboBox QAbstractItemView {{ border: 1px solid {border_color}; background-color: {input_bg}; selection-background-color: {selection_color}; selection-color: {selection_text_color}; color: {text_color}; }}
            QFormLayout QLabel {{ font-weight: bold; color: {group_title_color}; padding-top: 5px; }}
            QCheckBox, QRadioButton {{ spacing: 6px; color: {text_color}; }}
            QCheckBox#copyToDesktopCheckbox {{ color: {text_color}; /* Ensure checkbox text color */ }}
            QListWidget {{ border: 1px solid {border_color}; border-radius: 4px; background-color: {input_bg}; color: {text_color}; }}
            QListWidget::item:selected {{ background-color: {selection_color}; color: {selection_text_color}; }}
            QListWidget::item:hover {{ background-color: #E3F2FD; color: {text_color}; }}
            QLabel#iconPreviewLabel {{ background-color: #ECEFF1; border: 1px dashed #B0BEC5; color: #78909C; }}
        """)


    def connect_signals(self):
        # (Connections remain the same as previous version)
        self.script_browse_button.clicked.connect(self.browse_script)
        self.icon_browse_button.clicked.connect(self.browse_icon)
        self.interpreter_browse_button.clicked.connect(self.browse_interpreter)
        self.generate_button.clicked.connect(self.generate_desktop_file)
        self.clear_button.clicked.connect(self.clear_fields)
        for button_id in self.exec_button_group.buttons():
             button_id.clicked.connect(self.update_interpreter_state)

    def load_settings(self):
        # (Loading history remains the same)
        history = self.settings.value(SETTINGS_INTERPRETER_HISTORY, [])
        if isinstance(history, str): history = [history]
        if history: self.interpreter_combo.addItems(history)

    def save_settings(self):
        # (Saving history remains the same)
        history = [self.interpreter_combo.itemText(i) for i in range(self.interpreter_combo.count()) if self.interpreter_combo.itemText(i)]
        if len(history) > MAX_INTERPRETER_HISTORY: history = history[:MAX_INTERPRETER_HISTORY]
        self.settings.setValue(SETTINGS_INTERPRETER_HISTORY, history)

    def closeEvent(self, event):
        self.save_settings()
        super().closeEvent(event)

    def update_interpreter_state(self):
        # (Logic remains the same)
        checked_id = self.exec_button_group.checkedId()
        enable = checked_id in [1, 2, 3, 4]
        self.interpreter_label.setEnabled(enable)
        self.interpreter_combo.setEnabled(enable)
        self.interpreter_browse_button.setEnabled(enable)
        if checked_id == 0: self.interpreter_combo.setToolTip("Not applicable for direct execution.")
        elif checked_id == 4: self.interpreter_combo.setToolTip("Enter the full command or path to the executable.\nIt's best to use the full path if possible.")
        else: default_name = self._get_default_interpreter_name(checked_id); self.interpreter_combo.setToolTip(f"Recommended: Specify full path via Browse... \nIf left blank, attempts to use '{default_name}' from system PATH (less reliable).")

    def _get_default_interpreter_name(self, method_id):
        # (Remains the same)
        if method_id == 1: return "python3"
        if method_id == 2: return "java"
        if method_id == 3: return "bash"
        return ""

    def browse_script(self):
        # (Remains the same)
        start_dir = str(Path.home()); current_parent = Path(self.script_path).parent;
        if self.script_path and current_parent.exists(): start_dir = str(current_parent)
        path, _ = QFileDialog.getOpenFileName(self, "Select Script or Program", start_dir, "All Files (*)")
        if path:
            if not Path(path).is_file(): QMessageBox.warning(self, "Invalid Selection", "Selected path is not a file."); return
            native_path = QDir.toNativeSeparators(path); self.script_path = native_path; self.script_edit.setText(native_path)
            if not self.name_edit.text(): base_name = QFileInfo(path).completeBaseName().replace('_', ' ').replace('-', ' ').title(); self.name_edit.setText(base_name)

    def browse_icon(self):
        # (Remains the same)
        start_dir = str(Path.home()); current_parent = Path(self.icon_path).parent;
        if self.icon_path and current_parent.exists(): start_dir = str(current_parent)
        path, _ = QFileDialog.getOpenFileName(self, "Select Icon File", start_dir, "Images (*.png *.svg *.xpm);;All Files (*)")
        if path:
             if not Path(path).is_file(): QMessageBox.warning(self, "Invalid Selection", "Selected path is not a file."); return
             native_path = QDir.toNativeSeparators(path); self.icon_path = native_path; self.icon_edit.setText(native_path); self.update_icon_preview(native_path)

    def browse_interpreter(self):
        # (Remains the same)
        start_dir = "/usr/bin"; current_interp = self.interpreter_combo.currentText(); interp_parent = Path(current_interp).parent; script_parent = Path(self.script_path).parent
        if current_interp and interp_parent.exists(): start_dir = str(interp_parent)
        elif self.script_path and script_parent.exists(): start_dir = str(script_parent)
        path, _ = QFileDialog.getOpenFileName(self, "Select Interpreter or Command", start_dir, "All Files (*)")
        if path: native_path = QDir.toNativeSeparators(path); self.interpreter_combo.setCurrentText(native_path)

    def update_icon_preview(self, icon_path):
        # (Remains the same)
        if icon_path and Path(icon_path).is_file():
            pixmap = QPixmap(icon_path);
            if not pixmap.isNull(): scaled_pixmap = pixmap.scaled(self.icon_preview_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation); self.icon_preview_label.setPixmap(scaled_pixmap); return
        self.icon_preview_label.clear(); self.icon_preview_label.setText("?")

    def add_interpreter_to_history(self, interpreter_cmd):
        # (Remains the same)
        if not interpreter_cmd: return
        if self.interpreter_combo.findText(interpreter_cmd, Qt.MatchFlag.MatchFixedString) == -1:
            self.interpreter_combo.insertItem(0, interpreter_cmd)
            while self.interpreter_combo.count() > MAX_INTERPRETER_HISTORY: self.interpreter_combo.removeItem(self.interpreter_combo.count() - 1)
            self.interpreter_combo.setCurrentIndex(0)


    # --- Generation Logic ---

    def generate_desktop_file(self):
        app_name = self.name_edit.text().strip()
        script_source_path_str = self.script_path
        icon_source_path_str = self.icon_path
        interpreter_prefix = self.interpreter_combo.currentText().strip()
        run_in_terminal = self.terminal_checkbox.isChecked()
        comment = self.comment_edit.text().strip()
        exec_method_id = self.exec_button_group.checkedId()
        copy_to_desktop = self.copy_to_desktop_checkbox.isChecked() # <-- Get checkbox state

        selected_items = self.categories_list.selectedItems()
        selected_categories = [item.text() for item in selected_items]
        categories_str = ";".join(selected_categories)
        if categories_str and not categories_str.endswith(';'): categories_str += ';'

        # --- Input Validation ---
        # (Validation remains the same)
        if not app_name: QMessageBox.warning(self, "Input Missing", "Please enter an Application Name."); return
        if not script_source_path_str or not Path(script_source_path_str).is_file(): QMessageBox.warning(self, "Input Missing", "Please select a valid SOURCE Script or Program file."); return
        if not icon_source_path_str or not Path(icon_source_path_str).is_file(): QMessageBox.warning(self, "Input Missing", "Please select a valid Icon file."); return

        # --- Prepare Paths and Names ---
        script_source_path = Path(script_source_path_str)
        icon_source_path = Path(icon_source_path_str)
        icon_ext = icon_source_path.suffix.lower()
        if icon_ext not in [".png", ".svg", ".xpm"]: QMessageBox.warning(self, "Invalid Icon", "Please select a PNG, SVG, or XPM icon file."); return

        base_filename = sanitize_filename(app_name)
        desktop_filename = f"{base_filename}.desktop"
        app_dir_path = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.ApplicationsLocation))
        desktop_file_path = app_dir_path / desktop_filename

        # Script Target Path
        script_target_base_dir = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.HomeLocation)) / ".local" / "bin"
        script_target_subdir = script_target_base_dir / base_filename
        script_target_path = script_target_subdir / script_source_path.name

        # Icon Target Path (Directly in ~/.local/share/icons)
        icon_target_filename = f"{base_filename}{icon_ext}"
        icons_base_dir = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.GenericDataLocation)) / "icons"
        icon_target_path = icons_base_dir / icon_target_filename

        # --- Determine Exec Command ---
        # (Exec command logic remains the same, using script_target_path)
        exec_command = ""; interpreter_cmd = interpreter_prefix
        if not interpreter_cmd and exec_method_id in [1, 2, 3]: default_name = self._get_default_interpreter_name(exec_method_id); interpreter_cmd = find_executable_on_path(default_name) or default_name
        should_add_to_history = (exec_method_id == 4 and interpreter_cmd) or (exec_method_id in [1,2,3] and interpreter_prefix)
        quoted_script_target_path = f'"{str(script_target_path)}"'
        if exec_method_id == 0: exec_command = quoted_script_target_path
        elif exec_method_id == 1: exec_command = f"{interpreter_cmd} {quoted_script_target_path}"
        elif exec_method_id == 2: exec_command = f"{interpreter_cmd} -jar {quoted_script_target_path}"
        elif exec_method_id == 3: exec_command = f"{interpreter_cmd} {quoted_script_target_path}"
        elif exec_method_id == 4: exec_command = f"{interpreter_cmd} {quoted_script_target_path}" if interpreter_cmd else quoted_script_target_path

        # --- Generate .desktop Content ---
        # (Content generation remains the same, using full icon path)
        desktop_content = f"""[Desktop Entry]
Version=1.1
Type=Application
Name={app_name}
Exec={exec_command}
Icon={str(icon_target_path)}
Terminal={'true' if run_in_terminal else 'false'}
"""
        if comment: desktop_content += f"Comment={comment}\n"
        if categories_str: desktop_content += f"Categories={categories_str}\n"
        desktop_content += f"Path={str(script_target_path.parent)}\n"
        desktop_content += f"StartupNotify=true\n"

        # --- Perform File Operations ---
        desktop_copy_success = False # Flag for desktop copy status
        desktop_copy_path_str = "" # Store path for message
        try:
            # Create script target directory
            script_target_subdir.mkdir(parents=True, exist_ok=True)
            self.log_output(f"Ensured script directory exists: {script_target_subdir}")

            # Copy the script
            shutil.copy2(str(script_source_path), str(script_target_path))
            self.log_output(f"Script copied from '{script_source_path}' to '{script_target_path}'")

            # Set executable bit on the COPIED script
            current_stat = os.stat(script_target_path); new_mode = current_stat.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            if current_stat.st_mode != new_mode: os.chmod(script_target_path, new_mode); self.log_output(f"Set execute permission on: {script_target_path}")
            else: self.log_output(f"Execute permission already set on: {script_target_path}")

            # Create icon directory if needed
            icons_base_dir.mkdir(parents=True, exist_ok=True)

            # Copy icon file
            shutil.copy2(str(icon_source_path), str(icon_target_path))
            self.log_output(f"Icon copied to: {icon_target_path}")

            # Create .desktop directory
            app_dir_path.mkdir(parents=True, exist_ok=True)

            # Write .desktop file safely
            save_file = QSaveFile(str(desktop_file_path))
            if not save_file.open(QIODevice.OpenModeFlag.WriteOnly | QIODevice.OpenModeFlag.Text): raise OSError(f"Could not open QSaveFile for writing: {save_file.errorString()}")
            if save_file.write(desktop_content.encode('utf-8')) == -1: raise OSError(f"Could not write to QSaveFile: {save_file.errorString()}")
            if not save_file.commit(): raise OSError(f"Could not commit QSaveFile: {save_file.errorString()}")

            self.log_output(f".desktop file created: {desktop_file_path}")

            # --- NEW: Copy to Desktop if checked ---
            if copy_to_desktop:
                desktop_dir_str = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)
                if not desktop_dir_str:
                     self.log_output("Could not determine Desktop directory path.", error=True)
                     QMessageBox.warning(self, "Desktop Copy Skipped", "Could not find your Desktop directory path.")
                else:
                    try:
                        desktop_dir_path = Path(desktop_dir_str)
                        desktop_dir_path.mkdir(parents=True, exist_ok=True) # Ensure Desktop exists
                        desktop_shortcut_path = desktop_dir_path / desktop_filename
                        shutil.copy2(str(desktop_file_path), str(desktop_shortcut_path))
                        self.log_output(f"Shortcut also copied to Desktop: {desktop_shortcut_path}")
                        desktop_copy_success = True
                        desktop_copy_path_str = str(desktop_shortcut_path)
                    except Exception as copy_err:
                        self.log_output(f"Failed to copy shortcut to Desktop: {copy_err}", error=True)
                        QMessageBox.warning(self, "Desktop Copy Failed", f"Could not copy shortcut to Desktop:\n{copy_err}")
            # ------------------------------------

            # Add interpreter to history if needed
            if should_add_to_history: self.add_interpreter_to_history(interpreter_cmd)

            # Success Message
            success_message = (
                f"Successfully created shortcut for '{app_name}'!\n\n"
                f"Script Copied To: {script_target_path}\n"
                f"Primary Shortcut: {desktop_file_path}\n"
                f"Icon Copied To: {icon_target_path}\n"
            )
            if copy_to_desktop:
                 if desktop_copy_success:
                      success_message += f"Desktop Shortcut: {desktop_copy_path_str}\n"
                 else:
                      success_message += "Desktop Shortcut: Failed to copy.\n"

            success_message += "\nRun 'update-desktop-database' or log out/in for the shortcut to appear in menus."

            QMessageBox.information(self, "Success", success_message)
            # self.clear_fields()

        except Exception as e:
            self.log_output(f"Error: {e}", error=True)
            QMessageBox.critical(self, "Error", f"An error occurred during generation:\n{e}")

    def log_output(self, message, error=False):
        prefix = "ERROR: " if error else "INFO: "
        print(f"{prefix}{message}")

    # --- Clear Fields ---
    def clear_fields(self):
         self.name_edit.clear()
         self.script_edit.clear(); self.script_path = ""
         self.icon_edit.clear(); self.icon_path = ""
         self.icon_preview_label.clear(); self.icon_preview_label.setText("?")
         self.interpreter_combo.setCurrentText("")
         self.terminal_checkbox.setChecked(True)
         self.comment_edit.clear()
         self.categories_list.clearSelection()
         self.rb_python.setChecked(True)
         self.copy_to_desktop_checkbox.setChecked(False) # <-- Reset checkbox
         self.update_interpreter_state()


# --- Main Execution ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    # font = QFont()
    # font.setPointSize(10)
    # app.setFont(font)
    if "Fusion" in QStyleFactory.keys(): app.setStyle(QStyleFactory.create("Fusion"))
    dialog = DesktopLinkerApp()
    dialog.show()
    sys.exit(app.exec())
