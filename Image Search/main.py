import flet as ft
from threading import Timer
from image_search import ImageSearchEngine
import os
import threading
import darkdetect
import queue
import json
import subprocess
import platform
from PIL import Image
import io
import base64

class ImageSearchApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Image Search App"
        self.search_engine = ImageSearchEngine()
        self.sample_image_path = None
        self.indexing_queue = queue.Queue()
        self.search_queue = queue.Queue()
        self.similarity_threshold = 0.7  # Updated default value
        self.sample_image_preview = ft.Image(width=100, height=100, fit=ft.ImageFit.COVER, border_radius=ft.border_radius.all(10), visible=False)

        # Set theme
        self.theme = darkdetect.theme().lower()
        self.page.theme_mode = ft.ThemeMode.DARK if self.theme == "dark" else ft.ThemeMode.LIGHT

        # Create FilePicker instances
        self.folder_picker = ft.FilePicker(on_result=self.folder_picker_result)
        self.file_picker = ft.FilePicker(on_result=self.file_picker_result)
        self.page.overlay.extend([self.folder_picker, self.file_picker])

        # Add this line to enable the use of icons
        page.fonts = {
            "Roboto": "https://github.com/google/fonts/raw/main/apache/roboto/static/Roboto-Regular.ttf",
            "MaterialIcons": "https://github.com/google/material-design-icons/raw/master/font/MaterialIcons-Regular.ttf",
        }

        # Create main layout
        self.create_layout()

        # Load cached image features if available
        self.load_cache()
        
        # Check if cache is empty and update UI
        self.check_cache_status()

    def create_layout(self):
        # Sidebar controls
        self.folder_path_text = ft.Text("No folder selected", style=ft.TextThemeStyle.BODY_SMALL)
        self.progress_bar = ft.ProgressBar(width=280, value=0, visible=False)
        self.search_option = ft.Dropdown(
            width=280,
            options=[
                ft.dropdown.Option("🖼️ Image"),
                ft.dropdown.Option("🔤 Text"),
                ft.dropdown.Option("👾 Hybrid"),
            ],
            value="🔤 Text",
        )
        self.search_entry = ft.TextField(
            label="Text Search",
            width=280,
            border_radius=ft.border_radius.all(8),
            filled=True,
            dense=True,
            content_padding=ft.padding.symmetric(horizontal=10, vertical=8),
            suffix_icon=None,
            border_color=ft.colors.TRANSPARENT,
            focused_border_color=ft.colors.PRIMARY,
            focused_color=None,
            color=ft.colors.ON_SURFACE,
        )
        self.similarity_slider = ft.Slider(
            min=0,
            max=100,
            value=70,
            divisions=30,
            label="{value}",
            width=280,
            on_change=self.update_similarity_value
        )
        self.similarity_threshold_text = ft.Text("Similarity Threshold: 70.00%", size=14)
        
        def create_step_card(title, content):
            return ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text(title, size=16, weight=ft.FontWeight.BOLD),
                        *content
                    ]),
                    padding=10,
                ),
                margin=ft.margin.only(bottom=10),
            )

        sidebar = ft.Column([
            ft.Text("Image Search App", size=24, weight=ft.FontWeight.BOLD),
            create_step_card("Step 1: Select Images", [
                ft.ElevatedButton("📁 Select Folder", on_click=lambda _: self.folder_picker.get_directory_path(), width=280),
                self.folder_path_text,
                self.progress_bar,
            ]),
            create_step_card("Step 2: Choose Search Method", [
                self.search_option,
            ]),
            create_step_card("Step 3: Select Sample Image", [
                ft.ElevatedButton("📷 Select Sample Image", on_click=lambda _: self.file_picker.pick_files(allowed_extensions=["png", "jpg", "jpeg", "gif"]), width=280),
                ft.Container(
                    content=self.sample_image_preview,
                    alignment=ft.alignment.center
                ),
            ]),
            create_step_card("Step 4: Enter Search Query", [
                self.search_entry,
            ]),
            create_step_card("Step 5: Adjust Settings", [
                self.similarity_slider,
                self.similarity_threshold_text,
            ]),
            create_step_card("Step 6: Perform Search", [
                ft.ElevatedButton("🔍 Search", on_click=self.search_images, width=280),
            ]),
            create_step_card("Additional Options", [
                ft.Switch(
                    label="🌙 Dark Mode" if self.page.theme_mode == ft.ThemeMode.LIGHT else "☀️ Light Mode",
                    value=self.page.theme_mode == ft.ThemeMode.DARK,
                    on_change=self.toggle_theme,
                    label_position=ft.LabelPosition.LEFT
                ),
            ]),
        ], width=300, scroll=ft.ScrollMode.AUTO)

        # Image galleries
        self.all_images_grid = ft.GridView(expand=1, max_extent=200, child_aspect_ratio=0.8)
        self.search_results_grid = ft.GridView(expand=1, max_extent=220, child_aspect_ratio=0.75)

        main_content = ft.Column([
            ft.Text("All Images", size=16, weight=ft.FontWeight.BOLD),
            self.all_images_grid,
            ft.Divider(),
            ft.Text("Search Results", size=16, weight=ft.FontWeight.BOLD),
            self.search_results_grid,
        ], expand=True, spacing=20)

        # Main layout
        self.page.add(
            ft.Row([
                ft.Container(sidebar, width=300, padding=10, alignment=ft.alignment.top_left),
                ft.VerticalDivider(width=1),
                ft.Container(main_content, expand=True, padding=10),
            ], expand=True, alignment=ft.MainAxisAlignment.START)
        )

    def folder_picker_result(self, e: ft.FilePickerResultEvent):
        if e.path:
            self.folder_path_text.value = e.path
            self.search_engine.image_dir = e.path
            self.page.update()
            self.index_and_display_images(e.path)

    def file_picker_result(self, e: ft.FilePickerResultEvent):
        if e.files:
            self.sample_image_path = e.files[0].path
            
            # Create a preview of the selected image
            img = Image.open(self.sample_image_path)
            img.thumbnail((100, 100))  # Resize the image while maintaining aspect ratio
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            
            self.sample_image_preview.src_base64 = base64.b64encode(buf.getvalue()).decode()
            self.sample_image_preview.visible = True
            
            self.page.update()

    def index_and_display_images(self, folder_path):
        print(f"Starting to index folder: {folder_path}")
        self.progress_bar.visible = True
        self.progress_bar.value = 0
        self.page.update()

        def progress_callback(progress):
            print(f"Indexing progress: {progress}")
            self.indexing_queue.put(("progress", progress))

        def index_thread():
            print("Starting indexing thread")
            try:
                self.search_engine.index_images(folder_path, progress_callback)
                print("Indexing completed successfully")
                self.indexing_queue.put(("finished", None))
                self.save_cache()  # Save cache after indexing
            except Exception as e:
                print(f"Error during indexing: {str(e)}")
                self.indexing_queue.put(("error", str(e)))

        threading.Thread(target=index_thread, daemon=True).start()
        self.check_indexing_status()

    def check_indexing_status(self):
        try:
            message_type, data = self.indexing_queue.get_nowait()
            if message_type == "progress":
                self.progress_bar.value = data
            elif message_type == "finished":
                self.indexing_finished()
                return
            elif message_type == "error":
                self.show_error(f"Error during indexing: {data}")
                return
            self.page.update()
        except queue.Empty:
            pass
        
        Timer(0.1, self.check_indexing_status).start()

    def indexing_finished(self):
        print("Indexing finished, updating UI")
        self.progress_bar.visible = False
        self.display_all_images()
        self.page.update()

    def search_images(self, e):
        search_type = self.search_option.value
        query_text = self.search_entry.value

        if not self.validate_search_inputs(search_type, query_text):
            return

        self.progress_bar.visible = True
        self.page.update()

        threading.Thread(target=self.search_thread, args=(search_type, query_text), daemon=True).start()
        self.check_search_status()

    def validate_search_inputs(self, search_type, query_text):
        if search_type in ["🖼️ Image", "👾 Hybrid"] and not self.sample_image_path:
            self.show_error("Please select a sample image for Image Search or Hybrid search.")
            return False
        
        if search_type in ["🔤 Text", "👾 Hybrid"] and not query_text:
            self.show_error("Please enter a text query for Text Search or Hybrid search.")
            return False

        if not self.search_engine.image_features:
            self.show_error("Please load images first.")
            return False

        return True

    def show_error(self, message):
        snack_bar = ft.SnackBar(content=ft.Text(message))
        self.page.overlay.append(snack_bar)
        snack_bar.open = True
        self.page.update()

    def search_thread(self, search_type, query_text):
        try:
            results = self.perform_search(search_type, query_text)
            threshold = self.similarity_threshold
            self.search_results = [(path, score) for path, score in results if score >= threshold]
            self.search_queue.put(("finished", self.search_results))
        except Exception as e:
            self.search_queue.put(("error", str(e)))

    def check_search_status(self):
        try:
            message_type, data = self.search_queue.get_nowait()
            if message_type == "finished":
                self.search_finished(data)
            elif message_type == "error":
                self.show_error(f"An error occurred during search: {data}")
            self.progress_bar.visible = False
            self.page.update()
        except queue.Empty:
            Timer(0.1, self.check_search_status).start()

    def perform_search(self, search_type, query_text):
        if search_type == "🖼️ Image":
            return self.search_engine.search_by_image(self.sample_image_path)
        elif search_type == "🔤 Text":
            return self.search_engine.search_by_text(query_text)
        else:  # 👾 Hybrid
            return self.search_engine.search_hybrid(self.sample_image_path, query_text)

    def search_finished(self, results):
        self.progress_bar.visible = False
        self.display_search_results(results)
        self.page.update()

    def display_all_images(self):
        self.all_images_grid.controls.clear()
        indexed_images = self.search_engine.get_indexed_images()

        for img_path in indexed_images:
            file_name = os.path.basename(img_path)
            image = ft.Image(
                src=img_path,
                width=150,
                height=150,
                fit=ft.ImageFit.COVER,
                repeat=ft.ImageRepeat.NO_REPEAT,
                border_radius=ft.border_radius.all(10),
            )
            
            def create_on_double_tap(path):
                return lambda _: self.open_file_location(path)
            
            gesture_detector = ft.GestureDetector(
                content=image,
                on_double_tap=create_on_double_tap(img_path)
            )
            
            self.all_images_grid.controls.append(
                ft.Container(
                    content=ft.Column([
                        gesture_detector,
                        ft.Text(file_name, size=12, text_align=ft.TextAlign.CENTER, no_wrap=True, max_lines=1),
                    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                    padding=10,
                    margin=ft.margin.all(5),
                    height=200,
                )
            )
        self.page.update()

    def display_search_results(self, results):
        self.search_results_grid.controls.clear()

        for img_path, score in results:
            file_name = os.path.basename(img_path)
            image = ft.Image(
                src=img_path,
                width=150,
                height=150,
                fit=ft.ImageFit.COVER,
                repeat=ft.ImageRepeat.NO_REPEAT,
                border_radius=ft.border_radius.all(10),
            )
            
            def create_on_double_tap(path):
                return lambda _: self.open_file_location(path)
            
            gesture_detector = ft.GestureDetector(
                content=image,
                on_double_tap=create_on_double_tap(img_path)
            )
            
            self.search_results_grid.controls.append(
                ft.Container(
                    content=ft.Column([
                        gesture_detector,
                        ft.Text(file_name, size=12, text_align=ft.TextAlign.CENTER, no_wrap=True, max_lines=1),
                        ft.Text(f"Score: {score:.2f}", size=12, text_align=ft.TextAlign.CENTER),
                    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                    padding=10,
                    margin=ft.margin.all(5),
                    height=220,
                )
            )
        self.page.update()

    def toggle_theme(self, e):
        self.page.theme_mode = ft.ThemeMode.DARK if e.control.value else ft.ThemeMode.LIGHT
        self.page.update()

    def load_cache(self):
        cache_file = "image_features_cache.json"
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                self.search_engine.load_cache(cache_data)
                
                if 'folder_path' in cache_data:
                    self.folder_path_text.value = cache_data['folder_path']
            except json.JSONDecodeError:
                print("Error decoding cache file. Starting with empty cache.")
                self.search_engine.image_features = {}
            except Exception as e:
                print(f"Error loading cache: {str(e)}. Starting with empty cache.")
                self.search_engine.image_features = {}

    def check_cache_status(self):
        if not self.search_engine.image_features:
            self.folder_path_text.value = "No images indexed. Please select a folder to index."
        else:
            self.folder_path_text.value = f"Loaded {len(self.search_engine.image_features)} images from cache"
            self.display_all_images()
        self.page.update()

    def update_similarity_value(self, e):
        self.similarity_threshold = e.control.value / 100
        self.similarity_threshold_text.value = f"Similarity Threshold: {e.control.value:.2f}%"
        self.page.update()

    def open_file_location(self, image_path):
        folder_path = os.path.dirname(image_path)
        print(f"Opening folder: {folder_path}")
        if platform.system() == "Windows":
            os.startfile(folder_path)
        elif platform.system() == "Darwin":  # macOS
            subprocess.Popen(["open", folder_path])
        else:  # Linux and other Unix-like
            subprocess.Popen(["xdg-open", folder_path])

    def save_cache(self):
        cache_file = "image_features_cache.json"
        cache_data = self.search_engine.get_cache()
        
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)

def main(page: ft.Page):
    page.window.width = 1200  # Increase window width
    page.window.height = 1000  # Increase window height
    page.window.resizable = True  # Allow window resizing
    app = ImageSearchApp(page)
    page.on_close = app.save_cache

ft.app(target=main)