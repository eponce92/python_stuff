import os
import clip
import torch
from PIL import Image

try:
    from torchvision.transforms import Resize, ToTensor, Normalize
except ImportError:
    print("Warning: torchvision not fully imported. Some functionality may be limited.")

class ImageSearchEngine:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model, self.preprocess = clip.load("ViT-B/32", device=self.device)
        self.image_features = {}

    def index_images(self, folder_path):
        for root, _, files in os.walk(folder_path):
            for filename in files:
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    image_path = os.path.join(root, filename)
                    self.index_single_image(image_path)

    def index_single_image(self, image_path):
        if image_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            try:
                image = Image.open(image_path).convert("RGB")
                image_input = self.preprocess(image).unsqueeze(0).to(self.device)
                with torch.no_grad():
                    image_features = self.model.encode_image(image_input)
                self.image_features[image_path] = image_features
            except Exception as e:
                print(f"Error indexing {image_path}: {str(e)}")

    def search_by_image(self, query_image_path):
        query_image = Image.open(query_image_path).convert("RGB")
        query_input = self.preprocess(query_image).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            query_features = self.model.encode_image(query_input)
        
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
            similarity = torch.cosine_similarity(query_features, features)
            similarities[path] = similarity.item()
        
        return sorted(similarities.items(), key=lambda x: x[1], reverse=True)

    def get_indexed_images(self):
        return list(self.image_features.keys())