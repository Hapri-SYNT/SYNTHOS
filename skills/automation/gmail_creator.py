import os, json, base64, re
from typing import Dict, Optional
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.send',
          'https://www.googleapis.com/auth/gmail.readonly']

class GmailCreator:
    def __init__(self):
        self.service = self._auth()
    
    def _auth(self):
        token_file = 'token.json'
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        if creds.expired:
            creds.refresh(Request())
            with open(token_file, 'w') as f:
                f.write(creds.to_json())
        return build('gmail', 'v1', credentials=creds)
    
    def check_inbox(self, dna, query: str = "verify OR confirm") -> Optional[Dict]:
        try:
            results = self.service.users().messages().list(
                userId='me', q=query, maxResults=3
            ).execute()
            messages = results.get('messages', [])
            if messages:
                msg = self.service.users().messages().get(
                    userId='me', id=messages[0]['id']
                ).execute()
                payload = msg.get('payload', {})
                parts = payload.get('parts', [payload])
                body = ""
                for part in parts:
                    if part.get('mimeType') == 'text/plain':
                        data = part.get('body', {}).get('data', '')
                        if data:
                            body += base64.urlsafe_b64decode(data).decode()
                dna.log_action(f"📧 Email: {msg.get('snippet', '')[:50]}")
                return {"subject": msg.get('snippet', ''), "body": body[:500]}
            return None
        except Exception as e:
            return None
    
    def extract_link(self, msg: Dict) -> Optional[str]:
        if not msg: return None
        links = re.findall(r'https?://[^\s<>"]+verif[^\s<>"]*', msg.get('body', ''))
        if not links:
            links = re.findall(r'https?://[^\s<>"]+confirm[^\s<>"]*', msg.get('body', ''))
        return links[0] if links else None
    
    def extract_otp(self, msg: Dict) -> Optional[str]:
        if not msg: return None
        otps = re.findall(r'\b(\d{4,8})\b', msg.get('body', ''))
        return otps[0] if otps else None
    
    def execute(self, dna, action: str = "verify", platform: str = "") -> Dict:
        if action == "verify":
            dna.log_action(f"📧 Checking verification for {platform}...")
            msg = self.check_inbox(dna, f"verify OR confirm OR welcome {platform}")
            if msg:
                return {
                    "success": True,
                    "verification_link": self.extract_link(msg),
                    "otp": self.extract_otp(msg),
                    "subject": msg.get('subject', ''),
                }
            return {"success": False, "desc": "No verification email yet"}
        return {"success": False}

gmail_creator = GmailCreator()
