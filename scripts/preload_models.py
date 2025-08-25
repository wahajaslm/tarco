#!/usr/bin/env python3
"""
Pre-download ML models during Docker build to avoid runtime downloads.
This script downloads all required models and caches them in the container.
"""

import os
import sys

# Add the app directory to Python path
sys.path.insert(0, '/app')

def preload_models():
    """Pre-download all required ML models."""
    print("Starting model pre-download...")
    
    try:
        # Import the models that will be used
        from sentence_transformers import SentenceTransformer
        from sentence_transformers.cross_encoder import CrossEncoder
        
        # Set model cache directory
        cache_dir = "/app/.cache/huggingface"
        os.makedirs(cache_dir, exist_ok=True)
        
        # Pre-download embedding model
        print("Downloading embedding model...")
        SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2",
            cache_folder=cache_dir
        )
        print("Embedding model downloaded successfully")

        # Pre-download reranker model
        print("Downloading reranker model...")
        CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        print("Reranker model downloaded successfully")
        
        print("All models pre-downloaded successfully!")
        return True
        
    except Exception as e:
        print(f"Error pre-downloading models: {e}")
        return False

if __name__ == "__main__":
    success = preload_models()
    sys.exit(0 if success else 1)
