import os
from dotenv import load_dotenv

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN", "")
HF_MODEL = os.getenv("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.2:featherless-ai")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

DISABLE_MEMORY = os.getenv("DISABLE_MEMORY", "0") == "1"
DISABLE_EMBEDDINGS = os.getenv("DISABLE_EMBEDDINGS", "0") == "1"
