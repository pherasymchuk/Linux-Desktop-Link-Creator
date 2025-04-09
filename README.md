# Desktop Link Creator 🐧✨
<img src="ldlc_icon.png" alt="App Icon" width="20%" height="20%">

A simple PySide6 GUI application for Linux desktops to easily create `.desktop` application launchers (shortcuts) without manually editing files.

Tired of creating `.desktop` files in `~/.local/share/applications` and managing icons in `~/.local/share/icons` every time you have a new script or GUI app? This tool automates the process!

## Features

*   **Graphical User Interface:** Easy-to-use interface built with PySide6.
*   **Script/Program Selection:** Browse and select the main executable or script file.
*   **Execution Methods:**
    *   Directly execute programs.
    *   Run Python 3 scripts (uses `python3` from PATH or specified interpreter).
    *   Run Java JAR files (uses `java -jar` from PATH or specified JRE).
    *   Run Bash scripts (uses `bash` from PATH or specified interpreter).
    *   Define a custom command/interpreter prefix.
*   **Interpreter History:** Remembers custom interpreter paths/commands used previously.
*   **Icon Selection:** Browse for PNG or SVG icon files.
*   **Automatic File Management:**
    *   Copies the selected script/program to `~/.local/bin/<app-name>/`.
    *   Copies the selected icon to `~/.local/share/icons/` (using a sanitized filename).
    *   Generates the `.desktop` file in `~/.local/share/applications/`.
    *   Sets execute permissions (`chmod +x`) on the *copied* script.
*   **Customization:**
    *   Set the application name (used for filenames).
    *   Select standard Freedesktop categories from a list.
    *   Add an optional comment/description.
    *   Toggle "Run in Terminal" for console applications.
*   **Usability:**
    *   Icon preview.
    *   "Clear All" button to reset the form.

## Installation

**Prerequisites:**

*   **Linux Desktop Environment:** Tested on environments following Freedesktop standards (GNOME, KDE, XFCE, etc.).
*   **Python 3:** Version 3.7 or higher recommended.
*   **pip:** Python package installer (usually included with Python).

**Steps:**

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd desktop-link-creator
    ```

2.  **(Optional but Recommended) Create a Virtual Environment:**
    ```bash
    python3 -m venv venv
    ```

3.  **Install Dependencies:**
    ```bash
    python3 -m pip install pyside6
    ```

## Usage

1.  **Run the Application:**
    ```bash
    python3 desktop_entry_creator.py # Or the specific name you saved the script as
    ```
    (If you created a virtual environment, make sure it's activated first).

2.  **Fill in the Details:**
    *   **Application Name:** Enter the desired name for your shortcut (e.g., "My Custom Script"). This will also influence the generated filenames.
    *   **Script/Program:** Click "Browse..." and select the main script file (e.g., `.py`, `.sh`, `.jar`) or executable program you want to launch.
    *   **Execution Method:** Choose how the script/program should be run:
        *   `Direct Executable`: For compiled programs or scripts with a shebang (`#!/usr/bin/env python3`) that already have execute permissions.
        *   `Python3 Script`: To run a `.py` file using `python3`.
        *   `Java JAR`: To run a `.jar` file using `java -jar`.
        *   `Bash Script`: To run a `.sh` file using `bash`.
        *   `Custom Command Prefix (*Recommended*)`: If you need a specific command before the script path (e.g., `/opt/my-app/bin/run`, `wine`, `specific_java_version`).
