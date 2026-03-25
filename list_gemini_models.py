from google import genai
import util

# Initialize Gemini client
client = genai.Client(api_key=util.GOOGLE_API_KEY)

# List all models
for model in client.models.list():
    print(model.name, model.supported_actions)
