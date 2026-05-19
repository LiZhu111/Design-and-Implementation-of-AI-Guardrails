"""
Global configuration for the Gardening Chatbot.
Supports easy topic switching for High Distinction requirements.
"""

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
    "sunlight", "shade", "climate", "season", "winter", "summer"
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

API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
API_ENDPOINT = "https://prd-ifb220-apim.azure-api.net/ifb220-ai"
API_VERSION = "2025-03-01-preview"

CHAT_MODEL = "gpt-4.1-mini"
EMBEDDING_MODEL = "text-embedding-ada-002"

DENIAL_MESSAGE = (
    "I appreciate your query, but as an assistant dedicated to gardening, "
    "I can only help you with planting, soil, or plant care topics. "
    "Let me know if you have any botanical questions!"
)

LOG_FILE = "chatbot.log"