*   **Interpreter/Command Prefix:**
    *   This field is active for Python, Java, Bash, and Custom methods.
    *   **Recommendation:** To avoid errors caused by incorrect program versions or missing `PATH` entries, it's **highly recommended** to explicitly specify the full path to the interpreter here. Click "Browse..." to find it (e.g., `/usr/bin/python3.10`, `/opt/jdk-17/bin/java`, `/bin/bash`).
    *   If left blank *only* for Python/Java/Bash methods, the tool will *attempt* to use the default command found in your system's `PATH` (e.g., `python3`, `java`, `bash`), but this may lead to unexpected behavior if the wrong version is found first or if the command isn't in the standard `PATH`.
    *   For "Custom", this field *is* the command prefix you need.
    *   Previously used custom interpreters are saved in the dropdown history.
    *   **Icon File:** Click "Icon..." and select a `.png` or `.svg` file. A preview will be shown.
    *   **Run in Terminal:** Check this box if your script is a command-line application that needs a terminal window to run or show output. Uncheck for GUI applications.
    *   **Comment:** (Optional) A short description of the application.
    *   **Categories:** Select one or more standard categories from the list (use Ctrl+Click or Shift+Click). This helps organize the shortcut in application menus.

3.  **Generate:** Click the "Generate .desktop File" button. The tool will:
    *   Copy the script to `~/.local/bin/<app-name>/`.
    *   Copy the icon to `~/.local/share/icons/`.
    *   Make the copied script executable.
    *   Create the `.desktop` file in `~/.local/share/applications/`.
    *   **(Important Note on Icon Path):** This version writes the *full path* to the icon in `~/.local/share/icons/` into the `.desktop` file's `Icon=` entry. This bypasses standard theme lookups but ensures the specific icon is used.

4.  **Update Desktop Database (IMPORTANT!):**
    For your new shortcut to appear in application menus, you usually need to update your desktop environment's database. Open a terminal and run:
    ```bash
    update-desktop-database ~/.local/share/applications/
    ```
    In some cases, you might also need to run `gtk-update-icon-cache ~/.local/share/icons/` or simply **log out and log back in** to your desktop session.

5.  **Clear Form:** Use the "Clear All" button to reset all fields.

## Creating a Shortcut for *This* App (Recursion!)

You can use the Desktop Link Creator to make a shortcut for itself:

1.  Run the Desktop Link Creator.
2.  **Application Name:** `Desktop Link Creator`
3.  **Script/Program:** Browse to the `desktop_entry_creator.py` (or whatever you named it) file in the cloned repository directory.
4.  **Execution Method:** Select `Python3 Script`.
5.  **Interpreter:** Leave blank (to use `python3` from your `PATH`).
6.  **Icon File:** Browse to the `icon.png` (or `.svg`) file you added to the repository.
7.  **Run in Terminal:** Leave *unchecked* (it's a GUI app).
8.  **Categories:** Select `Utility`, `Development`, maybe `Qt`.
9.  Click **Generate**.
10. Run `update-desktop-database ~/.local/share/applications/` or log out/in. You should now find "Desktop Link Creator" in your application menu!

## Best Practices & Troubleshooting

*   **Specify Interpreters Explicitly:** Relying on commands found in the system `PATH` (`python3`, `java`, `bash`) can sometimes pick up the wrong version or fail if the `PATH` isn't configured as expected. To ensure your shortcut uses the correct program, always try to browse and select the full path to the interpreter (e.g., `/usr/bin/python3.10`, `/usr/lib/jvm/java-17-openjdk-amd64/bin/java`) in the "Interpreter/Command Prefix" field when using Python, Java, or Bash execution methods.
*   **Shortcut Not Appearing:** If your shortcut doesn't show up in the menu after generation, make sure you ran `update-desktop-database ~/.local/share/applications/` in your terminal and then logged out and back into your desktop session.
*   **Incorrect Icon:** Ensure the icon file wasn't moved or deleted after creating the shortcut. Check permissions on the copied icon file in `~/.local/share/icons/`.
*   **Script Fails to Run:** Try running the command shown in the generated `.desktop` file's `Exec=` line directly in your terminal. This can help diagnose permission issues, interpreter problems, or errors within the script itself. Ensure the "Run in Terminal" option is checked if the script requires it.

## Acknowledgements

*   Built using the excellent [PySide6](https://www.qt.io/qt-for-python) (Qt for Python) library.
*   This application was developed with assistance from Google's **Gemini 2.5 Pro** language model during brainstorming, coding, and refinement stages.
