import tkinter as tk
from tkinter import filedialog, ttk
from PIL import Image, ImageTk
import os
from image_search import ImageSearchEngine
import threading
import subprocess
import sv_ttk
import darkdetect
import sys
import json
from tkinterdnd2 import DND_FILES, TkinterDnD
import concurrent.futures

# Only import pywinstyles on Windows
if sys.platform == "win32":
    import pywinstyles

os.environ['KMP_DUPLICATE_LIB_OK']='True'

class ImageSearchApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Image Search App")
        self.search_engine = ImageSearchEngine()
        self.sample_image_path = None

        # Create theme variable
        self.theme_var = tk.StringVar(value=darkdetect.theme().lower())

        # Apply Sun Valley theme
        self.apply_theme(self.theme_var.get())

        # Create main frame
        self.main_frame = ttk.Frame(self.master)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Create and place widgets
        self.create_widgets()

        # Load cached image features if available
        self.load_cache()

    def apply_theme(self, theme):
        sv_ttk.set_theme(theme)
        if sys.platform == "win32":
            self.apply_theme_to_titlebar(theme)
        
        # Update the theme variable
        self.theme_var.set(theme)
        
        # Update the checkbutton state if it exists
        if hasattr(self, 'dark_mode_check'):
            if theme == "dark":
                self.dark_mode_check.state(['selected'])
            else:
                self.dark_mode_check.state(['!selected'])

    def apply_theme_to_titlebar(self, theme):
        version = sys.getwindowsversion()
        if version.major == 10 and version.build >= 22000:
            pywinstyles.change_header_color(self.master, "#1c1c1c" if theme == "dark" else "#fafafa")
        elif version.major == 10:
            pywinstyles.apply_style(self.master, "dark" if theme == "dark" else "normal")
            self.master.wm_attributes("-alpha", 0.99)
            self.master.wm_attributes("-alpha", 1)

    def create_widgets(self):
        # Create left sidebar
        self.sidebar = ttk.Frame(self.main_frame, padding="10")
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)

        # Create right frame for image galleries
        self.gallery_frame = ttk.Frame(self.main_frame)
        self.gallery_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Sidebar controls
        ttk.Label(self.sidebar, text="Image Search App", font=('Arial', 16, 'bold')).pack(pady=10)

        # Folder selection section
        ttk.Separator(self.sidebar, orient='horizontal').pack(fill=tk.X, pady=10)
        ttk.Label(self.sidebar, text="1. Select Image Directory", font=('Arial', 10, 'bold')).pack(anchor='w', pady=5)
        ttk.Button(self.sidebar, text="📁 Browse", command=self.select_folder).pack(fill=tk.X, pady=5)
        self.folder_label = ttk.Label(self.sidebar, text="No folder selected", wraplength=200)
        self.folder_label.pack(fill=tk.X, pady=5)

        # Progress bar
        self.progress_bar = ttk.Progressbar(self.sidebar, mode='indeterminate', length=200)
        self.progress_bar.pack(fill=tk.X, pady=5)
        self.progress_bar.pack_forget()  # Hide initially

        # Search options section
        ttk.Separator(self.sidebar, orient='horizontal').pack(fill=tk.X, pady=10)
        ttk.Label(self.sidebar, text="2. Configure Search", font=('Arial', 10, 'bold')).pack(anchor='w', pady=5)
        ttk.Label(self.sidebar, text="Search Type:").pack(anchor='w', pady=2)
        self.search_option = tk.StringVar(value="Text Search")
        search_options = ["🖼️ Image Search", "📝 Text Search", "🔀 Hybrid"]
        self.search_option_menu = ttk.Combobox(self.sidebar, textvariable=self.search_option, values=search_options, state="readonly")
        self.search_option_menu.pack(fill=tk.X, pady=5)

        # Image sample selection
        self.sample_image_button = ttk.Button(self.sidebar, text="🖼️ Select Sample Image", command=self.select_sample_image)
        self.sample_image_button.pack(fill=tk.X, pady=5)
        self.sample_image_label = ttk.Label(self.sidebar, text="Drag and drop image here", wraplength=200)
        self.sample_image_label.pack(fill=tk.X, pady=5)
        self.sample_image_label.drop_target_register(DND_FILES)
        self.sample_image_label.dnd_bind('<<Drop>>', self.drop_sample_image)
        self.sample_image_display = ttk.Label(self.sidebar)
        self.sample_image_display.pack(fill=tk.X, pady=5)

        # Search query
        ttk.Label(self.sidebar, text="Search Query:").pack(anchor='w', pady=2)
        self.search_entry = ttk.Entry(self.sidebar)
        self.search_entry.pack(fill=tk.X, pady=5)

        # Similarity threshold slider
        ttk.Label(self.sidebar, text="Similarity Threshold:").pack(anchor='w', pady=2)
        self.similarity_threshold = tk.DoubleVar(value=0.5)  # Default value of 0.5
        self.similarity_slider = ttk.Scale(self.sidebar, from_=0, to=1, orient=tk.HORIZONTAL, 
                                           variable=self.similarity_threshold, command=self.update_threshold_label)
        self.similarity_slider.pack(fill=tk.X, pady=5)
        self.threshold_label = ttk.Label(self.sidebar, text=f"Threshold: {self.similarity_threshold.get():.2f}")
        self.threshold_label.pack(fill=tk.X, pady=5)

        # Search button
        ttk.Separator(self.sidebar, orient='horizontal').pack(fill=tk.X, pady=10)
        ttk.Button(self.sidebar, text="🔎 Search", command=self.search_images).pack(fill=tk.X, pady=10)

        # Image galleries
        self.all_images_frame = ttk.LabelFrame(self.gallery_frame, text="All Images", padding="10")
        self.all_images_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.search_results_frame = ttk.LabelFrame(self.gallery_frame, text="Search Results", padding="10")
        self.search_results_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Scrollable canvas for image galleries
        self.create_scrollable_canvas(self.all_images_frame)
        self.create_scrollable_canvas(self.search_results_frame)

        # Add dark mode toggle
        self.dark_mode_check = ttk.Checkbutton(self.sidebar, text="Dark Mode", variable=self.theme_var, 
                        command=self.toggle_theme, style="Switch.TCheckbutton")
        self.dark_mode_check.pack(fill=tk.X, pady=5)

        # Set initial state of the checkbutton
        if self.theme_var.get() == "dark":
            self.dark_mode_check.state(['selected'])
        else:
            self.dark_mode_check.state(['!selected'])

        # Add "Save Search Results" button
        ttk.Button(self.sidebar, text="💾 Save Results", command=self.save_search_results).pack(fill=tk.X, pady=5)

    def toggle_theme(self):
        current_theme = sv_ttk.get_theme()
        new_theme = "dark" if current_theme == "light" else "light"
        self.theme_var.set(new_theme)
        self.apply_theme(new_theme)
        
        # Update the checkbutton state
        if new_theme == "dark":
            self.dark_mode_check.state(['selected'])
        else:
            self.dark_mode_check.state(['!selected'])
        
        # Force update of all widgets
        self.master.update_idletasks()

    def save_search_results(self):
        if not hasattr(self, 'search_results'):
            tk.messagebox.showinfo("Info", "No search results to save.")
            return
        
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if file_path:
            with open(file_path, 'w') as f:
                json.dump(self.search_results, f)
            tk.messagebox.showinfo("Success", f"Search results saved to {file_path}")

    def select_sample_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")])
        self.set_sample_image(file_path)

    def set_sample_image(self, file_path):
        if file_path:
            self.sample_image_path = file_path
            self.sample_image_label.config(text=os.path.basename(file_path))
            
            img = Image.open(file_path)
            img.thumbnail((150, 150))
            photo = ImageTk.PhotoImage(img)
            self.sample_image_display.config(image=photo)
            self.sample_image_display.image = photo

    def drop_sample_image(self, event):
        file_path = event.data.strip("{}").split()[0]  # Get the first file if multiple are dropped
        if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            self.set_sample_image(file_path)
        else:
            tk.messagebox.showwarning("Invalid File", "Please drop an image file.")

    def update_threshold_label(self, *args):
        self.threshold_label.config(text=f"Threshold: {self.similarity_threshold.get():.2f}")

    def select_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.folder_label.config(text=folder_path)
            self.search_engine.image_dir = folder_path
            self.index_and_display_images(folder_path)

    def index_and_display_images(self, folder_path):
        self.progress_bar.pack(fill=tk.X, pady=5)
        self.progress_bar.start()

        def index_thread():
            self.search_engine.index_images(folder_path)
            self.master.after(0, self.indexing_finished)

        threading.Thread(target=index_thread, daemon=True).start()

    def indexing_finished(self):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.display_all_images()

    def search_images(self):
        search_type = self.search_option.get()
        query_text = self.search_entry.get()

        if search_type in ["🖼️ Image Search", "🔀 Hybrid"] and not self.sample_image_path:
            tk.messagebox.showwarning("Warning", "Please select a sample image for Image Search or Hybrid search.")
            return
        
        if search_type in ["📝 Text Search", "🔀 Hybrid"] and not query_text:
            tk.messagebox.showwarning("Warning", "Please enter a text query for Text Search or Hybrid search.")
            return

        if not self.search_engine.image_features:
            tk.messagebox.showwarning("Warning", "Please load images first.")
            return

        self.progress_bar.pack(fill=tk.X, pady=5)
        self.progress_bar.start()

        def search_thread():
            try:
                if search_type == "🖼️ Image Search":
                    results = self.search_engine.search_by_image(self.sample_image_path)
                elif search_type == "📝 Text Search":
                    results = self.search_engine.search_by_text(query_text)
                else:  # Hybrid
                    results = self.search_engine.search_hybrid(self.sample_image_path, query_text)
                
                threshold = self.similarity_threshold.get()
                self.search_results = [(path, score) for path, score in results if score >= threshold]
                
                self.master.after(0, self.search_finished, self.search_results)
            except Exception as e:
                self.master.after(0, lambda e=e: tk.messagebox.showerror("Error", f"An error occurred during search: {str(e)}"))
            finally:
                self.master.after(0, lambda: self.progress_bar.pack_forget())

        threading.Thread(target=search_thread, daemon=True).start()

    def search_finished(self, results):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.display_search_results(results)

    def display_all_images(self):
        for widget in self.all_images_frame.winfo_children():
            widget.destroy()

        canvas, scrollable_frame = self.create_scrollable_canvas(self.all_images_frame)

        indexed_images = self.search_engine.get_indexed_images()
        columns = 5  # You can adjust this number to change the number of columns

        for i, img_path in enumerate(indexed_images):
            try:
                img = Image.open(img_path)
                img.thumbnail((150, 150))  # Increased size for better visibility
                photo = ImageTk.PhotoImage(img)
                frame = ttk.Frame(scrollable_frame)
                label = ttk.Label(frame, image=photo)
                label.image = photo  # Keep a reference
                label.pack(fill=tk.BOTH, expand=True)
                ttk.Label(frame, text=os.path.basename(img_path), wraplength=150).pack()
                frame.grid(row=i//columns, column=i%columns, padx=5, pady=5, sticky="nsew")
                
                # Bind double-click event to open folder
                label.bind("<Double-1>", lambda e, path=img_path: self.open_image_folder(path))
            except Exception as e:
                print(f"Error loading image {img_path}: {str(e)}")
                continue

        for i in range(columns):
            scrollable_frame.columnconfigure(i, weight=1)

        self.all_images_frame.update()

    def display_search_results(self, results):
        for widget in self.search_results_frame.winfo_children():
            widget.destroy()

        canvas, scrollable_frame = self.create_scrollable_canvas(self.search_results_frame)

        columns = 5  # You can adjust this number to change the number of columns

        for i, (img_path, score) in enumerate(results):
            try:
                img = Image.open(img_path)
                img.thumbnail((150, 150))  # Increased size for better visibility
                photo = ImageTk.PhotoImage(img)
                frame = ttk.Frame(scrollable_frame)
                label = ttk.Label(frame, image=photo)
                label.image = photo  # Keep a reference
                label.pack(fill=tk.BOTH, expand=True)
                ttk.Label(frame, text=f"{os.path.basename(img_path)}\nScore: {score:.2f}", wraplength=150).pack()
                frame.grid(row=i//columns, column=i%columns, padx=5, pady=5, sticky="nsew")
                
                # Bind double-click event to open folder
                label.bind("<Double-1>", lambda e, path=img_path: self.open_image_folder(path))
            except Exception as e:
                print(f"Error loading image {img_path}: {str(e)}")
                continue

        for i in range(columns):
            scrollable_frame.columnconfigure(i, weight=1)

        self.search_results_frame.update()

    def open_image_folder(self, image_path):
        folder_path = os.path.dirname(image_path)
        if os.name == 'nt':  # For Windows
            os.startfile(folder_path)
        elif os.name == 'posix':  # For macOS and Linux
            subprocess.call(['open', folder_path])

    def create_scrollable_canvas(self, parent):
        canvas = tk.Canvas(parent)
        scrollbar_y = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollbar_x = ttk.Scrollbar(parent, orient="horizontal", command=canvas.xview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar_y.pack(side="right", fill="y")
        scrollbar_x.pack(side="bottom", fill="x")

        # Bind mouse wheel event to the canvas
        canvas.bind("<MouseWheel>", lambda event: canvas.yview_scroll(int(-1 * (event.delta / 120)), "units"))
        canvas.bind("<Shift-MouseWheel>", lambda event: canvas.xview_scroll(int(-1 * (event.delta / 120)), "units"))

        # Make sure the scrollable frame captures mouse events
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        def _on_shift_mousewheel(event):
            canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
        
        scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        scrollable_frame.bind("<Shift-MouseWheel>", _on_shift_mousewheel)

        return canvas, scrollable_frame

    def load_cache(self):
        cache_file = "image_features_cache.json"
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            self.search_engine.load_cache(cache_data)
            self.display_all_images()  # Display cached images

    def save_cache(self):
        cache_file = "image_features_cache.json"
        cache_data = self.search_engine.get_cache()
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)

def main():
    root = TkinterDnD.Tk()
    app = ImageSearchApp(root)
    root.geometry("1200x800")
    root.mainloop()
    app.save_cache()  # Save cache when closing the app

if __name__ == "__main__":
    main()