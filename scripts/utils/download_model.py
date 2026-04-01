#!/usr/bin/env python3
"""
Model download utility for MediaFactory.

Downloads Hugging Face models for offline use and updates config.toml.
Uses the unified model registry with huggingface_id as identifier.

Usage:
    python download_model.py <huggingface_id> [options]
    python download_model.py Systran/faster-whisper-large-v3
    python download_model.py facebook/m2m100_1.2B --source=https://hf-mirror.com

This is a CLI wrapper around the core download functionality in
src/mediafactory/models/model_download.py
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from mediafactory.models.model_download import (
    delete_model,
    download_model,
    get_all_model_statuses,
    is_model_downloaded,
)
from mediafactory.models.model_registry import (
    MODEL_REGISTRY,
    get_display_name,
    get_model_info,
)
from mediafactory.config import get_config_manager


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent.absolute()


def list_available_models():
    """Print all available models from the registry."""
    print("\n" + "=" * 60)
    print("Available Models")
    print("=" * 60)

    statuses = get_all_model_statuses()

    # Whisper models
    print("\nWhisper Models (Transcription):")
    print("-" * 40)
    for huggingface_id, info in MODEL_REGISTRY.items():
        if info.model_type.name != "WHISPER":
            continue
        status = "✓" if statuses.get(huggingface_id) else " "
        print(f"  [{status}] {huggingface_id}")
        print(f"      Display: {info.display_name}")
        print(f"      Size: {info.model_size_gb}GB | Memory: ~{info.runtime_memory_gb}GB")
        print(f"      System: {info.recommended_system_gb}GB+ | License: {info.license.value}")
        print()

    # Translation models
    print("\nTranslation Models:")
    print("-" * 40)
    for huggingface_id, info in MODEL_REGISTRY.items():
        if info.model_type.name != "TRANSLATION":
            continue
        status = "✓" if statuses.get(huggingface_id) else " "
        print(f"  [{status}] {huggingface_id}")
        print(f"      Display: {info.display_name}")
        print(f"      Size: {info.model_size_gb}GB | Memory: ~{info.runtime_memory_gb}GB")
        print(f"      System: {info.recommended_system_gb}GB+ | License: {info.license.value}")
        print()

    print("=" * 60)
    print("Legend: [✓] = downloaded, [ ] = not downloaded")
    print("Note: Models are stored in nested directories (e.g., models/Systran/faster-whisper-large-v3/)")
    print()


def get_download_source() -> str:
    """Get download source from config.toml or return default."""
    try:
        config_manager = get_config_manager()
        return config_manager.config.model.download_source or "https://huggingface.co"
    except Exception:
        return "https://huggingface.co"


def main():
    """Main function."""
    args = sys.argv[1:]

    # Show help
    if not args or "--help" in args or "-h" in args:
        print(__doc__)
        return

    # List models
    if "--list" in args or "-l" in args:
        list_available_models()
        return

    # Parse arguments
    model_input = None
    download_source = None
    local_path = None
    should_delete = False

    for arg in args:
        if arg.startswith("--source="):
            download_source = arg.split("=", 1)[1]
        elif arg.startswith("--path="):
            local_path = arg.split("=", 1)[1]
        elif arg == "--delete":
            should_delete = True
        elif not arg.startswith("--"):
            if model_input is None:
                model_input = arg

    # Validate model ID
    if model_input is None:
        print("Error: No model ID specified")
        print("\nUse --list to see available models")
        print("Use --help for usage information")
        sys.exit(1)

    # Normalize: accept both formats (huggingface_id or display_name lookup)
    huggingface_id = model_input

    # Try to find by huggingface_id first
    model_info = get_model_info(huggingface_id)

    # If not found, try to match by display_name or partial ID
    if model_info is None:
        for hf_id, info in MODEL_REGISTRY.items():
            if (
                info.display_name.lower() == huggingface_id.lower()
                or huggingface_id.lower() in hf_id.lower()
            ):
                huggingface_id = hf_id
                model_info = info
                break

    # Handle delete
    if should_delete:
        success, error_msg = delete_model(huggingface_id)
        if success:
            display_name = get_display_name(huggingface_id)
            print(f"✓ Deleted {display_name}")
            print(f"  Removed from: models/{huggingface_id}/")
        else:
            print(f"✗ Failed to delete '{huggingface_id}': {error_msg}")
        return

    # Get download source
    if download_source is None:
        download_source = get_download_source()

    # Download model
    try:
        if model_info is None:
            print(f"Error: Unknown model ID '{model_input}'")
            print("Use --list to see available models")
            sys.exit(1)

        print(f"\nDownloading {model_info.display_name}...")
        print(f"  HuggingFace ID: {huggingface_id}")
        print(f"  Download source: {download_source}")
        print(f"  Target directory: models/{huggingface_id}/")
        print()

        local_path_result = download_model(
            huggingface_id,
            custom_path=local_path,
            download_source=download_source,
            progress_callback=lambda pct, msg: print(f"  [{pct}%] {msg}"),
        )

        print(f"\n✓ Successfully downloaded {model_info.display_name}")
        print(f"  Location: {local_path_result}")
        print(f"  Config updated: Model added to available list")

    except KeyboardInterrupt:
        print("\n\nDownload cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error downloading model")
        print(f"  Details: {e}")
        print(f"\nTips:")
        print(f"  - Check your network connection")
        print(f"  - Try using a mirror: --source=https://hf-mirror.com")
        print(f"  - Verify the model ID with --list")
        sys.exit(1)


if __name__ == "__main__":
    main()
