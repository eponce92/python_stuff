import os
import clip
import torch
from PIL import Image
import json
import pickle

class ImageSearchEngine:
    def __init__(self):
        print(f"CUDA is available: {torch.cuda.is_available()}")
        print(f"CUDA version: {torch.version.cuda}")
        print(f"PyTorch version: {torch.__version__}")
        
        if torch.cuda.is_available():
            print(f"CUDA device count: {torch.cuda.device_count()}")
            print(f"Current CUDA device: {torch.cuda.current_device()}")
            print(f"CUDA device name: {torch.cuda.get_device_name(0)}")
            
            # Force CUDA usage
            torch.cuda.set_device(0)
            self.device = torch.device("cuda:0")
        else:
            print("CUDA is not available. Using CPU.")
            self.device = torch.device("cpu")
        
        print(f"Using device: {self.device}")
        
        try:
            # Change 1: Use a larger CLIP model
            self.model, self.preprocess = clip.load("ViT-L/14", device=self.device)
            print("CLIP model loaded successfully")
            print(f"CLIP model device: {next(self.model.parameters()).device}")
        except Exception as e:
            print(f"Error loading CLIP model: {str(e)}")
            raise
        
        self.image_features = {}
        self.image_dir = None

    def index_images(self, folder_path, progress_callback=None):
        print(f"Scanning folder: {folder_path}")
        image_paths = []
        for root, _, files in os.walk(folder_path):
            for filename in files:
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    image_path = os.path.join(root, filename)
                    image_paths.append(image_path)
        
        print(f"Found {len(image_paths)} images")
        total_images = len(image_paths)
        batch_size = 32
        for i in range(0, total_images, batch_size):
            batch = image_paths[i:i+batch_size]
            print(f"Processing batch {i//batch_size + 1}")
            self.index_batch(batch)
            if progress_callback:
                progress = (i + len(batch)) / total_images
                progress_callback(progress)

    def index_batch(self, image_paths):
        images = []
        valid_paths = []
        for path in image_paths:
            try:
                image = Image.open(path).convert("RGB")
                # Change 2: Use CLIP's preprocessing
                images.append(self.preprocess(image))
                valid_paths.append(path)
            except Exception as e:
                print(f"Error processing {path}: {str(e)}")
        
        if not images:
            print("No valid images in this batch")
            return

        image_input = torch.stack(images).to(self.device)
        print(f"Image input device: {image_input.device}")
        with torch.no_grad():
            image_features = self.model.encode_image(image_input)
        
        # Normalize the features
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        
        for path, features in zip(valid_paths, image_features):
            self.image_features[path] = features.cpu()  # Store features on CPU
        
        print(f"Indexed {len(valid_paths)} images in this batch")

    def index_single_image(self, image_path):
        if image_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            try:
                image = Image.open(image_path).convert("RGB")
                image_input = self.preprocess(image).unsqueeze(0).to(self.device)
                with torch.no_grad():
                    image_features = self.model.encode_image(image_input)
                # Normalize the features
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                self.image_features[image_path] = image_features.cpu()  # Store features on CPU
                print(f"Successfully indexed single image: {image_path}")
            except Exception as e:
                print(f"Error indexing {image_path}: {str(e)}")

    def search_by_image(self, query_image_path):
        print(f"Searching by image: {query_image_path}")
        try:
            query_image = Image.open(query_image_path).convert("RGB")
            query_input = self.preprocess(query_image).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                query_features = self.model.encode_image(query_input)
            
            # Normalize the query features
            query_features = query_features / query_features.norm(dim=-1, keepdim=True)
            
            return self._calculate_similarities(query_features.cpu())
        except Exception as e:
            print(f"Error in search_by_image: {str(e)}")
            raise

    def search_by_text(self, query_text):
        print(f"Searching by text: {query_text}")
        try:
            text_input = clip.tokenize([query_text]).to(self.device)
            
            with torch.no_grad():
                text_features = self.model.encode_text(text_input)
            
            # Normalize the text features
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
            
            return self._calculate_similarities(text_features.cpu(), is_text_search=True)
        except Exception as e:
            print(f"Error in search_by_text: {str(e)}")
            raise

    def _calculate_similarities(self, query_features, is_text_search=False):
        similarities = {}
        for path, features in self.image_features.items():
            similarity = torch.cosine_similarity(query_features, features.unsqueeze(0))
            similarities[path] = similarity.item()
        
        # Adjust minimum similarity threshold for text searches
        min_similarity = 0.2 if is_text_search else 0.7
        filtered_similarities = {k: v for k, v in similarities.items() if v >= min_similarity}
        
        # Debug: Print similarity scores
        print(f"Number of results before filtering: {len(similarities)}")
        print(f"Number of results after filtering: {len(filtered_similarities)}")
        print(f"Top 5 similarity scores: {sorted(similarities.values(), reverse=True)[:5]}")
        
        return sorted(filtered_similarities.items(), key=lambda x: x[1], reverse=True)

    def search_hybrid(self, query_image_path, query_text):
        print(f"Performing hybrid search with image: {query_image_path} and text: {query_text}")
        try:
            image_results = dict(self.search_by_image(query_image_path))
            text_results = dict(self.search_by_text(query_text))
            
            # Find common images (AND operation)
            common_images = set(image_results.keys()) & set(text_results.keys())
            
            # Combine scores for common images
            combined_results = {}
            for path in common_images:
                combined_results[path] = (image_results[path] + text_results[path]) / 2
            
            return sorted(combined_results.items(), key=lambda x: x[1], reverse=True)
        except Exception as e:
            print(f"Error in search_hybrid: {str(e)}")
            raise

    def get_indexed_images(self):
        return list(self.image_features.keys())

    def load_cache(self, cache_data):
        if 'folder_path' in cache_data:
            self.image_dir = cache_data['folder_path']
            del cache_data['folder_path']
        
        self.image_features = {path: torch.tensor(features) for path, features in cache_data.items()}
        print(f"Loaded {len(self.image_features)} items from cache")

    def get_cache(self):
        cache_data = {path: features.tolist() for path, features in self.image_features.items()}
        cache_data['folder_path'] = self.image_dir
        return cache_data