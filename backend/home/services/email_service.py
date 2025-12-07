import smtplib
import logging
from email.mime.text import MIMEText
from typing import List
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending plain text email alerts"""
    
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER', '')
        self.smtp_port = int(os.getenv('SMTP_PORT', '25'))
        self.smtp_username = os.getenv('SMTP_USERNAME', '')
        self.from_email = os.getenv('SMTP_FROM_EMAIL', self.smtp_username)
        self.enabled = os.getenv('EMAIL_ALERTS_ENABLED', 'true').lower() == 'true'
        self.smtp_timeout = int(os.getenv('SMTP_TIMEOUT_SECONDS', '60'))
        # Authentication is optional - some internal SMTP servers don't require it
        self.use_auth = os.getenv('SMTP_USE_AUTH', 'false').lower() == 'true'
        
        if not self.smtp_server:
            logger.warning("SMTP server not configured. Email alerts will be disabled.")
            self.enabled = False
        
        if self.use_auth and not self.smtp_username:
            logger.warning("SMTP authentication enabled but username not configured. Email alerts will be disabled.")
            self.enabled = False
    
    def send_gpu_memory_alert(
        self,
        server_name: str,
        server_ip: str,
        gpu_index: int,
        gpu_name: str,
        current_usage_pct: float,
        usage_limit: int,
        memory_used_mib: int,
        memory_total_mib: int,
        recipient_emails: List[str]
    ) -> bool:
        
        if not self.enabled:
            logger.warning("Email alerts are disabled. Skipping email send.")
            return False
        
        if not recipient_emails:
            logger.warning(f"No recipient emails configured for server {server_name}")
            return False
        
        # Simple subject line
        subject = f"GPU Memory Alert: {server_name} GPU {gpu_index} at {current_usage_pct:.1f}%"
        
        # Plain text message
        message = f"""GPU memory usage has exceeded the configured limit.

Server: {server_name} ({server_ip})
GPU: GPU {gpu_index} - {gpu_name}
Current Usage: {current_usage_pct:.1f}%
Threshold: {usage_limit}%
Memory: {memory_used_mib:,} MiB used of {memory_total_mib:,} MiB total
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This is an automated alert from the GPU Monitoring System.
"""
        
        return self._send_email(recipient_emails, subject, message)
    
    def _send_email(self, to_emails: List[str], subject: str, message: str) -> bool:
        """
        Send plain text email via SMTP (with or without authentication)
        
        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            message: Plain text message body
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            logger.debug(f"Connecting to {self.smtp_server}:{self.smtp_port}")
            
            # Simple SMTP connection without authentication (like check.py implementation)
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=self.smtp_timeout) as server:
                server.ehlo()  # Identify to the server
                logger.debug("EHLO sent successfully")
                
                # Refresh server capabilities
                server.ehlo()
                
                # Send email using simple sendmail (no MIMEText needed for basic messages)
                message_with_headers = f"Subject: {subject}\r\n\r\n{message}"
                server.sendmail(
                    from_addr=self.from_email,
                    to_addrs=to_emails,
                    msg=message_with_headers
                )
            
            logger.info(f"Alert email sent successfully to {len(to_emails)} recipients")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP Authentication failed: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error occurred: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email: {e}", exc_info=True)
            return False

# Global instance
email_service = EmailService()

