import os
import clip
import torch
from PIL import Image
import json
import pickle
from torchvision import transforms

class ImageSearchEngine:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        try:
            self.model, self.preprocess = clip.load("ViT-B/32", device=self.device)
        except Exception as e:
            print(f"Error loading CLIP model: {str(e)}")
            raise
        self.image_features = {}
        self.preprocess = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

    def index_images(self, folder_path):
        image_paths = []
        for root, _, files in os.walk(folder_path):
            for filename in files:
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    image_path = os.path.join(root, filename)
                    image_paths.append(image_path)
        
        batch_size = 32
        for i in range(0, len(image_paths), batch_size):
            batch = image_paths[i:i+batch_size]
            self.index_batch(batch)

    def index_batch(self, image_paths):
        images = []
        valid_paths = []
        for path in image_paths:
            try:
                image = Image.open(path).convert("RGB")
                images.append(self.preprocess(image))
                valid_paths.append(path)
            except Exception as e:
                print(f"Error processing {path}: {str(e)}")
        
        if not images:
            return

        image_input = torch.stack(images).to(self.device)
        with torch.no_grad():
            image_features = self.model.encode_image(image_input)
        
        # Normalize the features
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        
        for path, features in zip(valid_paths, image_features):
            self.image_features[path] = features

    def index_single_image(self, image_path):
        if image_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            try:
                image = Image.open(image_path).convert("RGB")
                image_input = self.preprocess(image).unsqueeze(0).to(self.device)
                with torch.no_grad():
                    image_features = self.model.encode_image(image_input)
                # Normalize the features
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                self.image_features[image_path] = image_features
            except Exception as e:
                print(f"Error indexing {image_path}: {str(e)}")

    def search_by_image(self, query_image_path):
        query_image = Image.open(query_image_path).convert("RGB")
        query_input = self.preprocess(query_image).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            query_features = self.model.encode_image(query_input)
        
        # Normalize the query features
        query_features = query_features / query_features.norm(dim=-1, keepdim=True)
        
        return self._calculate_similarities(query_features)

    def search_by_text(self, query_text):
        text_input = clip.tokenize([query_text]).to(self.device)
        
        with torch.no_grad():
            text_features = self.model.encode_text(text_input)
        
        return self._calculate_similarities(text_features)

    def search_hybrid(self, query_image_path, query_text):
        image_results = self.search_by_image(query_image_path)
        text_results = self.search_by_text(query_text)
        
        # Combine results (you may want to adjust this combination method)
        combined_results = {}
        for path in set(dict(image_results).keys()) | set(dict(text_results).keys()):
            combined_results[path] = (dict(image_results).get(path, 0) + dict(text_results).get(path, 0)) / 2
        
        return sorted(combined_results.items(), key=lambda x: x[1], reverse=True)

    def _calculate_similarities(self, query_features):
        similarities = {}
        for path, features in self.image_features.items():
            # Use the stored features directly, as they are already normalized
            similarity = torch.cosine_similarity(query_features, features)
            similarities[path] = similarity.item()
        
        return sorted(similarities.items(), key=lambda x: x[1], reverse=True)

    def get_indexed_images(self):
        return list(self.image_features.keys())

    def load_cache(self, cache_data):
        self.image_features = {path: torch.tensor(features) for path, features in cache_data.items()}

    def save_cache(self, cache_file):
        with open(cache_file, 'wb') as f:
            pickle.dump(self.image_features, f)

    def get_cache(self):
        return {path: features.tolist() for path, features in self.image_features.items()}