import os
import sys
import json
import requests
import pyperclip
import datetime
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox, simpledialog, ttk
from pathlib import Path

# Conditionally import windnd for Windows drag-and-drop
IS_WINDOWS = sys.platform == "win32"
if IS_WINDOWS:
    try:
        import windnd
    except ImportError:
        print("Warning: 'windnd' library not found. Drag and drop to window will be disabled.")
        windnd = None # Ensure windnd is defined for later checks
else:
    windnd = None # Not on Windows, so windnd is not applicable


CONFIG_DIR_NAME = ".context_builder"
CONFIG_FILE_NAME = "config.json"
CACHE_FILE_CUSTOM = "custom_instructions.cache"

DEFAULT_EXCLUDES = {
    "folders": [".git", "__pycache__", "node_modules", ".venv", "venv", "build", "dist", ".idea", ".vs"],
    "extensions": [".exe", ".dll", ".so", ".pyc", ".pyo", ".pyd", ".pdf", ".doc", ".docx", ".jpg", ".png", ".gif"]
}

class AppState:
    def __init__(self):
        self.home = Path.home()
        self.config_dir = self.home / CONFIG_DIR_NAME
        self.config_file = self.config_dir / CONFIG_FILE_NAME
        self.cache_file = self.config_dir / CACHE_FILE_CUSTOM
        self.data = {
            "included_paths": [],
            "excluded_paths": [],
            "excluded_types": DEFAULT_EXCLUDES["extensions"].copy(),
            "custom_instructions_url": "",
            "use_custom_instructions": False
        }
        self.load_config()

    def load_config(self):
        if self.config_file.exists():
            try:
                with self.config_file.open("r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    for k, v in loaded.items():
                        if k in self.data:
                            self.data[k] = v
            except Exception as e:
                print(f"Warning: Could not load config: {e}")
                pass

    def save_config(self):
        self.config_dir.mkdir(exist_ok=True)
        with self.config_file.open("w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)

    def save_custom_instructions_cache(self, content):
        self.config_dir.mkdir(exist_ok=True)
        with self.cache_file.open("w", encoding="utf-8") as f:
            f.write(content)

    def load_custom_instructions_cache(self):
        if self.cache_file.exists():
            return self.cache_file.read_text(encoding="utf-8")
        return ""

state = AppState()

def fetch_custom_instructions(url):
    if not url:
        return ""
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        content = r.text
        state.save_custom_instructions_cache(content)
        return content
    except Exception as e:
        return f"<!-- Failed to fetch custom instructions: {e} -->"

def build_context(task_instructions, error_output):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    parts = []
    parts.append("<context>")
    parts.append(f"    <timestamp>{timestamp}</timestamp>")

    if task_instructions.strip():
        parts.append("    <instructions>")
        parts.append(task_instructions)
        parts.append("    </instructions>")

    if error_output.strip():
        parts.append("    <output>")
        parts.append(error_output)
        parts.append("    </output>")

    if state.data.get("use_custom_instructions"):
        url = state.data.get("custom_instructions_url", "")
        content = ""
        if url:
            content = fetch_custom_instructions(url)
        else:
            content = state.load_custom_instructions_cache()
        
        parts.append("    <custom_instructions>")
        parts.append(content if content.strip() else "<!-- No custom instructions content -->")
        parts.append("    </custom_instructions>")

    parts.append("    <repository_structure>")
    included_files = collect_included_files()

    base_for_relpath = Path.cwd()
    if state.data["included_paths"]:
        try:
            abs_paths = [Path(p).resolve() for p in state.data["included_paths"]]
            if abs_paths:
                common_ancestors = [p.parent if p.is_file() else p for p in abs_paths]
                if common_ancestors: # Ensure list is not empty
                    common = Path(os.path.commonpath(common_ancestors))
                    if common and all(str(p).startswith(str(common)) for p in abs_paths):
                        base_for_relpath = common
        except Exception:
            pass

    for fpath_str in included_files:
        fpath = Path(fpath_str)
        try:
            rel = os.path.relpath(fpath, base_for_relpath)
        except ValueError:
            rel = str(fpath.resolve())

        fcontent = read_file_content(fpath_str)
        parts.append("        <file>")
        parts.append(f"            <path>{rel.replace(os.sep, '/')}</path>")
        parts.append(f"            <content><![CDATA[{fcontent}]]></content>")
        parts.append("        </file>")
    parts.append("    </repository_structure>")
    parts.append("</context>")
    return "\n".join(parts)

def read_file_content(path_str):
    path = Path(path_str)
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        if path.name.lower() in [".env"] or path.name.lower().startswith(".env."):
            content = obfuscate_env(content)
        return content
    except UnicodeDecodeError:
        return f"Binary or non-UTF-8 content not displayed ({path.name})"
    except Exception as e:
        return f"Error reading file ({path.name}): {e}"

def obfuscate_env(content):
    lines = []
    for line in content.splitlines():
        if "=" in line:
            key_value = line.split("=", 1)
            key = key_value[0].strip()
            if key and not key.startswith("#"):
                lines.append(f"{key}=********")
            else:
                lines.append(line)
        else:
            lines.append(line)
    return "\n".join(lines)

def collect_included_files():
    files = []
    for p_str in state.data["included_paths"]:
        p = Path(p_str)
        if p.is_file() and p.exists():
            if should_include_file(p):
                files.append(str(p.resolve()))
        elif p.is_dir() and p.exists():
            for fp in p.rglob("*"):
                if fp.is_file() and should_include_file(fp):
                    files.append(str(fp.resolve()))
    return sorted(list(set(files)))

def should_include_file(path: Path):
    resolved_path = path.resolve()

    for exc_str in state.data["excluded_paths"]:
        excp = Path(exc_str).resolve()
        try:
            if excp.is_dir() and str(resolved_path).startswith(str(excp) + os.sep):
                return False
            if excp.is_file() and excp == resolved_path:
                return False
        except Exception:
            pass

    if path.suffix.lower() in state.data["excluded_types"]:
        return False

    for part in resolved_path.parts:
        if part in DEFAULT_EXCLUDES["folders"]:
            return False
    return True

class ContextBuilderGUI:
    def __init__(self, master):
        self.master = master
        master.title("Context Builder")
        master.minsize(600, 500)

        self.frame_main = ttk.Frame(master, padding="10")
        self.frame_main.pack(fill="both", expand=True)

        files_labelframe = ttk.Labelframe(self.frame_main, text="1. Select Files & Folders to Include")
        files_labelframe.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0,10))
        files_labelframe.columnconfigure(0, weight=1)

        drag_drop_text = "Drag & Drop onto window or use buttons:" if IS_WINDOWS and windnd else "Use buttons to add files/folders:"
        self.label_included_info = ttk.Label(files_labelframe, text=drag_drop_text)
        self.label_included_info.grid(row=0, column=0, sticky="w", pady=(0,2))
        self.label_item_count = ttk.Label(files_labelframe, text="Items: 0")
        self.label_item_count.grid(row=0, column=1, sticky="e", padx=5)

        self.list_included = tk.Listbox(files_labelframe, selectmode=tk.EXTENDED, width=80, height=10)
        self.list_included.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(0,5))
        self.list_included_scrollbar_y = ttk.Scrollbar(files_labelframe, orient="vertical", command=self.list_included.yview)
        self.list_included_scrollbar_y.grid(row=1, column=2, sticky="nsw", pady=(0,5))
        self.list_included_scrollbar_x = ttk.Scrollbar(files_labelframe, orient="horizontal", command=self.list_included.xview)
        self.list_included_scrollbar_x.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0,5))
        self.list_included.config(yscrollcommand=self.list_included_scrollbar_y.set, xscrollcommand=self.list_included_scrollbar_x.set)
        self.list_included.bind("<Delete>", lambda event: self.remove_included())

        files_buttons_frame = ttk.Frame(files_labelframe)
        files_buttons_frame.grid(row=3, column=0, columnspan=2, sticky="w", pady=(0,5))
        self.btn_included_add_files = ttk.Button(files_buttons_frame, text="Add Files...", command=self.add_files)
        self.btn_included_add_files.pack(side="left", padx=(0,5))
        self.btn_included_add_folder = ttk.Button(files_buttons_frame, text="Add Folder...", command=self.add_folder)
        self.btn_included_add_folder.pack(side="left", padx=5)
        self.btn_included_remove = ttk.Button(files_buttons_frame, text="Remove Selected", command=self.remove_included)
        self.btn_included_remove.pack(side="left", padx=5)
        self.btn_included_clear = ttk.Button(files_buttons_frame, text="Clear All", command=self.clear_included)
        self.btn_included_clear.pack(side="left", padx=5)
        files_labelframe.rowconfigure(1, weight=1)

        instr_labelframe = ttk.Labelframe(self.frame_main, text="2. Task Instructions (Optional)")
        instr_labelframe.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(0,10))
        instr_labelframe.columnconfigure(0, weight=1)
        instr_labelframe.rowconfigure(0, weight=1)
        self.text_instructions = scrolledtext.ScrolledText(instr_labelframe, width=80, height=6, wrap=tk.WORD)
        self.text_instructions.grid(row=0, column=0, sticky="nsew", pady=(0,5))

        error_labelframe = ttk.Labelframe(self.frame_main, text="3. Prior Error/Output (Optional)")
        error_labelframe.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(0,5))
        error_labelframe.columnconfigure(0, weight=1)
        error_labelframe.rowconfigure(0, weight=1)
        self.text_error = scrolledtext.ScrolledText(error_labelframe, width=80, height=6, wrap=tk.WORD)
        self.text_error.grid(row=0, column=0, sticky="nsew", pady=(0,5))
        self.btn_clear_error = ttk.Button(error_labelframe, text="Clear Error/Output", command=lambda: self.text_error.delete("1.0", "end"))
        self.btn_clear_error.grid(row=1, column=0, sticky="e", pady=(0,5))

        self.bottom_frame = ttk.Frame(self.frame_main)
        self.bottom_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10,0))
        self.bottom_frame.columnconfigure(2, weight=1)
        self.btn_settings = ttk.Button(self.bottom_frame, text="Settings ⚙️", command=self.open_settings)
        self.btn_settings.grid(row=0, column=0, padx=(0,5))
        self.btn_preview = ttk.Button(self.bottom_frame, text="Preview Final Files", command=self.preview_final_files)
        self.btn_preview.grid(row=0, column=1, padx=(0,10))
        self.btn_copy = ttk.Button(self.bottom_frame, text="Generate & Copy Context to Clipboard", command=self.copy_latest, style="Accent.TButton")
        self.btn_copy.grid(row=0, column=2, sticky="ew", ipady=5)

        self.frame_main.rowconfigure(0, weight=3)
        self.frame_main.rowconfigure(1, weight=2)
        self.frame_main.rowconfigure(2, weight=2)
        self.frame_main.columnconfigure(0, weight=1)

        self.update_list_included()
        self.settings_win = None
        try:
            s = ttk.Style()
            s.configure("Accent.TButton", font=('Helvetica', 10, 'bold'))
        except tk.TclError: pass # Ignore if theming fails

        if IS_WINDOWS and windnd: # Only hook if on Windows and windnd imported successfully
            windnd.hook_dropfiles(self.master, func=self.files_dropped)
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def update_list_included(self):
        self.list_included.delete(0, tk.END)
        for p_str in state.data["included_paths"]:
            self.list_included.insert(tk.END, p_str)
        self.label_item_count.config(text=f"Items: {self.list_included.size()}")

    def files_dropped(self, files_bytes_list): # windnd passes a list of byte strings
        if not (IS_WINDOWS and windnd): # Should not be called if not windows, but defensive
            return
        added_any = False
        current_paths_set = set(state.data["included_paths"])
        for f_bytes in files_bytes_list:
            try:
                path_str = Path(f_bytes.decode("utf-8", errors="replace")).resolve().as_posix()
                if path_str not in current_paths_set:
                    state.data["included_paths"].append(path_str)
                    current_paths_set.add(path_str)
                    added_any = True
            except Exception as e:
                print(f"Error processing dropped file: {f_bytes}, Error: {e}")
        if added_any:
            state.data["included_paths"] = sorted(list(current_paths_set))
            self.update_list_included()

    def add_files(self):
        paths = filedialog.askopenfilenames(title="Select files")
        if paths:
            added_any = False
            current_paths_set = set(state.data["included_paths"])
            for p_str_orig in paths:
                p_str = Path(p_str_orig).resolve().as_posix()
                if p_str not in current_paths_set:
                    state.data["included_paths"].append(p_str)
                    current_paths_set.add(p_str)
                    added_any = True
            if added_any:
                state.data["included_paths"] = sorted(list(current_paths_set))
                self.update_list_included()

    def add_folder(self):
        folder = filedialog.askdirectory(title="Select a folder")
        if folder:
            folder_str = Path(folder).resolve().as_posix()
            if folder_str not in state.data["included_paths"]:
                state.data["included_paths"].append(folder_str)
                state.data["included_paths"] = sorted(list(set(state.data["included_paths"])))
                self.update_list_included()

    def remove_included(self):
        selected_indices = self.list_included.curselection()
        if not selected_indices: return
        selected_values = [self.list_included.get(i) for i in selected_indices]
        for val in selected_values:
            if val in state.data["included_paths"]:
                state.data["included_paths"].remove(val)
        self.update_list_included()

    def clear_included(self):
        if messagebox.askyesno("Confirm Clear", "Are you sure you want to remove all selected files and folders?"):
            state.data["included_paths"] = []
            self.update_list_included()

    def preview_final_files(self):
        if not state.data["included_paths"]:
            messagebox.showinfo("Preview", "No files/folders selected to preview.", parent=self.master)
            return
        original_text = self.btn_preview.cget("text")
        self.btn_preview.config(text="Generating Preview...", state=tk.DISABLED)
        self.master.update_idletasks()
        try:
            effective_files = collect_included_files()
            preview_win = tk.Toplevel(self.master)
            preview_win.title("Effective File List Preview")
            preview_win.geometry("700x500")
            preview_win.transient(self.master); preview_win.grab_set()
            preview_win.columnconfigure(0, weight=1); preview_win.rowconfigure(0, weight=1)
            st_frame = ttk.Frame(preview_win); st_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
            st_frame.rowconfigure(0, weight=1); st_frame.columnconfigure(0, weight=1)
            st = scrolledtext.ScrolledText(st_frame, wrap=tk.WORD, relief=tk.SUNKEN, borderwidth=1)
            st.grid(row=0, column=0, sticky="nsew")
            yscroll = ttk.Scrollbar(st_frame, orient="vertical", command=st.yview)
            yscroll.grid(row=0, column=1, sticky="ns"); st.config(yscrollcommand=yscroll.set)
            if not effective_files: st.insert(tk.END, "No files would be included...")
            else:
                st.insert(tk.END, f"The following {len(effective_files)} files will be included:\n\n")
                base_for_relpath = Path.cwd()
                if state.data["included_paths"]:
                    try:
                        abs_paths = [Path(p).resolve() for p in state.data["included_paths"]]
                        if abs_paths:
                            common_ancestors = [p.parent if p.is_file() else p for p in abs_paths]
                            if common_ancestors:
                                common = Path(os.path.commonpath(common_ancestors))
                                if common and all(str(p).startswith(str(common)) for p in abs_paths):
                                    base_for_relpath = common
                    except Exception: pass
                for f_path_str in effective_files:
                    f_path = Path(f_path_str)
                    try: rel = os.path.relpath(f_path, base_for_relpath)
                    except ValueError: rel = str(f_path.resolve())
                    st.insert(tk.END, rel.replace(os.sep, '/') + "\n")
            st.config(state=tk.DISABLED)
            close_btn = ttk.Button(preview_win, text="Close", command=preview_win.destroy)
            close_btn.grid(row=1, column=0, pady=(0,10), padx=10, sticky="e")
            preview_win.bind('<Escape>', lambda e: preview_win.destroy())
        except Exception as e: messagebox.showerror("Preview Error", f"Error: {e}", parent=self.master)
        finally: self.btn_preview.config(text=original_text, state=tk.NORMAL)

    def copy_latest(self):
        task_instructions = self.text_instructions.get("1.0", "end-1c").strip()
        error_output = self.text_error.get("1.0", "end-1c").strip()
        if not state.data["included_paths"] and not task_instructions and not error_output and not (state.data.get("use_custom_instructions") and (state.data.get("custom_instructions_url") or state.load_custom_instructions_cache())):
            messagebox.showwarning("Empty Context", "Nothing to build context from.")
            return
        original_text = self.btn_copy.cget("text")
        self.btn_copy.config(text="Generating...", state=tk.DISABLED)
        self.master.update_idletasks()
        try:
            xml = build_context(task_instructions, error_output)
            pyperclip.copy(xml)
            messagebox.showinfo("Copied", "Context copied to clipboard!")
        except pyperclip.PyperclipException as e:
            messagebox.showerror("Clipboard Error", f"Could not copy: {e}\n\nContext printed to console.", parent=self.master)
            print("--BEGIN CONTEXT--\n", xml, "\n--END CONTEXT--")
        except Exception as e:
            messagebox.showerror("Error Building Context", f"Error: {e}", parent=self.master)
            print(f"Error building context: {e}")
        finally: self.btn_copy.config(text=original_text, state=tk.NORMAL)

    def on_closing(self):
        state.save_config(); self.master.destroy()

    def open_settings(self):
        if self.settings_win is not None and self.settings_win.winfo_exists():
            self.settings_win.lift(); return
        self.settings_win = tk.Toplevel(self.master)
        self.settings_win.title("Settings"); self.settings_win.transient(self.master)
        self.settings_win.grab_set(); self.settings_win.resizable(False, False)
        settings_frame = ttk.Frame(self.settings_win, padding="10")
        settings_frame.pack(fill="both", expand=True)

        custom_instr_lf = ttk.Labelframe(settings_frame, text="Custom Instructions")
        custom_instr_lf.grid(row=0, column=0, columnspan=3, sticky="ew", pady=5, padx=5)
        custom_instr_lf.columnconfigure(1, weight=1)
        self.var_use_custom = tk.BooleanVar(value=state.data.get("use_custom_instructions", False))
        chk_custom = ttk.Checkbutton(custom_instr_lf, text="Include Custom Instructions from URL/Cache", variable=self.var_use_custom)
        chk_custom.grid(row=0, column=0, columnspan=3, sticky="w", pady=2, padx=5)
        ttk.Label(custom_instr_lf, text="URL:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.entry_url = ttk.Entry(custom_instr_lf, width=60)
        self.entry_url.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        self.entry_url.insert(0, state.data.get("custom_instructions_url", ""))
        btn_test_url = ttk.Button(custom_instr_lf, text="Test URL", command=self.test_url)
        btn_test_url.grid(row=1, column=2, sticky="w", padx=(0,5), pady=2)

        excluded_types_lf = ttk.Labelframe(settings_frame, text="Excluded File Extensions")
        excluded_types_lf.grid(row=1, column=0, columnspan=3, sticky="ew", pady=5, padx=5)
        excluded_types_lf.columnconfigure(0, weight=1)
        self.list_excluded_types = tk.Listbox(excluded_types_lf, selectmode=tk.SINGLE, width=60, height=5)
        self.list_excluded_types.grid(row=0, column=0, columnspan=3, sticky="nsew", padx=5, pady=(5,0))
        types_scrollbar = ttk.Scrollbar(excluded_types_lf, orient="vertical", command=self.list_excluded_types.yview)
        types_scrollbar.grid(row=0, column=3, sticky="nsw", padx=(0,5), pady=(5,0)); self.list_excluded_types.config(yscrollcommand=types_scrollbar.set)
        for ext in state.data["excluded_types"]: self.list_excluded_types.insert("end", ext)
        ext_button_frame = ttk.Frame(excluded_types_lf)
        ext_button_frame.grid(row=1, column=0, columnspan=3, sticky="w", padx=5, pady=(2,5))
        ttk.Button(ext_button_frame, text="Add Extension...", command=self.add_ext).pack(side="left")
        ttk.Button(ext_button_frame, text="Remove Selected", command=self.remove_ext).pack(side="left", padx=5)
        ttk.Label(excluded_types_lf, text="Note: Default folder exclusions (e.g. '.git', 'node_modules')\nand some default extensions (e.g. '.exe', '.dll') are always active.", justify=tk.LEFT, relief=tk.SUNKEN, padding=5).grid(row=2, column=0, columnspan=3, sticky="ew", padx=5, pady=5)

        excluded_paths_lf = ttk.Labelframe(settings_frame, text="Excluded Specific Files or Folders (Absolute Paths)")
        excluded_paths_lf.grid(row=2, column=0, columnspan=3, sticky="ew", pady=5, padx=5)
        excluded_paths_lf.columnconfigure(0, weight=1)
        self.list_excluded_paths = tk.Listbox(excluded_paths_lf, selectmode=tk.SINGLE, width=60, height=5)
        self.list_excluded_paths.grid(row=0, column=0, columnspan=3, sticky="nsew", padx=5, pady=(5,0))
        paths_scrollbar = ttk.Scrollbar(excluded_paths_lf, orient="vertical", command=self.list_excluded_paths.yview)
        paths_scrollbar.grid(row=0, column=3, sticky="nsw", padx=(0,5), pady=(5,0)); self.list_excluded_paths.config(yscrollcommand=paths_scrollbar.set)
        for p_str in state.data["excluded_paths"]: self.list_excluded_paths.insert("end", p_str)
        path_button_frame = ttk.Frame(excluded_paths_lf)
        path_button_frame.grid(row=1, column=0, columnspan=3, sticky="w", padx=5, pady=(2,5))
        ttk.Button(path_button_frame, text="Exclude File(s)...", command=lambda: self.add_exc(mode="files")).pack(side="left")
        ttk.Button(path_button_frame, text="Exclude Folder...", command=lambda: self.add_exc(mode="folder")).pack(side="left", padx=5)
        ttk.Button(path_button_frame, text="Remove Selected", command=self.remove_exc).pack(side="left", padx=5)

        btn_save_settings = ttk.Button(settings_frame, text="Save & Close Settings", command=self.save_settings, style="Accent.TButton")
        btn_save_settings.grid(row=3, column=0, columnspan=3, pady=10, padx=5, sticky="e")
        self.settings_win.bind('<Escape>', lambda e: self.settings_win.destroy())

    def test_url(self):
        url = self.entry_url.get().strip()
        if not url: messagebox.showinfo("URL Test", "No URL.", parent=self.settings_win); return
        original_title = self.settings_win.title()
        self.settings_win.title("Settings - Testing URL...")
        self.settings_win.update_idletasks()
        try:
            r = requests.get(url, timeout=5); r.raise_for_status()
            messagebox.showinfo("URL Test", "Successfully fetched.", parent=self.settings_win)
        except Exception as e: messagebox.showerror("URL Test", f"Failed: {e}", parent=self.settings_win)
        finally: self.settings_win.title(original_title)

    def add_ext(self):
        ext = simpledialog.askstring("Add Extension", "Extension (e.g., .log):", parent=self.settings_win)
        if ext:
            ext = ext.strip().lower()
            if not ext.startswith("."): ext = "." + ext
            if ext != "." and ext not in self.list_excluded_types.get(0, tk.END):
                self.list_excluded_types.insert("end", ext)

    def remove_ext(self):
        sel = self.list_excluded_types.curselection()
        if sel: self.list_excluded_types.delete(sel[0])

    def add_exc(self, mode="files"):
        paths_to_add = []
        if mode == "files": paths_to_add.extend(filedialog.askopenfilenames(title="Exclude file(s)", parent=self.settings_win) or [])
        elif mode == "folder": paths_to_add.append(filedialog.askdirectory(title="Exclude folder", parent=self.settings_win))
        for p_orig in filter(None, paths_to_add): # Filter out None if dialog is cancelled
            p_str = Path(p_orig).resolve().as_posix()
            if p_str not in self.list_excluded_paths.get(0, tk.END): self.list_excluded_paths.insert("end", p_str)

    def remove_exc(self):
        sel = self.list_excluded_paths.curselection()
        if sel: self.list_excluded_paths.delete(sel[0])

    def save_settings(self):
        state.data["use__custom_instructions"] = self.var_use_custom.get() # Typo: use_custom_instructions
        state.data["custom_instructions_url"] = self.entry_url.get().strip()
        state.data["excluded_types"] = sorted(list(set(self.list_excluded_types.get(0, tk.END))))
        state.data["excluded_paths"] = sorted(list(set(self.list_excluded_paths.get(0, tk.END))))
        state.save_config()
        self.settings_win.destroy(); self.settings_win = None
        messagebox.showinfo("Settings Saved", "Settings saved.", parent=self.master)

def main():
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        os.chdir(Path(sys.executable).parent)
    root = tk.Tk()
    try:
        style = ttk.Style(root)
        available = style.theme_names()
        for t in ['vista', 'clam', 'alt', 'default']: # Preference order
            if t in available: style.theme_use(t); break
    except tk.TclError: pass
    app = ContextBuilderGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()