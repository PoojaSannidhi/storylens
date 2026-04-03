"""
tools/email_tools.py

SendGrid email tool for StoryLens.
Sends the generated children's book PDF to the parent.

Same pattern as pr_lens email_tools.py.
"""

import os
import base64
from typing import Dict
from crewai.tools import tool


@tool("Send Children's Book via Email")
def send_email(
    to_email: str,
    book_title: str,
    child_name: str,
    pdf_path: str,
) -> Dict[str, str]:
    """
    Sends the generated children's book PDF to the parent via SendGrid.

    Args:
        to_email:   Parent's email address
        book_title: Title of the generated book
        child_name: Name of the child hero
        pdf_path:   Path to the generated PDF file

    Returns:
        Dict with status and message.
    """
    import sendgrid
    from sendgrid.helpers.mail import (
        Mail, Email, To, Content, Attachment,
        FileContent, FileName, FileType, Disposition
    )

    api_key    = os.environ.get("SENDGRID_API_KEY")
    from_email = os.environ.get("SENDGRID_FROM_EMAIL")
    recipient  = to_email.strip() or os.environ.get("SENDGRID_TO_EMAIL", "")

    if not all([api_key, from_email, recipient]):
        return {
            "status": "skipped",
            "reason": "SendGrid not configured or no recipient provided"
        }

    if not os.path.exists(pdf_path):
        return {
            "status": "error",
            "reason": f"PDF file not found at {pdf_path}"
        }

    try:
        # Read and encode PDF
        with open(pdf_path, "rb") as f:
            pdf_data = base64.b64encode(f.read()).decode()

        # Build email
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #3264c8;">📚 {child_name}'s Book is Ready!</h1>
            <p style="font-size: 16px; color: #555;">
                Your personalized children's book <strong>"{book_title}"</strong> 
                has been generated just for <strong>{child_name}</strong>!
            </p>
            <p style="font-size: 16px; color: #555;">
                Find the PDF attached to this email. 
                Print it out and enjoy reading together! 🌟
            </p>
            <p style="font-size: 14px; color: #999; margin-top: 40px;">
                Made with ❤️ by StoryLens AI
            </p>
        </div>
        """

        message = Mail(
            from_email=Email(from_email),
            to_emails=To(recipient),
            subject=f"📚 {child_name}'s Book is Ready — {book_title}",
            html_content=Content("text/html", html_body),
        )

        # Attach PDF
        attachment = Attachment(
            file_content=FileContent(pdf_data),
            file_name=FileName(f"{child_name}_storylens_book.pdf"),
            file_type=FileType("application/pdf"),
            disposition=Disposition("attachment"),
        )
        message.attachment = attachment

        # Send
        sg = sendgrid.SendGridAPIClient(api_key=api_key)
        response = sg.send(message)

        if response.status_code in [200, 202]:
            return {
                "status": "success",
                "sent_to": recipient,
                "book": book_title,
            }
        else:
            return {
                "status": "error",
                "reason": f"SendGrid returned status {response.status_code}",
            }

    except Exception as e:
        return {
            "status": "error",
            "reason": str(e),
        }