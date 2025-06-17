"""
Email processing logic for analyzing and handling email messages.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import re
import asyncio

from browser_automation import BrowserAutomation, EmailMessage
from ai_service import AIEmailService, EmailContext

logger = logging.getLogger(__name__)

@dataclass
class ProcessingResult:
    """Result of email processing"""
    email_id: str
    success: bool
    reply_generated: bool
    reply_sent: bool
    error_message: Optional[str] = None
    priority: str = "normal"
    processing_time: float = 0.0

class EmailProcessor:
    """Handles email processing workflow"""
    
    def __init__(self, browser_automation: BrowserAutomation, ai_service: AIEmailService):
        self.browser_automation = browser_automation
        self.ai_service = ai_service
        self.processed_emails: Dict[str, ProcessingResult] = {}
        
    def _extract_email_metadata(self, email: EmailMessage) -> Dict[str, Any]:
        """Extract metadata from email for processing decisions"""
        metadata = {
            'sender_domain': email.sender_email.split('@')[1] if '@' in email.sender_email else '',
            'subject_length': len(email.subject),
            'body_length': len(email.body) if email.body else 0,
            'has_attachments': False,  # Would need to detect from UI
            'is_automated': self._is_automated_email(email),
            'contains_links': self._contains_links(email.body) if email.body else False,
            'is_urgent': self._is_urgent_email(email),
            'requires_action': self._requires_action(email)
        }
        return metadata
    
    def _is_automated_email(self, email: EmailMessage) -> bool:
        """Detect if email is automated/promotional"""
        automated_indicators = [
            'noreply', 'no-reply', 'donotreply', 'automated', 'notification',
            'newsletter', 'marketing', 'promo', 'unsubscribe'
        ]
        
        email_text = f"{email.sender_email} {email.subject}".lower()
        return any(indicator in email_text for indicator in automated_indicators)
    
    def _contains_links(self, body: str) -> bool:
        """Check if email body contains links"""
        if not body:
            return False
        
        link_patterns = [
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            r'www\.[\w\.-]+',
            r'[\w\.-]+\.com'
        ]
        
        for pattern in link_patterns:
            if re.search(pattern, body, re.IGNORECASE):
                return True
        return False
    
    def _is_urgent_email(self, email: EmailMessage) -> bool:
        """Check if email is urgent based on subject and content"""
        urgent_keywords = [
            'urgent', 'asap', 'immediate', 'emergency', 'critical', 'important',
            'deadline', 'time-sensitive', 'priority', 'rush'
        ]
        
        email_text = f"{email.subject} {email.body}".lower()
        return any(keyword in email_text for keyword in urgent_keywords)
    
    def _requires_action(self, email: EmailMessage) -> bool:
        """Check if email requires specific action"""
        action_keywords = [
            'please', 'request', 'need', 'require', 'confirm', 'approve',
            'review', 'feedback', 'response', 'reply', 'meeting', 'schedule'
        ]
        
        email_text = f"{email.subject} {email.body}".lower()
        return any(keyword in email_text for keyword in action_keywords)
    
    def _should_skip_email(self, email: EmailMessage, metadata: Dict[str, Any]) -> Tuple[bool, str]:
        """Determine if email should be skipped"""
        # Skip automated emails
        if metadata['is_automated']:
            return True, "Automated email detected"
        
        # Skip very short emails that might be spam
        if metadata['subject_length'] < 5:
            return True, "Subject too short"
        
        # Skip emails from known spam domains (would need a list)
        spam_domains = ['spam.com', 'test.com']  # Example
        if metadata['sender_domain'] in spam_domains:
            return True, "Spam domain detected"
        
        return False, ""
    
    def _create_email_context(self, email: EmailMessage) -> EmailContext:
        """Create EmailContext from EmailMessage"""
        return EmailContext(
            sender_name=email.sender_name,
            sender_email=email.sender_email,
            subject=email.subject,
            body=email.body,
            timestamp=email.timestamp,
            is_reply=email.is_reply
        )
    
    async def process_single_email(self, email: EmailMessage) -> ProcessingResult:
        """Process a single email completely"""
        start_time = datetime.now()
        
        try:
            # Extract metadata
            metadata = self._extract_email_metadata(email)
            
            # Check if should skip
            should_skip, skip_reason = self._should_skip_email(email, metadata)
            if should_skip:
                logger.info(f"Skipping email {email.id}: {skip_reason}")
                return ProcessingResult(
                    email_id=email.id,
                    success=True,
                    reply_generated=False,
                    reply_sent=False,
                    error_message=f"Skipped: {skip_reason}"
                )
            
            # Get full email content if not already loaded
            if not email.body:
                email_body = await self.browser_automation.open_email(email)
                if not email_body:
                    return ProcessingResult(
                        email_id=email.id,
                        success=False,
                        reply_generated=False,
                        reply_sent=False,
                        error_message="Could not load email content"
                    )
                email.body = email_body
            
            # Create context for AI processing
            email_context = self._create_email_context(email)
            
            # Analyze priority
            priority = self.ai_service.analyze_email_priority(email_context)
            
            # Generate AI reply
            reply_content = await self.ai_service.generate_reply(email_context)
            
            if not reply_content:
                return ProcessingResult(
                    email_id=email.id,
                    success=False,
                    reply_generated=False,
                    reply_sent=False,
                    error_message="Failed to generate reply",
                    priority=priority
                )
            
            # Send reply
            reply_sent = await self.browser_automation.send_reply(email, reply_content)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = ProcessingResult(
                email_id=email.id,
                success=reply_sent,
                reply_generated=True,
                reply_sent=reply_sent,
                priority=priority,
                processing_time=processing_time
            )
            
            self.processed_emails[email.id] = result
            
            if reply_sent:
                logger.info(f"Successfully processed email {email.id} from {email.sender_email}")
            else:
                logger.error(f"Failed to send reply for email {email.id}")
            
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"Error processing email: {str(e)}"
            logger.error(error_msg)
            
            result = ProcessingResult(
                email_id=email.id,
                success=False,
                reply_generated=False,
                reply_sent=False,
                error_message=error_msg,
                processing_time=processing_time
            )
            
            self.processed_emails[email.id] = result
            return result
    
    async def process_email_batch(self, emails: List[EmailMessage]) -> List[ProcessingResult]:
        """Process multiple emails with priority ordering"""
        if not emails:
            return []
        
        # Sort emails by priority (urgent first)
        prioritized_emails = []
        for email in emails:
            email_context = self._create_email_context(email)
            priority = self.ai_service.analyze_email_priority(email_context)
            prioritized_emails.append((email, priority))
        
        # Sort by priority (high -> medium -> normal)
        priority_order = {'high': 0, 'medium': 1, 'normal': 2}
        prioritized_emails.sort(key=lambda x: priority_order.get(x[1], 3))
        
        results = []
        for email, priority in prioritized_emails:
            result = await self.process_single_email(email)
            results.append(result)
            
            # Add delay between processing emails
            await asyncio.sleep(2)
        
        return results
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get statistics about processed emails"""
        if not self.processed_emails:
            return {
                'total_processed': 0,
                'successful': 0,
                'failed': 0,
                'replies_generated': 0,
                'replies_sent': 0,
                'average_processing_time': 0.0
            }
        
        total = len(self.processed_emails)
        successful = sum(1 for r in self.processed_emails.values() if r.success)
        failed = total - successful
        replies_generated = sum(1 for r in self.processed_emails.values() if r.reply_generated)
        replies_sent = sum(1 for r in self.processed_emails.values() if r.reply_sent)
        avg_time = sum(r.processing_time for r in self.processed_emails.values()) / total
        
        return {
            'total_processed': total,
            'successful': successful,
            'failed': failed,
            'replies_generated': replies_generated,
            'replies_sent': replies_sent,
            'average_processing_time': round(avg_time, 2),
            'success_rate': round((successful / total) * 100, 2)
        }
    
    def get_failed_emails(self) -> List[ProcessingResult]:
        """Get list of failed email processing attempts"""
        return [result for result in self.processed_emails.values() if not result.success]
    
    def clear_processing_history(self):
        """Clear processing history"""
        self.processed_emails.clear()
        logger.info("Processing history cleared")