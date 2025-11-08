from transformers import pipeline
from typing import List, Dict, Any

def get_terrain_classification(image_path: str) -> List[Dict[str, Any]]:
    """
    Performs image classification on the terrain image to identify surface types.
    This function strictly returns raw data (labels and scores).
    """
    # Note: Ensure you have PyTorch or TensorFlow installed to run this pipeline.
    try:
        classifier = pipeline("image-classification", model="smp111/terrain_recognition")
        # The output is a list of dictionaries: [{'label': 'marshy', 'score': 0.47}, ...]
        return classifier(image_path)
    except Exception as e:
        print(f"ERROR in image classification: {e}")
        return []