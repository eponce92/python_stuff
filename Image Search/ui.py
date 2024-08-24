import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
from PIL import Image, ImageTk
import io

class ImageSearchUI:
    def __init__(self, search_engine):
        self.root = tk.Tk()
        self.root.title("Image Search")
        self.search_engine = search_engine
        self.similarity_threshold = 0.5
        self.search_folder = ""
        self.sample_image = ""

        self.create_widgets()
        self.root.bind("<Control-Return>", self.search_images)
        self.root.bind("<Escape>", self.clear_results)

    def create_widgets(self):
        # Left sidebar
        left_frame = ttk.Frame(self.root, padding="10")
        left_frame.pack(side=tk.LEFT, fill=tk.Y)

        ttk.Label(left_frame, text="Search Configuration", font=("", 12, "bold")).pack(pady=5)
        
        ttk.Button(left_frame, text="Select Folder", command=self.select_search_folder).pack(pady=5)
        self.indexing_progress = ttk.Progressbar(left_frame, mode='indeterminate')
        
        ttk.Button(left_frame, text="Select Sample Image", command=self.select_sample_image).pack(pady=5)
        self.sample_image_label = ttk.Label(left_frame, text="Drag and drop image here")
        self.sample_image_label.pack(pady=5)
        self.sample_image_label.bind("<Button-1>", self.select_sample_image)
        
        self.text_search_var = tk.StringVar()
        ttk.Entry(left_frame, textvariable=self.text_search_var, width=25).pack(pady=5)
        
        self.search_type_var = tk.StringVar(value="Text")
        ttk.Combobox(left_frame, textvariable=self.search_type_var, values=["Text", "Image Sample", "Hybrid"]).pack(pady=5)
        
        ttk.Label(left_frame, text="Similarity Threshold:").pack(pady=5)
        self.similarity_var = tk.DoubleVar(value=self.similarity_threshold)
        ttk.Scale(left_frame, from_=0, to=1, variable=self.similarity_var, command=self.update_similarity).pack(pady=5)
        self.similarity_label = ttk.Label(left_frame, text=f"Threshold: {self.similarity_threshold:.2f}")
        self.similarity_label.pack(pady=5)
        
        ttk.Button(left_frame, text="Search", command=self.search_images).pack(pady=5)
        self.search_progress = ttk.Progressbar(left_frame, mode='indeterminate')

        # Right side for galleries
        right_frame = ttk.Frame(self.root, padding="10")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.indexed_gallery_title = ttk.Label(right_frame, text="Indexed Images:", font=("", 12, "bold"))
        self.indexed_gallery_title.pack(pady=5)
        self.indexed_gallery = ttk.Frame(right_frame)
        self.indexed_gallery.pack(fill=tk.BOTH, expand=True)

        self.results_gallery_title = ttk.Label(right_frame, text="Search Results:", font=("", 12, "bold"))
        self.results_gallery_title.pack(pady=5)
        self.results_gallery = ttk.Frame(right_frame)
        self.results_gallery.pack(fill=tk.BOTH, expand=True)

        self.clear_results_button = ttk.Button(right_frame, text="Clear Results", command=self.clear_results)
        self.clear_results_button.pack(pady=5)
        self.clear_results_button.pack_forget()  # Hide initially

    def update_similarity(self, value):
        self.similarity_threshold = float(value)
        self.similarity_label.config(text=f"Threshold: {self.similarity_threshold:.2f}")

    def select_search_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.search_folder = folder_path
            self.indexed_gallery_title.config(text=f'Indexed Images from "{os.path.basename(self.search_folder)}":')
            self.indexing_progress.pack(pady=5)
            self.indexing_progress.start()
            threading.Thread(target=self.index_images, args=(folder_path,)).start()

    def index_images(self, folder_path):
        self.search_engine.index_images(folder_path)
        self.root.after(0, self.indexing_finished)

    def indexing_finished(self):
        self.indexing_progress.stop()
        self.indexing_progress.pack_forget()
        messagebox.showinfo("Indexing", "Indexing completed")
        self.display_indexed_images(self.search_engine.get_indexed_images())

    def display_indexed_images(self, image_paths):
        for widget in self.indexed_gallery.winfo_children():
            widget.destroy()
        
        for i, image_path in enumerate(image_paths):
            img = Image.open(image_path)
            img.thumbnail((100, 100))
            photo = ImageTk.PhotoImage(img)
            label = ttk.Label(self.indexed_gallery, image=photo)
            label.image = photo
            label.grid(row=i//5, column=i%5, padx=5, pady=5)

    def select_sample_image(self, event=None):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")])
        if file_path:
            self.sample_image = file_path
            img = Image.open(self.sample_image)
            img.thumbnail((180, 180))
            photo = ImageTk.PhotoImage(img)
            self.sample_image_label.config(image=photo, text="")
            self.sample_image_label.image = photo

    def search_images(self, event=None):
        if not self.search_folder:
            messagebox.showwarning("Warning", "Please select a search folder.")
            return

        search_type = self.search_type_var.get()
        search_text = self.text_search_var.get()

        if search_type in ["Image Sample", "Hybrid"] and not self.sample_image:
            messagebox.showwarning("Warning", "Please select a sample image for Image Sample or Hybrid search.")
            return

        if search_type in ["Text", "Hybrid"] and not search_text:
            messagebox.showwarning("Warning", "Please enter text for Text or Hybrid search.")
            return

        self.search_progress.pack(pady=5)
        self.search_progress.start()
        for widget in self.results_gallery.winfo_children():
            widget.destroy()
        threading.Thread(target=self.perform_search, args=(search_type, self.sample_image, search_text)).start()

    def perform_search(self, search_type, sample_image, search_text):
        if search_type == "Text":
            results = self.search_engine.search_by_text(search_text)
        elif search_type == "Image Sample":
            results = self.search_engine.search_by_image(sample_image)
        else:  # Hybrid
            results = self.search_engine.search_hybrid(sample_image, search_text)

        filtered_results = [(path, sim) for path, sim in results if sim >= self.similarity_threshold]
        self.root.after(0, self.display_results, filtered_results)

    def display_results(self, results):
        self.search_progress.stop()
        self.search_progress.pack_forget()
        for widget in self.results_gallery.winfo_children():
            widget.destroy()
        
        for i, (image_path, similarity) in enumerate(results):
            img = Image.open(image_path)
            img.thumbnail((200, 200))
            photo = ImageTk.PhotoImage(img)
            frame = ttk.Frame(self.results_gallery, borderwidth=1, relief="solid")
            frame.grid(row=i//3, column=i%3, padx=5, pady=5)
            
            label = ttk.Label(frame, image=photo)
            label.image = photo
            label.pack()
            
            ttk.Label(frame, text=f"Similarity: {similarity:.2f}").pack()
            ttk.Label(frame, text=os.path.basename(image_path)).pack()
            
            frame.bind("<Button-1>", lambda e, path=image_path: os.startfile(path))

        self.clear_results_button.pack(pady=5)

    def clear_results(self, event=None):
        for widget in self.results_gallery.winfo_children():
            widget.destroy()
        self.clear_results_button.pack_forget()

    def run(self):
        self.root.mainloop()