"""Example usage of the portable env_loader module.

This demonstrates how to use env_loader to access .env variables
in a way that works across different computers and directory structures.
"""

from __future__ import annotations

from env_loader import load_env_file, get_env_variable, find_project_root


def main() -> None:
    """Demonstrate portable .env loading."""
    
    # Method 1: Automatic loading (recommended)
    print("=== Method 1: Automatic loading ===")
    success = load_env_file(verbose=True)
    if success:
        print("✓ .env file loaded successfully")
    else:
        print("✗ Failed to load .env file")
    
    # Method 2: Get specific variables with validation
    print("\n=== Method 2: Get specific variables ===")
    
    # Avoid printing secrets; just confirm presence.
    nasa_key = get_env_variable("NASA_API_KEY")
    print("NASA_API_KEY: set" if nasa_key else "NASA_API_KEY: not set")

    # Get required variable (raises ValueError if not set)
    try:
        _ = get_env_variable("GARMIN_EMAIL", required=True)
        print("GARMIN_EMAIL: set")
    except ValueError as e:
        print(f"Error: {e}")
    
    # Method 3: Show project root detection
    print("\n=== Method 3: Project root detection ===")
    project_root = find_project_root()
    if project_root:
        print(f"Project root: {project_root}")
        print(f".env location: {project_root / '.env'}")
    else:
        print("Could not detect project root")
    
    # Method 4: Direct environment access after loading
    print("\n=== Method 4: Direct os.environ access ===")
    import os
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    print("OPENAI_API_KEY: set" if openai_key.strip() else "OPENAI_API_KEY: not set")


if __name__ == "__main__":
    main()
