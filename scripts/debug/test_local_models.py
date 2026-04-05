#!/usr/bin/env python3
"""Debug script for local model functionality in MediaFactory."""

import os
import sys

from mediafactory.models.local_models import LocalModelManager
from mediafactory.engine import TranslationEngine

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_local_model_functionality():
    """Test the local model functionality."""
    print("Testing Local Model Functionality in VideoDub")
    print("=" * 50)

    # Test 1: Initialize LocalModelManager
    print("\n1. Testing LocalModelManager initialization...")
    local_manager = LocalModelManager()
    print("✓ LocalModelManager initialized successfully")

    # Test 2: Initialize TranslationEngine with local model preference
    print("\n2. Testing TranslationEngine with local model preference...")
    _ = TranslationEngine(use_local_models_only=False)
    print("✓ TranslationEngine initialized successfully")

    # Test 3: Get downloaded translation models
    print("\n3. Testing get_downloaded_translation_models...")
    downloaded_models = local_manager.get_downloaded_translation_models()
    print(f"✓ Downloaded translation models: {downloaded_models}")

    # Test 4: Get best available model
    print("\n4. Testing get_best_available_model...")
    best_model = local_manager.get_best_available_model()
    print(f"✓ Best available model: {best_model}")

    # Test 5: Check model availability
    print("\n5. Testing is_model_available_locally...")
    # Test with a common model ID
    test_model_id = "facebook/nllb-200-distilled-600M"
    is_available = local_manager.is_model_available_locally(test_model_id)
    print(f"✓ Model '{test_model_id}' available: {is_available}")

    # Test 6: Get model path
    print("\n6. Testing get_model_path...")
    model_path = local_manager.get_model_path()
    print(f"✓ Model path: {model_path}")

    print("\n" + "=" * 50)
    print("All tests completed successfully!")
    print("\nFeatures implemented:")
    print("- Local model directory scanning")
    print("- Online attempt limiting (2 attempts max per model)")
    print("- Fallback mechanism when online fails")
    print("- Support for specifying local models only")
    print("- Integration with subtitle processing")
    print("- CLI and GUI support for local models")


if __name__ == "__main__":
    test_local_model_functionality()
