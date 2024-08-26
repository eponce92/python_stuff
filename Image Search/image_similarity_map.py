import numpy as np
from sklearn.manifold import TSNE
import plotly.graph_objects as go
import os
import json
from image_search import ImageSearchEngine
from PIL import Image
import io
import base64
from io import BytesIO

def create_image_marker(img_path, size=50):
    with Image.open(img_path) as img:
        img.thumbnail((size, size))
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"

class EnhancedImageSimilarityMapGenerator3D:
    def __init__(self, image_search_engine):
        self.search_engine = image_search_engine

    def generate_enhanced_3d_map(self, max_images=100):
        try:
            # Get image features and paths
            image_features = []
            image_paths = []
            for path, features in list(self.search_engine.image_features.items())[:max_images]:
                image_features.append(features.numpy())
                image_paths.append(path)

            # Convert to numpy array
            image_features = np.array(image_features)

            # Perform t-SNE for 3D
            tsne = TSNE(n_components=3, random_state=42)
            tsne_results = tsne.fit_transform(image_features)

            # Normalize the t-SNE results
            tsne_min = tsne_results.min(axis=0)
            tsne_max = tsne_results.max(axis=0)
            tsne_normalized = (tsne_results - tsne_min) / (tsne_max - tsne_min)

            # Create an empty figure
            fig = go.Figure()

            # Add scatter plot of points
            fig.add_trace(go.Scatter3d(
                x=tsne_normalized[:, 0],
                y=tsne_normalized[:, 1],
                z=tsne_normalized[:, 2],
                mode='markers',
                marker=dict(
                    size=3,
                    color=tsne_normalized[:, 2],
                    colorscale='Viridis',
                    opacity=0.8
                ),
                hoverinfo='none'
            ))

            # Add image thumbnails
            self.add_images(fig, image_paths, tsne_normalized)

            # Create layout
            layout = go.Layout(
                title='Enhanced 3D Image Similarity Map',
                scene=dict(
                    xaxis_title='t-SNE 1',
                    yaxis_title='t-SNE 2',
                    zaxis_title='t-SNE 3',
                    aspectmode='cube',
                ),
                hovermode='closest',
            )

            # Add layout to figure
            fig.update_layout(layout)

            # Add buttons for different views
            fig.update_layout(
                updatemenus=[
                    dict(
                        type="buttons",
                        direction="left",
                        buttons=[
                            dict(args=[{'scene.camera.eye': {'x': 1.25, 'y': 1.25, 'z': 1.25}}],
                                 label="Reset View",
                                 method="relayout"),
                            dict(args=[{'scene.camera.eye': {'x': 0, 'y': 0, 'z': 2.5}}],
                                 label="XY Plane",
                                 method="relayout"),
                            dict(args=[{'scene.camera.eye': {'x': 2.5, 'y': 0, 'z': 0}}],
                                 label="YZ Plane",
                                 method="relayout"),
                            dict(args=[{'scene.camera.eye': {'x': 0, 'y': 2.5, 'z': 0}}],
                                 label="XZ Plane",
                                 method="relayout"),
                        ],
                        pad={"r": 10, "t": 10},
                        showactive=False,
                        x=0.05,
                        xanchor="left",
                        y=1.1,
                        yanchor="top"
                    ),
                ]
            )

            # Show the interactive plot
            fig.show(renderer="browser")

        except Exception as e:
            print(f"An error occurred while generating the enhanced 3D map: {str(e)}")

    def add_images(self, fig, image_paths, tsne_normalized):
        x, y, z = tsne_normalized.T
        
        for i, path in enumerate(image_paths):
            try:
                marker_img = create_image_marker(path)
                
                fig.add_trace(go.Scatter3d(
                    x=[x[i]],
                    y=[y[i]],
                    z=[z[i]],
                    mode='markers',
                    marker=dict(
                        symbol='square',
                        size=20,
                        color='rgba(0, 0, 0, 0)',
                        line=dict(
                            color='rgba(0, 0, 0, 0)',
                            width=0
                        )
                    ),
                    text=os.path.basename(path),
                    hoverinfo='text',
                    hoverlabel=dict(bgcolor='white'),
                    customdata=[marker_img],
                    hovertemplate='<img src="%{customdata}" width="100">'
                ))
            except Exception as e:
                print(f"Error processing image {path}: {str(e)}")

# Usage example
if __name__ == "__main__":
    try:
        # Initialize your ImageSearchEngine and load the cache
        search_engine = ImageSearchEngine()
        with open("image_features_cache.json", 'r') as f:
            search_engine.load_cache(json.load(f))

        map_generator = EnhancedImageSimilarityMapGenerator3D(search_engine)
        map_generator.generate_enhanced_3d_map()
    except Exception as e:
        print(f"An error occurred: {str(e)}")