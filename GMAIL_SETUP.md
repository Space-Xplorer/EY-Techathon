# Gmail API Setup Guide

## Overview
The Email Agent uses Gmail API to send RFP bid submission emails automatically after user approval.

## Prerequisites
- Google account
- Python 3.8+
- Google Cloud Console access

## Setup Steps

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **"Create Project"**
3. Name it: `RFP-Orchestrator` or similar
4. Click **"Create"**

### 2. Enable Gmail API

1. In your project, go to **"APIs & Services" → "Library"**
2. Search for **"Gmail API"**
3. Click on it and press **"Enable"**

### 3. Create OAuth 2.0 Credentials

1. Go to **"APIs & Services" → "Credentials"**
2. Click **"+ CREATE CREDENTIALS"** → **"OAuth client ID"**
3. If prompted, configure the consent screen:
   - User Type: **External**
   - App name: `RFP Orchestrator`
   - User support email: Your email
   - Developer contact: Your email
   - Scopes: Add `gmail.send`
   - Test users: Add your Gmail address
4. Back to Credentials → Create OAuth client ID:
   - Application type: **Desktop app**
   - Name: `RFP Email Client`
5. Click **"CREATE"**
6. Download the JSON file (looks like `client_secret_XXX.json`)

### 4. Install Python Dependencies

```bash
cd backend
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

Or add to `requirements.txt`:
```
google-auth==2.25.2
google-auth-oauthlib==1.2.0
google-auth-httplib2==0.2.0
google-api-python-client==2.111.0
```

### 5. Configure Credentials

1. Create a `config` folder in backend:
   ```bash
   mkdir backend/config
   ```

2. Copy your downloaded JSON file to:
   ```
   backend/config/gmail_credentials.json
   ```

3. Add to `.gitignore`:
   ```
   backend/config/gmail_credentials.json
   backend/config/gmail_token.pickle
   ```

### 6. Set Environment Variables (Optional)

In `backend/.env`:
```env
RFP_RECIPIENT_EMAIL=procurement@client-company.com
GMAIL_SENDER_NAME=Team SpaM
```

### 7. First-Time Authentication

When you first run the email agent:

```bash
cd backend
python -c "from agents.email_agent import EmailAgent; agent = EmailAgent(); agent.authenticate()"
```

This will:
1. Open a browser window
2. Ask you to sign in to your Google account
3. Request permission to send emails
4. Save credentials to `gmail_token.pickle`

**Important**: You only need to do this once. The token will be reused for future emails.

## Usage

### Test Email Draft (No Sending)

```python
from agents.email_agent import EmailAgent

agent = EmailAgent()
email = agent.draft_bid_email(
    rfp_title="Government PWD Amaravati",
    total_cost=21488500.0,
    win_probability=67.8,
    bid_text="Your bid text here...",
    recipient_email="client@example.com"
)

print(email['subject'])
print(email['body'])
```

### Send Email via API

From frontend (after user approves):
```javascript
const response = await fetch(
  `http://localhost:8000/rfp/${threadId}/approve-email?approved=true`,
  { method: 'POST' }
);
const result = await response.json();
console.log(result);  // { status: "email_sent", message: "...", result: {...} }
```

### Send Email Programmatically

```python
from agents.email_agent import EmailAgent

agent = EmailAgent()

result = agent.send_email(
    to="client@example.com",
    subject="RFP Bid Submission - Project XYZ",
    body="Email body here...",
    attachment_path="backend/data/output/final_bid.txt"
)

if result['success']:
    print(f"✅ Email sent! Message ID: {result['message_id']}")
else:
    print(f"❌ Failed: {result['error']}")
```

## Workflow Integration

The email agent is integrated into the workflow after bid generation:

```
loader → sales → technical → [human_gate] → pricing → bid → email_draft → [email_gate] → email_send
```

**Pause Points**:
1. `human_gate` - User selects which RFP file to proceed with
2. `email_gate` - User approves/rejects email sending

## Security Notes

### Important Security Practices

1. **Never commit credentials**:
   ```bash
   # Add to .gitignore
   config/gmail_credentials.json
   config/gmail_token.pickle
   ```

2. **Use test users during development**:
   - In Google Cloud Console → OAuth consent screen
   - Add test users (your email addresses)
   - Only these users can receive emails until app is published

3. **Production deployment**:
   - Store credentials in environment variables or secret managers
   - Use service accounts for automated emails
   - Implement rate limiting

4. **Token security**:
   - `gmail_token.pickle` contains authentication tokens
   - Keep it secure (same as passwords)
   - Rotate if compromised

## Troubleshooting

### Error: "credentials not found"
- Ensure `gmail_credentials.json` is in `backend/config/`
- Check file path in `email_agent.py`

### Error: "insufficient permissions"
- Re-run authentication: `agent.authenticate()`
- Check OAuth scopes include `gmail.send`

### Error: "invalid grant"
- Token expired - delete `gmail_token.pickle` and re-authenticate
- Check system clock is correct

### Emails not sending
- Check Gmail API is enabled in Cloud Console
- Verify test users are added (for unpublished apps)
- Check recipient email is valid

### Rate limits
- Gmail API limits: 100 emails/second, 1 billion/day
- For high volume, use batch sending

## Alternative: SMTP (No OAuth)

If Gmail API is too complex, you can use SMTP:

```python
import smtplib
from email.mime.text import MIMEText

def send_via_smtp(to, subject, body, smtp_user, smtp_pass):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = smtp_user
    msg['To'] = to
    
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
```

**Note**: Requires "App Password" from Google account settings.

## Support

For issues:
1. Check [Gmail API Documentation](https://developers.google.com/gmail/api)
2. Review [Python Quickstart](https://developers.google.com/gmail/api/quickstart/python)
3. Check error logs in backend console
