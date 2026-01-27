import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from .base import BaseTool
import os

class EmailTool(BaseTool):
    name = "send_email"
    description = "Send an email. Args: {'subject': 'subject line', 'body': 'email content'}"
    
    def execute(self, subject, body):
        """Send an email"""
        try:
            sender = os.getenv("EMAIL_SENDER")
            password = os.getenv("EMAIL_PASSWORD")
            recipient = os.getenv("EMAIL_RECIPIENT")
            
            if not all([sender, password, recipient]):
                return {
                    "success": False,
                    "error": "Email credentials not configured in .env"
                }
            
            print(f"[Email] Sending email to: {recipient}")
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = sender
            msg['To'] = recipient
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send via Gmail SMTP
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
            server.quit()
            
            return {
                "success": True,
                "data": f"Email sent to {recipient}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
