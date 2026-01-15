import os
import pandas as pd
import logging
import json
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic

from utils.constants import GEMINI_API_KEY, OPENAI_API_KEY, DATA_BUCKET_NAME, USE_LOCAL_METADATA, LOCAL_METADATA_PATH, ANTHROPIC_API_KEY
from utils.gcs_uploader import read_json_from_gcs

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


embedding_model = OpenAIEmbeddings(api_key=OPENAI_API_KEY)

os.environ['GOOGLE_API_KEY'] = GEMINI_API_KEY

llm_gemini_pro = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro",
    temperature=0.8
)

llm_gemini_flash = ChatGoogleGenerativeAI(
    model="gemini-flash-latest",
    temperature=0.8
)

llm_gemini_lite = ChatGoogleGenerativeAI(
    model="gemini-flash-lite-latest",
    temperature=0.8
)

llm_gpt = ChatOpenAI(
    model="gpt-4o",
    temperature=0.7,
    stream_usage=True,
    api_key=OPENAI_API_KEY
)

llm_anthropic = ChatAnthropic(
    model="claude-sonnet-4-5-20250929",
    temperature=0.7,
    stream_usage=True,
    api_key=ANTHROPIC_API_KEY
)

model_cohere="rerank-english-v3.0"

def load_metadata_from_json():
    # Check if local metadata location is specified
    local_metadata_path = LOCAL_METADATA_PATH if USE_LOCAL_METADATA else None # If USE_LOCAL_METADATA is true, use the local metadata path, otherwise use the GCS version

    if local_metadata_path:
        # Use local file
        try:
            with open(local_metadata_path, 'r') as f:
                data = json.load(f)
            logger.info(f"Loaded metadata from local file: {local_metadata_path}")
            return data.get("metadata", {})
        except FileNotFoundError:
            logger.error(f"Local metadata file not found at {local_metadata_path}")
            return {}
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from local file {local_metadata_path}")
            return {}
    else:
        # Use GCS version (default behavior)
        if not DATA_BUCKET_NAME:
            raise ValueError("DATA_BUCKET_NAME environment variable is not set.")
        
        metadata_path = "general_metadata.json"
        try:
            data = read_json_from_gcs(DATA_BUCKET_NAME, metadata_path)
            logger.info(f"Loaded metadata from GCS: gs://{DATA_BUCKET_NAME}/{metadata_path}")
            return data.get("metadata", {})
        except FileNotFoundError:
            logger.error(f"Metadata file not found in GCS at gs://{DATA_BUCKET_NAME}/{metadata_path}")
            return {}
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from gs://{DATA_BUCKET_NAME}/{metadata_path}")
            return {}

metadata = load_metadata_from_json()