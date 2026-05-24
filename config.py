# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Email settings
USER_EMAIL = os.getenv("USER_EMAIL")
APP_PASSWORD = os.getenv("APP_PASSWORD")
IMAP_SERVER = os.getenv("IMAP_SERVER")

# Security settings
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

# Validate that essential configurations are set
if not all([USER_EMAIL, APP_PASSWORD, IMAP_SERVER]):
    raise ValueError("Error: Please set USER_EMAIL, APP_PASSWORD, and IMAP_SERVER in the .env file.")