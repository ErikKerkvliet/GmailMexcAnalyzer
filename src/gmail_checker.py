# src/gmail_checker.py

import os
import base64
from email.utils import parsedate_to_datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GmailChecker:
    """
    Een klasse om te authenticeren met de Gmail API en e-mails op te halen.
    """

    def __init__(self, scopes: list):
        self.scopes = scopes
        self.creds = self._authenticate()
        self.service = build('gmail', 'v1', credentials=self.creds)

    def _authenticate(self) -> Credentials:
        """
        Beheert de authenticatie van de gebruiker en retourneert geldige credentials.
        Maakt of vernieuwt token.json indien nodig.
        """
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', self.scopes)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', self.scopes)
                creds = flow.run_local_server(port=0)

            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        return creds

    def get_new_emails(self, query: str) -> list:
        """
        Haalt een lijst van nieuwe e-mails op gebaseerd op een query.

        Args:
            query (str): De zoekopdracht voor de Gmail API (bv. 'is:unread').

        Returns:
            list: Een lijst van e-mail data dictionaries.
        """
        try:
            result = self.service.users().messages().list(userId='me', q=query).execute()
            messages_raw = result.get('messages', [])

            if not messages_raw:
                return []

            emails = []
            for msg_ref in messages_raw:
                msg_id = msg_ref['id']
                full_msg = self.service.users().messages().get(userId='me', id=msg_id).execute()

                # Parse de e-mail details
                email_data = self._parse_email_details(full_msg)
                emails.append(email_data)

            return emails

        except HttpError as error:
            print(f'Er is een fout opgetreden bij het ophalen van e-mails: {error}')
            return []

    @staticmethod
    def _get_email_body(payload: dict) -> str:
        """Haalt de platte tekst body uit de e-mail payload."""
        body = ""
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
                        break
        else:
            data = payload.get('body', {}).get('data')
            if data:
                body = base64.urlsafe_b64decode(data).decode('utf-8')
        return body

    def _parse_email_details(self, message: dict) -> dict:
        """Een helper-functie om de belangrijkste details uit een e-mail te halen."""
        payload = message['payload']
        headers = payload['headers']

        subject = "Geen onderwerp"
        sender = "Onbekende afzender"
        date_str = ""
        timestamp = 0

        for header in headers:
            name = header['name'].lower()
            if name == 'subject':
                subject = header['value']
            if name == 'from':
                sender = header['value']
            if name == 'date':
                date_str = header['value']

        # Converteer de datum-tekst naar een universele Unix-timestamp
        if date_str:
            dt_object = parsedate_to_datetime(date_str)
            timestamp = int(dt_object.timestamp())

        # Haal nu ook de body op
        body = self._get_email_body(payload)

        return {
            "id": message['id'],
            "sender": sender,
            "subject": subject,
            "snippet": message['snippet'],
            "labels": message.get('labelIds', []),
            "date": date_str,
            "body": body,
            "timestamp": timestamp
        }