try:
    print("Starting import...")
    import voice_auth
    print("Voice Auth Imported OK")
except Exception as e:
    print(f"Error importing voice_auth: {e}")
except ImportError as e:
    print(f"ImportError: {e}")
