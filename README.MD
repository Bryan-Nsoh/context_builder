# Context Builder

Context Builder is a desktop utility designed to help you quickly and efficiently gather relevant code, files, and instructions into a structured XML format. This output is ready to be pasted into Large Language Models (LLMs), development tools, or any system requiring structured contextual input.

The tool provides a simple graphical user interface (GUI) for selecting files and folders, adding task-specific instructions, including previous error outputs, and managing exclusion settings.

## Features

*   **Cross-Platform GUI:** Built with Python and Tkinter for use on Windows and macOS.
*   **Flexible File Selection:**
    *   Add individual files.
    *   Add entire folders (recursively includes files).
    *   Drag-and-drop files/folders onto the window (Windows only).
*   **Contextual Information:**
    *   Optional field for "Task Instructions."
    *   Optional field for "Error/Output from Previous Task."
    *   Option to include "Custom Instructions" fetched from a URL or local cache.
*   **Smart Exclusions:**
    *   Default exclusions for common unnecessary folders (e.g., `.git`, `node_modules`) and file types (e.g., `.exe`, `.dll`, `.pyc`).
    *   User-configurable list of excluded file extensions (e.g., `.log`, `.tmp`).
    *   User-configurable list of specific files or folders to exclude by absolute path.
*   **Preview Functionality:** "Preview Final Files" button shows exactly which files will be included in the context after all selections and exclusions are applied.
*   **Clipboard Integration:** Generates the XML context and copies it directly to your clipboard.
*   **Settings Persistence:** User preferences (exclusions, custom instruction URL) are saved locally for future sessions.
*   **.env File Obfuscation:** Automatically obfuscates values in `.env` files (e.g., `API_KEY=********`).

## Prerequisites

Before you begin, ensure you have the following installed:

*   **Python 3:** Version 3.7 or higher is recommended.
    *   You can download Python from [python.org](https://www.python.org/).
    *   Ensure Python is added to your system's PATH environment variable during installation.
*   **Pip:** Python's package installer (usually comes with Python).

## Setup and Installation

The application is built using PyInstaller, which bundles the Python script and its dependencies into a standalone executable (for Windows) or application bundle (for macOS).

### 1. Get the Code

Clone this repository or download the project files to your local machine. You should have at least:
*   `context_builder.py` (the main application script)
*   `setup_windows.ps1` (for Windows setup)
*   `setup_macos.sh` (for macOS setup - assumed to be present and functional)

### 2. Run the Setup Script for Your Operating System:

Navigate to the project directory in your terminal or command prompt.

**For Windows:**

1.  Open PowerShell.
2.  Navigate to the `CONTEXT_BUILDER` project directory.
3.  Run the setup script:
    ```powershell
    .\setup_windows.ps1
    ```
4.  This script will:
    *   Create a Python virtual environment (`.\ContextBuilder_WindowsBuild\venv`).
    *   Install the required Python packages (`requests`, `pyperclip`, `pyinstaller`, `windnd`).
    *   Build the `context_builder.exe` executable using PyInstaller.
5.  The standalone executable will be located in `.\ContextBuilder_WindowsBuild\dist\context_builder.exe`.

**For macOS:**

1.  Open Terminal.
2.  Navigate to the `CONTEXT_BUILDER` project directory.
3.  Make the setup script executable (if it's not already):
    ```bash
    chmod +x setup_macos.sh
    ```
4.  Run the setup script:
    ```bash
    ./setup_macos.sh
    ```
5.  This script will (similarly to Windows):
    *   Create a Python virtual environment (`./ContextBuilder_MacOSBuild/venv`).
    *   Install the required Python packages (`requests`, `pyperclip`, `pyinstaller`).
    *   Build the `ContextBuilder.app` application bundle using PyInstaller.
6.  The application bundle will be located in `./ContextBuilder_MacOSBuild/dist/ContextBuilder.app`.

**Note:** You only need the final executable (`context_builder.exe`) or application bundle (`ContextBuilder.app`) from the `dist` folder. The `ContextBuilder_WindowsBuild` or `ContextBuilder_MacOSBuild` folders contain intermediate build files and the virtual environment, which are not needed to run the application. You can copy the executable/app to a convenient location.

## How to Use Context Builder

1.  **Launch the Application:**
    *   **Windows:** Double-click `context_builder.exe`.
    *   **macOS:** Double-click `ContextBuilder.app` (you might need to drag it to your `/Applications` folder first).

2.  **Select Files and Folders:**
    *   **Drag & Drop (Windows Only):** Drag files or folders from your file explorer directly onto the application window.
    *   **Add Files... Button:** Click to open a file dialog and select one or more individual files.
    *   **Add Folder... Button:** Click to open a folder dialog and select a directory. All files within this directory (and its subdirectories, respecting exclusions) will be considered.
    *   The selected top-level paths will appear in the "Selected Files & Folders" listbox. The "Items: X" count will update.

3.  **Manage Selected Items:**
    *   **Remove Selected:** Select one or more items in the listbox and click this button (or press the `Delete` key) to remove them from the selection.
    *   **Clear All:** Removes all items from the selected files/folders list.

4.  **Add Optional Instructions:**
    *   **Task Instructions:** Type or paste any specific instructions related to the task you're preparing context for.
    *   **Prior Error/Output:** Type or paste any relevant error messages or output from a previous step that might be useful context. Use the "Clear Error/Output" button to clear this field.

5.  **Preview Final Files (Recommended):**
    *   Click the **"Preview Final Files"** button.
    *   A new window will appear showing a list of *all individual files* that will actually be included in the context after applying all default and custom exclusion rules. This helps verify your selections and settings.

6.  **Configure Settings (Optional):**
    *   Click the **"Settings ⚙️"** button to open the settings dialog. Here you can:
        *   **Custom Instructions:**
            *   Enable/disable inclusion of custom instructions.
            *   Set a URL to fetch custom instructions from. The content will be cached locally.
            *   "Test URL" button to verify the URL.
        *   **Excluded File Extensions:**
            *   View and manage a list of file extensions to exclude (e.g., `.log`, `.tmp`).
            *   Add new extensions or remove existing ones.
            *   *Note:* Default exclusions for common binary/system files (like `.exe`, `.dll`) and common project folders (like `.git`, `node_modules`) are always active.
        *   **Excluded Specific Files or Folders:**
            *   Add absolute paths to specific files or entire folders that should always be excluded.
        *   Click "Save & Close Settings" to apply changes.

7.  **Generate & Copy Context:**
    *   Once you're satisfied with your selections and settings, click the **"Generate & Copy Context to Clipboard"** button.
    *   The application will process all selected files, apply exclusions, read file contents (obfuscating `.env` files), and combine everything with your instructions into an XML-formatted string.
    *   This XML string is automatically copied to your system clipboard.
    *   A confirmation message will appear.

8.  **Paste the Context:**
    *   Paste the copied XML context into your target LLM, tool, or document.

## Understanding the XML Output

The generated XML context generally follows this structure:

```xml
<context>
    <timestamp>YYYYMMDD_HHMMSS</timestamp>
    <instructions>
        Your task instructions here...
    </instructions>
    <output>
        Your previous error/output here...
    </output>
    <custom_instructions>
        Content from your custom instructions URL/cache...
    </custom_instructions>
    <repository_structure>
        <file>
            <path>relative/or/absolute/path/to/file1.py</path>
            <content><![CDATA[File content of file1.py...]]></content>
        </file>
        <file>
            <path>another/file.txt</path>
            <content><![CDATA[Content of another/file.txt...]]></content>
        </file>
        <!-- ... more files ... -->
    </repository_structure>
</context>
```

*   Paths are made relative to a common ancestor of your selected items if possible, otherwise relative to the current working directory or absolute.
*   File content is wrapped in `<![CDATA[...]]>` to handle special characters.

## Settings Persistence

Your settings (custom instruction URL, exclusion lists) are saved in a `config.json` file located in a directory named `.context_builder` within your user's home directory:

*   **Windows:** `C:\Users\<YourUserName>\.context_builder\config.json`
*   **macOS/Linux:** `/Users/<yourusername>/.context_builder/config.json`

This means your settings will persist across application uses and even if you move the executable/app bundle. To reset to default settings, you can delete this `config.json` file or the entire `.context_builder` directory.

## Troubleshooting / Notes

*   **`windnd` Library (Windows):** If the `windnd` library is not found or fails to install during setup on Windows, drag-and-drop functionality will be disabled, but you can still use the "Add Files..." and "Add Folder..." buttons. The application will print a warning to the console if this happens.
*   **Clipboard Issues:** If `pyperclip` has issues copying to the clipboard on your system (rare for GUI environments), the XML context will be printed to the console/terminal from which the application was launched (if applicable).
*   **Python Path:** Ensure Python is correctly installed and added to your system's PATH for the setup scripts to work correctly.

---

Happy Context Building!
