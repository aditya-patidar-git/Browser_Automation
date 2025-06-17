"""
AI service for generating email replies using OpenAI API.
"""
import openai
import os 
from typing import Dict, Any, Optional
from dataclasses import dataclass
from config import AIConfig
import logging

logger = logging.getLogger(__name__)

@dataclass
class EmailContext:
    """Email context for AI processing"""
    sender_name:str
    sender_email: str
    subject: str
    body: str
    timestamp: Optional[str] = None
    is_reply: bool = False

class AIEmailService:
    """AI service for generating email replies"""
    
    def __init__(self, config: AIConfig):
        self.config = config
        self.client = openai.OpenAI(api_key=config.openai_api_key)
    
    def _create_system_prompt(self) -> str:
        """Create system prompt for email reply generation"""
        return """You are a professional email assistant. Your task is to generate appropriate, 
        formal email replies based on the incoming email context. 

        Guidelines:
        - Keep replies professional and concise
        - Match the tone of the original email
        - Address the sender's main points
        - Use proper email etiquette
        - Keep responses under 200 words unless specifically required
        - Always include appropriate greetings and closings
        - If the email requires specific action, acknowledge it appropriately
        - Respond strictly based on the provided information. Do not infer, assume, or invent any details that are not clearly stated.
        - Do not unnecessarily ask or pop up some dialog for attachments if it has not been given in the first place.
        Return only the email body content without subject line or signatures."""
    
    def _create_user_prompt(self, email_context: EmailContext) -> str:
        """Create user prompt with email context"""
        receiver_name = os.getenv("RECEIVER_NAME", "").strip()
        return f"""
        Please generate a professional reply to the following email:
        
        From: {email_context.sender_email}
        Subject: {email_context.subject}
        
        Email Content:
        {email_context.body}
        
        Your reply should be concise, professional, and address the sender’s main points.
        Do **not** include a subject line or a signature block.
        Just end the reply with:

        Best regards,
        {receiver_name}

        Generate an appropriate reply that addresses the sender's message professionally.
        """
    
    async def generate_reply(self, email_context: EmailContext) -> str:
        """Generate AI reply for the given email context"""
        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": self._create_system_prompt()},
                    {"role": "user", "content": self._create_user_prompt(email_context)}
                ],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature
            )
            
            reply_content = response.choices[0].message.content.strip()
            logger.info(f"Generated reply for email from {email_context.sender_email}")
            return reply_content
            
        except Exception as e:
            logger.error(f"Error generating AI reply: {str(e)}")
            return self._get_fallback_reply(email_context)
    
    def _get_fallback_reply(self, email_context: EmailContext) -> str:
        """Provide fallback reply if AI generation fails"""
        return f"""Dear {email_context.sender_name},

Thank you for your email regarding "{email_context.subject}".

I have received your message and will review it carefully. I will get back to you with a detailed response shortly.

Best regards,
{os.getenv("RECEIVER_NAME","")}"""
    
    def analyze_email_priority(self, email_context: EmailContext) -> str:
        """Analyze email priority for processing order"""
        urgent_keywords = ['urgent', 'asap', 'immediate', 'emergency', 'critical']
        
        email_text = f"{email_context.subject} {email_context.body}".lower()
        
        if any(keyword in email_text for keyword in urgent_keywords):
            return "high"
        elif email_context.is_reply:
            return "medium"
        else:
            return "normal"