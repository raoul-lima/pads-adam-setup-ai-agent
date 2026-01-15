import os
from dotenv import load_dotenv
from pathlib import Path
import pandas as pd

load_dotenv()

BQ_URL='bigquery://programmads-toolbox/dv360_advertising_data'

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")

# Backend root directory
backend_root = Path(__file__).parent.parent
# Project root directory (parent of backend)
project_root = Path(__file__).parent.parent

# Path for local data like sessions and user info
LOCAL_DATA_PATH = os.path.join(backend_root, 'data')
os.makedirs(LOCAL_DATA_PATH, exist_ok=True)

GOOGLE_APPLICATION_CREDENTIALS = os.path.join(project_root, 'credentials.json')

INSTRUCTION_FILE_PATH = os.path.join(backend_root, 'agents', 'prompts', 'prompt_instructions.json')

BUCKET_NAME = os.getenv("BUCKET_NAME")
DATA_BUCKET_NAME = os.getenv("DATA_BUCKET_NAME")
FEEDBACK_BUCKET_NAME = os.getenv("FEEDBACK_BUCKET_NAME")

FOLDER_NAME = "adam-agent-query-results"

# Conversation history settings
MAX_CONVERSATION_HISTORY = int(os.getenv("MAX_CONVERSATION_HISTORY", "50"))

# PostgreSQL Database Configuration
POSTGRES_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "35.205.161.122"),
    "port": os.getenv("POSTGRES_PORT", "5432"),
    "database": os.getenv("POSTGRES_DB", "adsecura_testing"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD")
}

# Use PostgreSQL instead of in-memory storage
USE_POSTGRES_STORAGE = os.getenv("USE_POSTGRES_STORAGE", "false").lower() == "true"

# Use local metadata instead of GCS
USE_LOCAL_METADATA = os.getenv("USE_LOCAL_METADATA", "false").lower() == "true"

# Path for local metadata
LOCAL_METADATA_PATH = os.path.join(backend_root, 'data', 'general_metadata.json')
