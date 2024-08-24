import os
import flet as ft
import pyperclip
import pathspec

def load_gitignore_patterns(root_folder):
    gitignore_path = os.path.join(root_folder, '.gitignore')
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r') as file:
            return pathspec.PathSpec.from_lines('gitwildmatch', file)
    return None

def scan_project(root_folder, exclude_folders, exclude_extensions, exclude_files):
    gitignore_spec = load_gitignore_patterns(root_folder)
    ignore_dirs = set(folder.strip() for folder in exclude_folders.split(',') if folder.strip())
    ignore_exts = set(ext.strip().lower() for ext in exclude_extensions.split(',') if ext.strip())
    ignore_files = set(file.strip() for file in exclude_files.split(',') if file.strip())
    
    content = []
    file_list = []
    total_lines = 0
    total_files = 0
    
    content.append(f"Root folder name: {os.path.basename(root_folder)}\n\n")
    content.append("Project folder and file structure:\n")
    
    for folder_name, subfolders, filenames in os.walk(root_folder):
        subfolders[:] = [d for d in subfolders if d not in ignore_dirs]
        level = folder_name.replace(root_folder, '').count(os.sep)
        indent = ' ' * 4 * (level)
        rel_folder = os.path.relpath(folder_name, root_folder)
        
        if gitignore_spec and gitignore_spec.match_file(rel_folder):
            continue
        
        content.append(f"{indent}{os.path.basename(folder_name)}/\n")
        subindent = ' ' * 4 * (level + 1)
        
        for filename in filenames:
            if filename in ignore_files:
                continue
            
            rel_file = os.path.relpath(os.path.join(folder_name, filename), root_folder)
            
            if gitignore_spec and gitignore_spec.match_file(rel_file):
                continue
            
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext not in ignore_exts:
                content.append(f"{subindent}{filename}\n")
                file_list.append(rel_file)
    
    content.append("\nFile Code:\n")
    
    for file_path in file_list:
        full_path = os.path.join(root_folder, file_path)
        try:
            with open(full_path, "r", errors="ignore") as file:
                file_content = file.read()
                content.append(f"\nFile: {file_path}\n")
                content.append(file_content)
                content.append("\n" + "="*80 + "\n")
                total_lines += len(file_content.splitlines())
                total_files += 1
        except Exception as e:
            content.append(f"\nFile: {file_path}\n")
            content.append(f"Error reading file: {e}\n")
            content.append("\n" + "="*80 + "\n")
    
    return "".join(content), file_list, total_files, total_lines

def main(page: ft.Page):
    page.title = "Project Scanner"
    page.window_width = 1200
    page.window_height = 700

    project_types = {
        "Generic": {
            "folders": ".git,__pycache__,venv,node_modules",
            "extensions": ".pyc,.pyo,.pyd,.pdf,.json,.md",
            "files": "README.md,LICENSE,.gitignore, code_extraction_UI.py"
        },
        "Python": {
            "folders": ".git,__pycache__,venv,node_modules,mtc_usb_modbus_check,auth,assets",
            "extensions": ".pyc,.pyo,.pyd,.pdf,.json,.md,.png,.ipynb",
            "files": "README.md, LICENSE, .gitignore, code_extraction_UI.py, requirements.txt, BatchCaller.py"
        },
        "Java": {
            "folders": ".git,target,build,.gradle",
            "extensions": ".class,.jar,.war,.ear",
            "files": "README.md,LICENSE,.gitignore,pom.xml,build.gradle, code_extraction_UI.py"
        },
        "C/C++": {
            "folders": ".git,build,bin,lib",
            "extensions": ".o,.obj,.a,.lib,.so,.dll",
            "files": "README.md,LICENSE,.gitignore,Makefile,CMakeLists.txt,code_extraction_UI.py"
        }
    }

    def update_exclusions(e):
        project_type = project_type_dropdown.value
        exclude_folders.value = project_types[project_type]["folders"]
        exclude_extensions.value = project_types[project_type]["extensions"]
        exclude_files.value = project_types[project_type]["files"]
        page.update()

    def browse_folder(e):
        folder_selected = ft.FilePicker(dialog_title="Select folder")
        folder_path.value = folder_selected.result.path if folder_selected.result else ""
        page.update()

    def use_current_location(e):
        current_dir = os.getcwd()
        folder_path.value = current_dir
        page.update()

    def scan_project_action(e):
        folder = folder_path.value
        exclude_folders_value = exclude_folders.value
        exclude_extensions_value = exclude_extensions.value
        exclude_files_value = exclude_files.value

        if not folder:
            page.dialog = ft.AlertDialog(title=ft.Text("Error"), content=ft.Text("Please select a project folder."))
            page.dialog.open = True
            page.update()
            return

        result, file_list, total_files, total_lines = scan_project(folder, exclude_folders_value, exclude_extensions_value, exclude_files_value)
        
        output_text.value = result
        file_listview.controls = [ft.Text(file) for file in file_list]
        stats_label.value = f"Total files scanned: {total_files} | Total lines extracted: {total_lines}"
        page.update()

    def copy_to_clipboard(e):
        content = output_text.value
        pyperclip.copy(content)
        page.dialog = ft.AlertDialog(title=ft.Text("Success"), content=ft.Text("Content copied to clipboard!"))
        page.dialog.open = True
        page.update()

    project_type_dropdown = ft.Dropdown(
        options=[ft.dropdown.Option(key=key, text=key) for key in project_types.keys()],
        value="Generic",
        on_change=update_exclusions
    )

    folder_path = ft.TextField(label="Project Folder", width=300)
    exclude_folders = ft.TextField(label="Exclude Folders", width=300)
    exclude_extensions = ft.TextField(label="Exclude File Extensions", width=300)
    exclude_files = ft.TextField(label="Exclude File Names", width=300)
    output_text = ft.TextField(
        label="Output",
        width=800,
        height=500,
        multiline=True,
        read_only=True
    )
    file_listview = ft.ListView(width=200, height=500)
    stats_label = ft.Text()

    page.add(
        ft.Row([
            ft.Column([
                ft.Text("Project Type:"),
                project_type_dropdown,
                ft.Text("Project Folder:"),
                folder_path,
                ft.Row([
                    ft.ElevatedButton(text="Browse", on_click=browse_folder),
                    ft.ElevatedButton(text="Current Location \u2191", on_click=use_current_location)
                ]),
                ft.Text("Exclude Folders:"),
                exclude_folders,
                ft.Text("Exclude File Extensions:"),
                exclude_extensions,
                ft.Text("Exclude File Names:"),
                exclude_files,
                ft.ElevatedButton(text="Scan Project", on_click=scan_project_action),
            ], width=300),
            ft.Column([
                ft.Row([
                    file_listview,
                    output_text
                ]),
                ft.Row([
                    stats_label,
                    ft.ElevatedButton(text="Copy to Clipboard", on_click=copy_to_clipboard)
                ])
            ])
        ])
    )

    update_exclusions(None)

ft.app(target=main)