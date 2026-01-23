import requests
import json 
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

api_key = os.environ.get("NTC_API_KEY", "")
api_url = os.environ.get("NTC_API_URL", "https://aigateway.ntictsolution.com/v1/chat/completions")
