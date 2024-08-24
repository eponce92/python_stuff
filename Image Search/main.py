import tkinter as tk
from tkinter import filedialog, ttk
from PIL import Image, ImageTk
import os
from image_search import ImageSearchEngine
import threading
import subprocess

class ImageSearchApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Image Search App")
        self.search_engine = ImageSearchEngine()

        # Create main frame
        self.main_frame = ttk.Frame(self.master)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Create and place widgets
        self.create_widgets()

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
        self.sample_image_label = ttk.Label(self.sidebar, text="No image selected", wraplength=200)
        self.sample_image_label.pack(fill=tk.X, pady=5)
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

        return canvas, scrollable_frame

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

    def select_sample_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")])
        if file_path:
            self.sample_image_path = file_path
            self.sample_image_label.config(text=os.path.basename(file_path))
            
            # Display the selected image
            img = Image.open(file_path)
            img.thumbnail((150, 150))  # Resize image to fit in the sidebar
            photo = ImageTk.PhotoImage(img)
            self.sample_image_display.config(image=photo)
            self.sample_image_display.image = photo  # Keep a reference

    def update_threshold_label(self, *args):
        self.threshold_label.config(text=f"Threshold: {self.similarity_threshold.get():.2f}")

    def search_images(self):
        search_type = self.search_option.get()
        query_text = self.search_entry.get()

        if search_type == "Image Search" and not hasattr(self, 'sample_image_path'):
            tk.messagebox.showwarning("Warning", "Please select a sample image for Image Search.")
            return
        
        if search_type in ["Text Search", "Hybrid"] and not query_text:
            tk.messagebox.showwarning("Warning", "Please enter a text query for Text Search or Hybrid search.")
            return

        if search_type == "Hybrid" and not hasattr(self, 'sample_image_path'):
            tk.messagebox.showwarning("Warning", "Please select a sample image for Hybrid search.")
            return

        if not self.search_engine.image_features:
            tk.messagebox.showwarning("Warning", "Please load images first.")
            return

        self.progress_bar.pack(fill=tk.X, pady=5)
        self.progress_bar.start()

        def search_thread():
            if search_type == "Image Search":
                results = self.search_engine.search_by_image(self.sample_image_path)
            elif search_type == "Text Search":
                results = self.search_engine.search_by_text(query_text)
            else:  # Hybrid
                results = self.search_engine.search_hybrid(self.sample_image_path, query_text)
            
            # Filter results based on similarity threshold
            threshold = self.similarity_threshold.get()
            filtered_results = [(path, score) for path, score in results if score >= threshold]
            
            self.master.after(0, self.search_finished, filtered_results)

        threading.Thread(target=search_thread, daemon=True).start()

    def search_finished(self, results):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.display_search_results(results)

    def display_all_images(self):
        for widget in self.all_images_frame.winfo_children():
            widget.destroy()

        canvas = tk.Canvas(self.all_images_frame)
        scrollbar_y = ttk.Scrollbar(self.all_images_frame, orient="vertical", command=canvas.yview)
        scrollbar_x = ttk.Scrollbar(self.all_images_frame, orient="horizontal", command=canvas.xview)
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

        indexed_images = self.search_engine.get_indexed_images()
        columns = 5  # You can adjust this number to change the number of columns

        for i, img_path in enumerate(indexed_images):
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

        for i in range(columns):
            scrollable_frame.columnconfigure(i, weight=1)

        self.all_images_frame.update()

    def display_search_results(self, results):
        for widget in self.search_results_frame.winfo_children():
            widget.destroy()

        canvas = tk.Canvas(self.search_results_frame)
        scrollbar_y = ttk.Scrollbar(self.search_results_frame, orient="vertical", command=canvas.yview)
        scrollbar_x = ttk.Scrollbar(self.search_results_frame, orient="horizontal", command=canvas.xview)
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

        columns = 5  # You can adjust this number to change the number of columns

        for i, (img_path, score) in enumerate(results):
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

        for i in range(columns):
            scrollable_frame.columnconfigure(i, weight=1)

        self.search_results_frame.update()

    def open_image_folder(self, image_path):
        folder_path = os.path.dirname(image_path)
        if os.name == 'nt':  # For Windows
            os.startfile(folder_path)
        elif os.name == 'posix':  # For macOS and Linux
            subprocess.call(['open', folder_path])

def main():
    root = tk.Tk()
    app = ImageSearchApp(root)
    root.geometry("1200x800")  # Set initial window size
    root.mainloop()

if __name__ == "__main__":
    main()