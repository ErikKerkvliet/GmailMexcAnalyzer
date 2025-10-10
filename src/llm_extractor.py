# src/llm_extractor.py

import os
import json
from openai import OpenAI


class LLMDataExtractor:
    """
    Uses an LLM (like GPT) as a fallback to extract trade data from an email text.
    """

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set in the .env file.")
        self.client = OpenAI(api_key=api_key)

    def extract_trade_data(self, email_body: str) -> dict | None:
        """
        Now also asks the LLM for the entry_price.
        """
        prompt = f"""
        Analyze the following email text from MEXC. Extract the cryptocurrency pair, the trade direction (LONG or SHORT), the trader's name, and the entry price.
        Respond ONLY with a valid JSON object with the keys "crypto_pair", "direction", "trader", and "entry_price".
        The value for "entry_price" must be a number (use a period as the decimal separator), not a string.
        Do not provide any extra explanation or text.

        Email text:
        ---
        {email_body}
        ---
        """

        try:
            print("   -> LLM Fallback: Calling OpenAI API...")
            response = self.client.chat.completions.create(
                model="gpt-5-nano",
                messages=[
                    {"role": "system",
                     "content": "You are a highly accurate data extraction assistant that only responds in JSON format."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            data = json.loads(content)

            # Validate if 'entry_price' is also present.
            if all(key in data for key in ["crypto_pair", "direction", "trader", "entry_price"]):
                print(f"   -> LLM Success: Data successfully extracted: {data}")
                return data
            else:
                print(f"   -> LLM Error: The JSON from the API is missing required keys. Received: {data.keys()}")
                return None

        except Exception as e:
            print(f"   -> LLM Error: An unexpected error occurred: {e}")
            return None