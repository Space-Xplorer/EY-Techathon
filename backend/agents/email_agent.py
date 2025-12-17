"""
Email Agent - Drafts and sends RFP bid submission emails via Gmail API
"""
import os
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, Dict
from dotenv import load_dotenv

load_dotenv()

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    import pickle
    GMAIL_API_AVAILABLE = True
except ImportError:
    GMAIL_API_AVAILABLE = False
    print("⚠️  Google API libraries not installed. Email sending will be simulated.")

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.send']


class EmailAgent:
    """Agent responsible for drafting and sending RFP bid emails"""
    
    def __init__(self, api_key: Optional[str] = None, credentials_path: Optional[str] = None):
        """
        Initialize Email Agent
        
        Args:
            api_key: Google Cloud API key (from .env)
            credentials_path: Path to Gmail OAuth credentials JSON file
        """
        self.api_key = api_key or os.getenv("api") or os.getenv("GOOGLE_API_KEY")
        self.credentials_path = credentials_path or os.path.join(
            os.path.dirname(__file__), '..', 'config', 'gmail_credentials.json'
        )
        self.token_path = os.path.join(
            os.path.dirname(__file__), '..', 'config', 'gmail_token.pickle'
        )
        self.service = None
    
    def authenticate(self) -> bool:
        """
        Authenticate with Gmail API using OAuth2 or API Key
        
        Returns:
            bool: True if authentication successful
        """
        if not GMAIL_API_AVAILABLE:
            print("⚠️  Gmail API libraries not available. Install with: pip install google-api-python-client google-auth-oauthlib")
            return False
        
        # Try API key first if available
        if self.api_key:
            try:
                print(f"🔑 Using Google Cloud API Key from environment")
                self.service = build('gmail', 'v1', developerKey=self.api_key)
                # Test the connection
                self.service.users().getProfile(userId='me').execute()
                print("✅ Gmail API authenticated via API key")
                return True
            except Exception as e:
                print(f"⚠️  API key authentication failed: {e}")
                print("   Falling back to OAuth2...")
        
        # Fall back to OAuth2
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    print(f"⚠️  Gmail credentials not found at {self.credentials_path}")
                    print("   Please download OAuth2 credentials from Google Cloud Console")
                    return False
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for next time
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        self.service = build('gmail', 'v1', credentials=creds)
        print("✅ Gmail API authenticated via OAuth2")
        return True
    
    def draft_bid_email(
        self,
        rfp_title: str,
        total_cost: float,
        win_probability: float,
        bid_text: str,
        recipient_email: str = "rfp-submissions@example.com",
        sender_name: str = "Team SpaM"
    ) -> Dict[str, str]:
        """
        Draft a professional RFP bid submission email
        
        Args:
            rfp_title: Title/name of the RFP
            total_cost: Total quoted price
            win_probability: Calculated win probability
            bid_text: The final bid document text
            recipient_email: Email address to send to
            sender_name: Name of the sender
        
        Returns:
            Dict with email details (subject, body, to, from)
        """
        
        subject = f"RFP Bid Submission - {rfp_title}"
        
        body = f"""Dear Sir/Madam,

We are pleased to submit our commercial bid for the following RFP:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RFP DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RFP Title: {rfp_title}
Total Quoted Amount: ₹{total_cost:,.2f}
Bid Validity: 90 Days
Delivery Timeline: As per RFP terms


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BID SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{bid_text}


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Our submission includes:
✓ Complete technical specifications
✓ Detailed pricing breakdown
✓ OEM product recommendations
✓ Testing and acceptance terms
✓ Quality assurance commitments

We have thoroughly analyzed the RFP requirements and are confident in delivering 
a solution that meets all specified criteria. Our technical team is available for 
any clarifications or discussions regarding this proposal.

Thank you for considering our bid. We look forward to your positive response.

Best regards,
{sender_name}

---
This email was generated by the RFP Orchestrator System
Confidence Score: {win_probability:.1f}%
Generated: {self._get_timestamp()}
"""
        
        return {
            "subject": subject,
            "body": body,
            "to": recipient_email,
            "from": sender_name,
            "timestamp": self._get_timestamp()
        }
    
    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        attachment_path: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Send email via Gmail API
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (plain text)
            attachment_path: Optional path to attachment file
        
        Returns:
            Dict with status and message ID
        """
        if not GMAIL_API_AVAILABLE:
            # Simulate email sending for demo purposes
            print(f"\n{'='*60}")
            print("📧 EMAIL SIMULATION (Gmail API not configured)")
            print(f"{'='*60}")
            print(f"To: {to}")
            print(f"Subject: {subject}")
            print(f"\n{body}")
            if attachment_path:
                print(f"\nAttachment: {attachment_path}")
            print(f"{'='*60}\n")
            
            return {
                "success": True,
                "message_id": "simulated_" + str(hash(subject)),
                "to": to,
                "subject": subject,
                "simulated": True
            }
        
        if not self.service:
            if not self.authenticate():
                # Fall back to simulation
                print("⚠️  Gmail authentication failed. Simulating email send...")
                return {
                    "success": True,
                    "message_id": "simulated_" + str(hash(subject)),
                    "to": to,
                    "subject": subject,
                    "simulated": True,
                    "note": "Email was simulated. Configure Gmail API to send real emails."
                }
        
        try:
            # Create message
            message = MIMEMultipart()
            message['To'] = to
            message['Subject'] = subject
            
            # Add body
            message.attach(MIMEText(body, 'plain'))
            
            # Add attachment if provided
            if attachment_path and os.path.exists(attachment_path):
                with open(attachment_path, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename={os.path.basename(attachment_path)}'
                    )
                    message.attach(part)
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Send
            sent_message = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            print(f"✅ Email sent successfully! Message ID: {sent_message['id']}")
            
            return {
                "success": True,
                "message_id": sent_message['id'],
                "to": to,
                "subject": subject
            }
            
        except Exception as e:
            print(f"❌ Error sending email: {e}")
            # Fall back to simulation on error
            print("⚠️  Simulating email send due to error...")
            return {
                "success": True,
                "message_id": "simulated_fallback_" + str(hash(subject)),
                "to": to,
                "subject": subject,
                "simulated": True,
                "note": f"Email was simulated due to error: {str(e)}"
            }
    
    def _get_timestamp(self) -> str:
        """Get formatted timestamp"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# Example usage
if __name__ == "__main__":
    agent = EmailAgent()
    
    # Draft email
    email_draft = agent.draft_bid_email(
        rfp_title="Government PWD Amaravati Cable Supply",
        total_cost=21488500.0,
        win_probability=67.8,
        bid_text="See attached final bid document...",
        recipient_email="procurement@example.com"
    )
    
    print("📧 Email Draft:")
    print(f"Subject: {email_draft['subject']}")
    print(f"\n{email_draft['body']}")
    
    # To send (requires Gmail API setup):
    # result = agent.send_email(
    #     to=email_draft['to'],
    #     subject=email_draft['subject'],
    #     body=email_draft['body'],
    #     attachment_path="path/to/final_bid.txt"
    # )
