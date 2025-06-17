"""
Main email automation agent using modern LangChain approach.
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from langchain.tools import BaseTool
from langchain_openai import ChatOpenAI
from langchain.schema import BaseMessage
from langchain.callbacks.manager import CallbackManagerForToolRun
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel, Field

from config import Config
from browser_automation import BrowserAutomation, EmailMessage
from ai_service import AIEmailService, EmailContext
from human_behavior import HumanBehaviorSimulator
from email_processor import EmailProcessor

logger = logging.getLogger(__name__)

class CheckEmailsTool(BaseTool):
    """Tool for checking unread emails"""
    name: str = "check_emails"
    description: str = "Check for new unread emails in the inbox. No parameters needed."
    
    # Store references as class variables that will be set by the agent
    _browser_automation: Optional[BrowserAutomation] = None
    
    @classmethod
    def set_browser_automation(cls, browser_automation: BrowserAutomation):
        cls._browser_automation = browser_automation
    
    def _run(self, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Check for unread emails (sync wrapper)"""
        try:
            # Create new event loop if none exists
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            if loop.is_running():
                # If loop is running, we need to use a different approach
                return "Email check initiated (async context)"
            else:
                return loop.run_until_complete(self._arun())
        except Exception as e:
            return f"Error checking emails: {str(e)}"
    
    async def _arun(self, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Check for unread emails"""
        try:
            if not self._browser_automation:
                return "Error: Browser automation not initialized"
            
            emails = await self._browser_automation.get_unread_emails()
            email_summaries = []
            for email in emails[:5]:  # Limit to first 5 for summary
                email_summaries.append(f"From: {email.sender_email}, Subject: {email.subject}")
            
            result = f"Found {len(emails)} unread emails:\n" + "\n".join(email_summaries)
            return result
        except Exception as e:
            logger.error(f"Error checking emails: {str(e)}")
            return f"Error checking emails: {str(e)}"

class ProcessEmailInput(BaseModel):
    """Input for process email tool"""
    email_subject: str = Field(description="Subject of the email to process")

class ProcessEmailTool(BaseTool):
    """Tool for processing individual emails"""
    name: str = "process_email"
    description: str = "Process a specific email by its subject and generate AI reply"
    args_schema: type[BaseModel] = ProcessEmailInput
    
    # Store references as class variables
    _email_processor: Optional[EmailProcessor] = None
    _current_emails: List[EmailMessage] = []
    
    @classmethod
    def set_email_processor(cls, email_processor: EmailProcessor):
        cls._email_processor = email_processor
    
    @classmethod
    def set_current_emails(cls, emails: List[EmailMessage]):
        cls._current_emails = emails
    
    def _run(self, email_subject: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Process email (sync wrapper)"""
        try:
            # Create new event loop if none exists
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            if loop.is_running():
                return f"Processing initiated for email: {email_subject}"
            else:
                return loop.run_until_complete(self._arun(email_subject))
        except Exception as e:
            return f"Error processing email: {str(e)}"
    
    async def _arun(self, email_subject: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Process email and generate reply"""
        try:
            if not self._email_processor:
                return "Error: Email processor not initialized"
            
            # Find email by subject
            target_email = None
            for email in self._current_emails:
                if email_subject.lower() in email.subject.lower():
                    target_email = email
                    break
            
            if not target_email:
                return f"Email with subject '{email_subject}' not found"
            
            # Process the email
            result = await self._email_processor.process_single_email(target_email)
            
            if result.success:
                return f"Successfully processed email from {target_email.sender_email}. Reply sent: {result.reply_sent}"
            else:
                return f"Failed to process email: {result.error_message}"
                
        except Exception as e:
            logger.error(f"Error processing email: {str(e)}")
            return f"Error processing email: {str(e)}"

class SendReplyInput(BaseModel):
    """Input for send reply tool"""
    email_subject: str = Field(description="Subject of the email to reply to")
    reply_content: str = Field(description="Content of the reply to send")

class SendReplyTool(BaseTool):
    """Tool for sending email replies"""
    name: str = "send_reply"
    description: str = "Send a reply to an email by its subject"
    args_schema: type[BaseModel] = SendReplyInput
    
    # Store references as class variables
    _browser_automation: Optional[BrowserAutomation] = None
    _current_emails: List[EmailMessage] = []
    
    @classmethod
    def set_browser_automation(cls, browser_automation: BrowserAutomation):
        cls._browser_automation = browser_automation
    
    @classmethod
    def set_current_emails(cls, emails: List[EmailMessage]):
        cls._current_emails = emails
    
    def _run(self, email_subject: str, reply_content: str, 
             run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Send reply (sync wrapper)"""
        try:
            # Create new event loop if none exists
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            if loop.is_running():
                return f"Reply sending initiated for: {email_subject}"
            else:
                return loop.run_until_complete(self._arun(email_subject, reply_content))
        except Exception as e:
            return f"Error sending reply: {str(e)}"
    
    async def _arun(self, email_subject: str, reply_content: str,
                    run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Send reply to email"""
        try:
            if not self._browser_automation:
                return "Error: Browser automation not initialized"
            
            # Find email by subject
            target_email = None
            for email in self._current_emails:
                if email_subject.lower() in email.subject.lower():
                    target_email = email
                    break
            
            if not target_email:
                return f"Email with subject '{email_subject}' not found"
            
            # Send the reply
            success = await self._browser_automation.send_reply(target_email, reply_content)
            
            if success:
                return f"Successfully sent reply to {target_email.sender_email}"
            else:
                return f"Failed to send reply to {target_email.sender_email}"
                
        except Exception as e:
            logger.error(f"Error sending reply: {str(e)}")
            return f"Error sending reply: {str(e)}"

class EmailAutomationAgent:
    """Main email automation agent using modern LangChain"""
    
    def __init__(self, config: Config):
        self.config = config
        self.human_simulator = HumanBehaviorSimulator(config.throttling)
        self.browser_automation = BrowserAutomation(
            config.browser, 
            config.email, 
            self.human_simulator
        )
        self.ai_service = AIEmailService(config.ai)
        self.email_processor = EmailProcessor(
            self.browser_automation,
            self.ai_service
        )
        
        # Initialize LangChain components
        self.llm = ChatOpenAI(
            model=config.ai.model,
            openai_api_key=config.ai.openai_api_key,
            temperature=config.ai.temperature
        )
        
        # Set up tool dependencies
        CheckEmailsTool.set_browser_automation(self.browser_automation)
        ProcessEmailTool.set_email_processor(self.email_processor)
        SendReplyTool.set_browser_automation(self.browser_automation)
        
        # Initialize tools
        self.tools = [
            CheckEmailsTool(),
            ProcessEmailTool(),
            SendReplyTool()
        ]
        
        # Create prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a professional email automation assistant. You can:
            1. Check for unread emails using check_emails
            2. Process individual emails using process_email 
            3. Send replies using send_reply

            Always be professional and efficient. When processing emails:
            - Check for new emails first
            - Prioritize urgent emails
            - Generate appropriate replies
            - Confirm actions taken

            Be concise but thorough in your responses."""),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # Create agent
        self.agent = create_openai_functions_agent(self.llm, self.tools, self.prompt)
        
        # Create agent executor
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=10,
            max_execution_time=300  # 5 minutes timeout
        )
        
        self.is_running = False
        self.processed_emails = set()
        self.current_emails: List[EmailMessage] = []
    
    async def initialize(self) -> bool:
        """Initialize the agent and login to email platform"""
        try:
            await self.browser_automation.initialize_browser()
            login_success = await self.browser_automation.login()
            
            if login_success:
                logger.info("Email agent initialized successfully")
                return True
            else:
                logger.error("Failed to login to email platform")
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize agent: {str(e)}")
            return False
    
    async def run_email_check_cycle(self):
        """Run a single email check and processing cycle"""
        try:
            # Check for unread emails
            emails = await self.browser_automation.get_unread_emails()
            self.current_emails = emails
            
            # Update tools with current emails
            ProcessEmailTool.set_current_emails(emails)
            SendReplyTool.set_current_emails(emails)
            
            if not emails:
                logger.info("No unread emails found")
                return
            
            logger.info(f"Found {len(emails)} unread emails")
            
            # Use agent to process emails
            task_prompt = f"""
            I found {len(emails)} unread emails. Please:
            1. Check the emails to see what we have
            2. Process each email individually, starting with any urgent ones
            3. Generate and send appropriate replies
            
            Here are the email subjects for reference:
            {chr(10).join([f"- {email.subject} (from {email.sender_email})" for email in emails[:5]])}
            """
            
            # Execute through agent
            try:
                result = await self.agent_executor.ainvoke({"input": task_prompt})
                logger.info(f"Agent processing result: {result.get('output', 'No output')}")
            except Exception as e:
                logger.error(f"Error in agent execution: {str(e)}")
                # Fallback to direct processing
                await self._fallback_processing(emails)
        
        except Exception as e:
            logger.error(f"Error in email check cycle: {str(e)}")
    
    async def _fallback_processing(self, emails: List[EmailMessage]):
        """Fallback email processing without agent"""
        logger.info("Using fallback processing method")
        
        for email in emails[:3]:  # Process first 3 emails
            if email.id in self.processed_emails:
                continue
            
            try:
                # Get full email content
                email_body = await self.browser_automation.open_email(email)
                if not email_body:
                    continue
                
                email.body = email_body
                
                # Create email context for AI processing
                email_context = EmailContext(
                    sender_name=email.sender_name,
                    sender_email=email.sender_email,
                    subject=email.subject,
                    body=email.body,
                    timestamp=email.timestamp,
                    is_reply=email.is_reply
                )
                
                # Generate AI reply
                reply_content = await self.ai_service.generate_reply(email_context)
                
                # Send the reply
                success = await self.browser_automation.send_reply(email, reply_content)
                
                if success:
                    self.processed_emails.add(email.id)
                    logger.info(f"Successfully processed and replied to email from {email.sender_email}")
                else:
                    logger.error(f"Failed to send reply to {email.sender_email}")
                
                # Human-like delay between processing emails
                await self.human_simulator.random_delay(3.0, 7.0)
                
            except Exception as e:
                logger.error(f"Error processing email {email.id}: {str(e)}")
                continue
    
    async def start_monitoring(self):
        """Start continuous email monitoring"""
        self.is_running = True
        logger.info("Starting email monitoring...")
        
        while self.is_running:
            try:
                await self.run_email_check_cycle()
                
                # Wait for next check interval
                await asyncio.sleep(self.config.email.inbox_check_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(30)  # Wait before retrying
    
    def stop_monitoring(self):
        """Stop email monitoring"""
        self.is_running = False
        logger.info("Stopping email monitoring...")
    
    async def process_emails_once(self):
        """Process emails once without continuous monitoring"""
        if not await self.initialize():
            return False
        
        await self.run_email_check_cycle()
        await self.cleanup()
        return True
    
    async def cleanup(self):
        """Clean up resources"""
        await self.browser_automation.close_browser()
        logger.info("Agent cleanup completed")
    
    async def run_with_langchain_orchestration(self, task_description: str):
        """Run agent with LangChain orchestration for complex tasks"""
        try:
            # Update tools with current emails if available
            if self.current_emails:
                ProcessEmailTool.set_current_emails(self.current_emails)
                SendReplyTool.set_current_emails(self.current_emails)
            
            # Use the agent executor to interpret and execute complex tasks
            result = await self.agent_executor.ainvoke({"input": task_description})
            return result.get('output', 'No output from agent')
        except Exception as e:
            logger.error(f"Error in LangChain orchestration: {str(e)}")
            return f"Error: {str(e)}"