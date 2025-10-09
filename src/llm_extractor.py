# src/llm_extractor.py

import os
import json
from openai import OpenAI


class LLMDataExtractor:
    """
    Gebruikt een LLM (zoals GPT) als fallback om trade-data uit een e-mailtekst te extraheren.
    """

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is niet ingesteld in het .env-bestand.")
        self.client = OpenAI(api_key=api_key)

    def extract_trade_data(self, email_body: str) -> dict | None:
        """
        GEWIJZIGD: Vraagt de LLM nu ook om de entry_price.
        """
        prompt = f"""
        Analyseer de volgende e-mailtekst van MEXC. Extraheer de cryptomunt-pair, de richting van de trade (LONG of SHORT), de naam van de trader, en de entry price.
        Antwoord UITSLUITEND met een geldig JSON-object met de sleutels "crypto_pair", "direction", "trader", en "entry_price".
        De waarde voor "entry_price" moet een getal zijn (gebruik een punt als decimaal scheidingsteken), geen string.
        Geef geen extra uitleg of tekst.

        E-mailtekst:
        ---
        {email_body}
        ---
        """

        try:
            print("   -> LLM Fallback: Aanroepen van OpenAI API...")
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

            # GEWIJZIGD: Valideer of 'entry_price' ook aanwezig is.
            if all(key in data for key in ["crypto_pair", "direction", "trader", "entry_price"]):
                print(f"   -> LLM Succes: Data succesvol geëxtraheerd: {data}")
                return data
            else:
                print(f"   -> LLM Fout: De JSON van de API mist de vereiste sleutels. Ontvangen: {data.keys()}")
                return None

        except Exception as e:
            print(f"   -> LLM Fout: Een onverwachte fout is opgetreden: {e}")
            return None