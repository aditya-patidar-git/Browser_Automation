"""
Main entry point for the email automation agent.
"""
import asyncio
import logging
import signal
import sys
from typing import Optional

from config import Config
from email_agent import EmailAutomationAgent
import asyncio.base_subprocess

def safe_del(self):
    try:
        self.close()
    except (RuntimeError, Exception):
        pass  # Ignore event loop closed error

asyncio.base_subprocess.BaseSubprocessTransport.__del__ = safe_del

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('email_agent.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class EmailAgentRunner:
    """Main runner for the email automation agent"""
    
    def __init__(self):
        self.agent: Optional[EmailAutomationAgent] = None
        self.config: Optional[Config] = None
        self.is_running = False
    
    async def initialize(self) -> bool:
        """Initialize the agent and configuration"""
        try:
            # Load configuration
            self.config = Config()
            logger.info("Configuration loaded successfully")
            
            # Initialize agent
            self.agent = EmailAutomationAgent(self.config)
            
            # Initialize agent components
            success = await self.agent.initialize()
            if not success:
                logger.error("Failed to initialize email agent")
                return False
            
            logger.info("Email automation agent initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize: {str(e)}")
            return False
    
    async def run_once(self):
        """Run email processing once"""
        if not self.agent:
            logger.error("Agent not initialized")
            return
        
        try:
            logger.info("Running email processing cycle...")
            await self.agent.run_email_check_cycle()
            logger.info("Email processing cycle completed")
            
        except Exception as e:
            logger.error(f"Error in email processing: {str(e)}")
        finally:
            await self.agent.cleanup()
    
    async def run_continuous(self, stop_event: asyncio.Event):
        """Run continuous email monitoring with graceful shutdown"""
        if not self.agent:
            logger.error("Agent not initialized")
            return
        
        logger.info("Starting continuous monitoring...")
        monitor_task = asyncio.create_task(self.agent.start_monitoring())

        try:
            await stop_event.wait()  # Wait for signal
            logger.info("Stop signal received. Shutting down monitoring...")
        finally:
            self.agent.stop_monitoring()
            await monitor_task
            await self.agent.cleanup()
            logger.info("Shutdown complete.")

    
    async def run_with_task(self, task_description: str):
        """Run agent with a specific task using LangChain orchestration"""
        if not self.agent:
            logger.error("Agent not initialized")
            return
        
        try:
            logger.info(f"Running task: {task_description}")
            result = await self.agent.run_with_langchain_orchestration(task_description)
            logger.info(f"Task result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error running task: {str(e)}")
            return f"Error: {str(e)}"
        finally:
            await self.agent.cleanup()
    
    async def stop(self):
        """Stop the agent"""
        self.is_running = False
        if self.agent:
            self.agent.stop_monitoring()
            await self.agent.cleanup()
        logger.info("Email agent stopped")
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}")
            if self.is_running:
                asyncio.create_task(self.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

async def main():
    """Main function"""
    runner = EmailAgentRunner()
    stop_event = asyncio.Event()
    def handle_signal(signum, frame):
        logger.info(f"Received shutdown signal ({signum})")
        stop_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    else:
        mode = "once"  # Default mode
    
    # Initialize
    if not await runner.initialize():
        logger.error("Failed to initialize agent")
        sys.exit(1)
    
    # Run based on mode
    try:
        if mode == "continuous":
            logger.info("Running in continuous monitoring mode")
            await runner.run_continuous(stop_event)
            
        elif mode == "once":
            logger.info("Running single email processing cycle")
            await runner.run_once()
            
        elif mode.startswith("task:"):
            task_description = mode[5:]  # Remove "task:" prefix
            logger.info(f"Running with custom task: {task_description}")
            await runner.run_with_task(task_description)
            
        else:
            logger.error(f"Unknown mode: {mode}")
            print_usage()
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        sys.exit(1)

def print_usage():
    """Print usage information"""
    print("""
Usage: python main.py [mode]

Modes:
    once        - Run email processing once and exit (default)
    continuous  - Run continuous email monitoring
    task:TEXT   - Run with custom LangChain task description

Examples:
    python main.py once
    python main.py continuous
    python main.py "task:Check emails and reply to urgent ones only"

Environment Variables Required:
    OPENAI_API_KEY     - OpenAI API key for AI responses
    EMAIL_USERNAME     - Email account username
    EMAIL_PASSWORD     - Email account password
    EMAIL_PLATFORM_URL - Email platform URL (optional, defaults to Outlook)
    """)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)
    finally:
        import time
        time.sleep(0.1)