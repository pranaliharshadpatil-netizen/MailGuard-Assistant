import os
from typing import Dict

def get_user_credentials() -> Dict[str, str]:
    """
    Retrieve email account credentials securely.
    Looks first in environment variables, then falls back to a config file.
    
    Returns:
        Dict[str, str]: A dictionary with 'email' and 'password' keys.
    """
    # 1. Try environment variables (recommended)
    email = os.getenv("MAILGUARD_EMAIL")
    password = os.getenv("MAILGUARD_PASSWORD")

    if email and password:
        return {"email": email, "password": password}

    # 2. Fallback: Try loading from config.txt
    try:
        creds = {}
        with open("config.txt", "r") as f:
            for line in f:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    creds[key] = value
        if "email" in creds and "password" in creds:
            return {"email": creds["email"], "password": creds["password"]}
    except FileNotFoundError:
        pass

    # 3. If nothing found
    return {"error": "Credentials not found. Set MAILGUARD_EMAIL and MAILGUARD_PASSWORD."}
