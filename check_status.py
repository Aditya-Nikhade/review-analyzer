# check_status.py
import os
from dotenv import load_dotenv
from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

# --- SETUP ---
# Make sure your .env file has your GITHUB_TOKEN
load_dotenv()

# Get credentials from environment variables
endpoint = os.getenv("AZURE_AI_ENDPOINT", "https://models.github.ai/inference")
github_token = os.getenv("GITHUB_TOKEN")

# --- SCRIPT LOGIC ---
print(f"Attempting to connect to endpoint: {endpoint}")

if not github_token:
    print("\nERROR: GITHUB_TOKEN environment variable is not set.")
    print("Please make sure your .env file contains your GitHub token.")
else:
    try:
        # Initialize the client
        client = ChatCompletionsClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(github_token),
        )

        # Make a very small, simple request to test the connection and authentication.
        # This is a "ping" to the service.
        print("Sending a small test request to the model...")
        response = client.complete(
            model="openai/gpt-4.1", # Use a cheap, fast model for testing
            messages=[{"role": "user", "content": "Say 'OK'"}],
            max_tokens=5,
            temperature=0.0
        )

        print("\n--- STATUS: SUCCESS! ---")
        print("Connection successful and authentication is valid.")
        print(f"Model responded: '{response.choices[0].message.content.strip()}'")

    except HttpResponseError as e:
        print("\n--- STATUS: FAILED ---")
        if e.status_code == 401 or e.status_code == 403:
            print("Error: Authentication Failed (401/403 Unauthorized).")
            print("Please double-check that your GITHUB_TOKEN is correct and has the necessary permissions.")
        elif e.status_code == 429:
            print("Error: Rate Limit Exceeded (429 Too Many Requests).")
            print("You are sending requests too quickly. Please wait a moment and try again.")
        else:
            print(f"An HTTP error occurred: {e.status_code}")
            print(f"Full error message: {e.message}")
            
    except Exception as e:
        print("\n--- STATUS: FAILED ---")
        print(f"An unexpected error occurred: {e}")