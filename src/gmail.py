from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import base64
from email import policy
from email.parser import BytesParser
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def authenticate():
    token_path = PROJECT_ROOT / "token.json"
    credentials = None

    # reuse saved credentials if they are still valid
    if token_path.exists():
        credentials = Credentials.from_authorized_user_file(
            str(token_path),
            SCOPES,
        )

    
    if not credentials or not credentials.valid:
        # access token expired and a refresh token exists
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        # no usable saved authorization exists, opens browser sign-in
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(PROJECT_ROOT / "credentials.json"),
                SCOPES,
            )
            credentials = flow.run_local_server(port=0)

        token_path.write_text(credentials.to_json())

    return credentials
    
    
def get_email_body(service, message_id):
    # fetch the raw email
    result = service.users().messages().get(
        userId="me",
        id=message_id,
        format="raw",
    ).execute()

    raw_data = result["raw"]
    raw_data += "=" * (-len(raw_data) % 4)
    email_bytes = base64.urlsafe_b64decode(raw_data)

    # decode the email into bytes
    message = BytesParser(policy=policy.default).parsebytes(email_bytes)

    # parses email structure, preferring plain text and falling back to HTML if necessary
    body = message.get_body(preferencelist=("plain", "html"))

    if body is None:
        return ""

    content = body.get_content()

    # converts HTML to text
    if body.get_content_type() == "text/html":
        soup = BeautifulSoup(content, "html.parser")

        for element in soup(["script", "style"]):
            element.decompose()

        content = soup.get_text(separator="\n", strip=True)

    return content
    
    
def fetch_recent_emails(credentials):
    # creates a Gmail client using my authorization
    service = build("gmail", "v1", credentials=credentials)

    # finds matching messages and returns their IDs 
    results = service.users().messages().list(
        userId="me",
        q="newer_than:7d",
        maxResults=5,
    ).execute()

    # retrieves the requested headers for each ID
    messages = results.get("messages", [])
    emails = []

    for message in messages:
        # sends each request to Google
        email = service.users().messages().get(
            userId="me",
            id=message["id"],
            format="metadata",
            metadataHeaders=["Subject", "From"],
        ).execute()

        headers = {
            header["name"].lower(): header["value"]
            for header in email["payload"].get("headers", [])
        }

        body = get_email_body(service, message["id"])
        
        emails.append({
            "id": message["id"],
            "sender": headers.get("from", ""),
            "subject": headers.get("subject", ""),
            "body": body,
        })

    return emails
        
    
if __name__ == "__main__":
    credentials = authenticate()
    emails = fetch_recent_emails(credentials)

    print(f"Fetched {len(emails)} email(s).")

    if emails:
        print("Subject:", emails[0]["subject"])
        print("Body length:", len(emails[0]["body"]), "characters")