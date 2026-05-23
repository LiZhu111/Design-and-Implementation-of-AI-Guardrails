import os
from dotenv import load_dotenv

load_dotenv()

CURRENT_TOPIC = "Gardening"

TOPIC_KEYWORDS = [
    "plant", "soil", "water", "flower", "fertilizer", "pest", "pests",
    "garden", "vegetable", "herb", "seed", "grow", "harvest",
    "lawn", "tree", "shrub", "compost", "mulch", "prune",
    "insect", "bugs", "disease", "rose", "roses", "tomato",
    "leaf", "root", "stem", "seedling", "sprout", "watering",
    "sunlight", "shade", "climate", "season", "winter", "summer",
    "vinegar", "weed", "weeds", "kill", "control", "organic",
    "dig", "land", "yard", "dirt", "pot", "pots", "shovel", "hoe"
]

TOPIC_SAMPLE_QUERIES = [
    "How to grow tomatoes in my backyard?",
    "What is the best soil for growing roses?",
    "How often should I water my garden plants?",
    "What organic fertilizer is good for vegetables?",
    "How to control pests on tomato plants?",
    "When is the best time to plant flowers?",
    "How to make compost at home?",
    "What are the best herbs to grow in pots?",
    "How to prune rose bushes properly?",
    "How to get rid of weeds naturally?"
]

EMBEDDING_THRESHOLD = 0.72
MAX_TOKENS = 4000

# Bind explicitly to environment variables required by QUT API Gateway
API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
API_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-03-01-preview")

MODEL_NAME = os.getenv("AZURE_DEPLOYMENT_NAME", "GPT-4.1-mini")
EMBEDDING_MODEL = os.getenv("AZURE_EMBEDDING_NAME", "text-embedding-ada-002")

# Keep this enabled for the required Ada-002 semantic guardrail layer.
USE_EMBEDDING_CHECK = os.getenv("USE_EMBEDDING_CHECK", "true").lower() == "true"

DENIAL_MESSAGE = "I'm sorry, but I can only assist you with gardening-related inquiries. Please let me know if you have any questions about plants, soil, or gardening techniques!"
LOG_FILE = "chatbot.log"


def clean_env_value(value: str) -> str:
    """Remove common copy/paste wrappers from .env values."""
    return (value or "").strip().strip('"').strip("'")


def validate_config():
    """Validate required configuration is present."""
    endpoint = clean_env_value(API_ENDPOINT).rstrip("/")
    model_name = clean_env_value(MODEL_NAME)
    embedding_model = clean_env_value(EMBEDDING_MODEL)

    required_vars = [
        ("AZURE_OPENAI_API_KEY", clean_env_value(API_KEY)),
        ("AZURE_OPENAI_ENDPOINT", endpoint),
        ("AZURE_DEPLOYMENT_NAME", model_name)
    ]
    
    missing = []
    for var_name, var_value in required_vars:
        if not var_value:
            missing.append(var_name)
    
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Please check your .env file. Expected format:\n"
            "AZURE_OPENAI_API_KEY=your_key_here\n"
            "AZURE_OPENAI_ENDPOINT=https://prd-ifb220-apim.azure-api.net/ifb220-ai\n"
            "AZURE_DEPLOYMENT_NAME=GPT-4.1-mini\n"
            "AZURE_EMBEDDING_NAME=text-embedding-ada-002"
        )
    
    print(f"OK Configuration validated. Topic: {CURRENT_TOPIC}, Model: {model_name}")
    print(f"OK Embedding model configured: {embedding_model}")
    print(f"OK Embedding check: {'ENABLED' if USE_EMBEDDING_CHECK else 'DISABLED'}")
