"""
Browser automation core functionality for email platforms.
"""
import sys
import asyncio
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from dataclasses import dataclass
import logging

from config import BrowserConfig, EmailConfig
from human_behavior import HumanBehaviorSimulator
from ai_service import EmailContext

logger = logging.getLogger(__name__)

@dataclass
class EmailMessage:
    """Represents an email message"""
    id: str
    sender_name:str
    sender_email: str
    subject: str
    body: str
    timestamp: str
    is_unread: bool = True
    is_reply: bool = False

class BrowserAutomation:
    """Core browser automation functionality"""
    
    def __init__(self, browser_config: BrowserConfig, email_config: EmailConfig, human_simulator: HumanBehaviorSimulator):
        self.browser_config = browser_config
        self.email_config = email_config
        self.human_simulator = human_simulator
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.is_logged_in = False
        self._playwright = None
    
    async def initialize_browser(self):
        """Initialize browser and context"""
        self._playwright = await async_playwright().start()
        
        self.browser = await self._playwright.chromium.launch(
            headless=self.browser_config.headless,
            args=['--no-sandbox', '--disable-dev-shm-usage'],
            channel="chrome"
        )
        
        self.context = await self.browser.new_context(
            viewport={'width': self.browser_config.viewport_width, 'height': self.browser_config.viewport_height},
            user_agent=self.browser_config.user_agent,
            device_scale_factor=1,
            is_mobile=False,
            has_touch=False,
            accept_downloads=True,
            permissions=["notifications"]
        )
        
        self.page = await self.context.new_page()
        self.page.set_default_timeout(self.browser_config.timeout)
        
        logger.info("Browser initialized successfully")
    
    async def login(self) -> bool:
        """Login to the email platform"""
        if not self.page:
            await self.initialize_browser()
        
        try:
            # Navigate to login page
            logger.info(f"Navigating to login page: {self.email_config.platform_url}")
            await self.page.goto("https://login.live.com/")
            await self.human_simulator.page_load_delay()
            
            # Generic selectors - these would need to be adapted for specific platforms
            username_selectors = [
                '#usernameEntry',  
                'input[type="email"]',
                'input[name="username"]',
                'input[name="email"]',
                '#username',
                '#email'
            ]
            
            password_selectors = [
                '#passwordEntry',              # <-- Newly added
                'input[name="passwd"]',  
                'input[type="password"]',
                'input[name="password"]',
                '#password'
            ]
            
            login_button_selectors = [
                'button[data-testid="primaryButton"]',
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Sign in")',
                'button:has-text("Login")',
                '#loginButton'
            ]
        

            # Find and fill username
            username_field = None
            for selector in username_selectors:
                try:
                    logger.info(f"Trying username selector: {selector}")
                    username_field = self.page.locator(selector).first
                    if await username_field.is_visible(timeout=5000):
                        break
                except:
                    continue
            
            if not username_field:
                raise Exception("Could not find username field")
            
            await self.human_simulator.human_type(username_field, self.email_config.username)

                        
            next_button = None
            for selector in login_button_selectors:
                try:
                    next_button = self.page.locator(selector).first
                    if await next_button.is_visible(timeout=5000):
                        break
                except:
                    continue

            if not next_button:
                raise Exception("Could not find Next button")

            await self.human_simulator.human_click(next_button)

            # Wait for page transition
            await self.human_simulator.page_load_delay()
            

            # Find and fill password
            password_field = None
            for selector in password_selectors:
                try:
                    logger.info(f"Trying password selector: {selector}")
                    password_field = self.page.locator(selector).first
                    if await password_field.is_visible(timeout=5000):
                        break
                except:
                    continue
            
            if not password_field:
                raise Exception("Could not find password field")
            
            await self.human_simulator.human_type(password_field, self.email_config.password)
            
                        # Find and click login button
            next_button = None
            for selector in login_button_selectors:
                try:
                    next_button = self.page.locator(selector).first
                    if await next_button.is_visible(timeout=5000):
                        break
                except:
                    continue

            if not next_button:
                raise Exception("Could not find Next button")

            await self.human_simulator.human_click(next_button)

            # Wait for page transition
            await self.human_simulator.page_load_delay()

            # Stay-signed in 
            # Give the dialog a little more time to appear
          # wait 2 seconds just in case

            selectors_to_try = [
                    'button[data-testid="secondaryButton"]',
                    'button:has-text("No")',
                    'button[type="submit"]:has-text("No")'
                ]

            for selector in selectors_to_try:
                try:
                    no_button = self.page.locator(selector).first
                    if await no_button.is_visible(timeout=5000):
                        logger.info(f"Clicked 'No' button using selector: {selector}")
                        break
                except:
                    continue

            await self.human_simulator.human_click(no_button)
            await self.human_simulator.page_load_delay()

            selectors_to_main_page = [
            'a[aria-label="Open Outlook.com "]' ,
            'a:has-text("Open Outlook.com")',
            'a[href*="outlook.com"]'            
            ]

            login_button = None
            for selector in selectors_to_main_page:
                try:
                    logger.info(f"Trying selector: {selector}")
                    await self.page.wait_for_selector(selector, timeout=10000)
                    login_button = self.page.locator(selector).first
                    break
                except Exception as e:
                    logger.warning(f"Selector failed: {selector} with error {e}")

            if not login_button:
                raise Exception("Login button not visible")

            async with self.page.context.expect_page() as new_page_info:
                await self.human_simulator.human_click(login_button)

            # Switch to the new tab
            new_page = await new_page_info.value
            await new_page.wait_for_load_state("load")
            self.page = new_page  # Update the current page reference
            await self.human_simulator.page_load_delay()


            logger.info("Waiting for inbox UI to render...")
            try:
                await self.page.wait_for_selector('button[aria-label="Mail"]', timeout=15000)
            except:
                logger.warning("Inbox UI not detected within wait period.")
        # Optional step: Handle "Stay signed in?" prompt
            # Optional step: Handle "Stay signed in?" prompt if it appears
            logger.info(f"\npage : {self.page}\n")
            # Check if login was successful by looking for inbox indicators
            inbox_indicators = [
            '#ddea774c-382b-47d7-aab5-adc2139a802b',
            'button[aria-label="Mail"]',                      # Exact aria-label match
            'button:has([alt="Mail"])',                # If targeting the image inside
            'button:has(img[alt="Mail"])',             # Direct image inside button
            'button:has-text("Mail")',                 # If there’s visible text (unlikely here)
            'button[role="button"][aria-label="Mail"]' # More specific variant
            ]

            mail_button = None
            for indicator in inbox_indicators:
                try:
                    mail_button =  self.page.locator(indicator).first
                    if await mail_button.is_visible(timeout=5000):
                        logger.info(f"\n{indicator}\n")
                        self.is_logged_in = True
                        logger.info("Login successful")
                        return True
                except:
                    continue
            
            logger.warning("Login may have failed - inbox not detected")
            return False
            
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return False
    
    async def navigate_to_inbox(self) -> bool:
        """Navigate to inbox if not already there"""
        if not self.is_logged_in:
            await self.login()
        
        try:
            inbox_selectors = [
                '#ddea774c-382b-47d7-aab5-adc2139a802b',
                'button[aria-label="Mail"]',                      # Exact aria-label match
                'button:has([alt="Mail"])',                # If targeting the image inside
                'button:has(img[alt="Mail"])',             # Direct image inside button           
                'button[role="button"][aria-label="Mail"]'
                'text=Inbox',
                '[aria-label*="Inbox"]',
            ]
            
            for selector in inbox_selectors:
                try:
                    inbox_link = self.page.locator(selector).first
                    if await inbox_link.is_visible(timeout=5000):
                        await self.human_simulator.human_click(inbox_link)
                        await self.human_simulator.page_load_delay()
                        return True
                except:
                    continue
            
            logger.info("Already in inbox or navigation not needed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to navigate to inbox: {str(e)}")
            return False
    
    async def get_unread_emails(self) -> List[EmailMessage]:
        """Retrieve unread emails from inbox"""
        if not await self.navigate_to_inbox():
            return []
        
        try:
        # Wait for at least one unread email to appear
            unread_selector = 'div[aria-label^="Unread"]'
            await self.page.wait_for_selector(unread_selector, timeout=15000)

            unread_locator = self.page.locator(unread_selector)
            count = await unread_locator.count()
            logger.info(f"Found {count} unread email(s) in DOM")

            emails = []
            for i in range(count):
                element = unread_locator.nth(i)
                try:
                    aria_label = await element.get_attribute("aria-label")
                    logger.info(f"\nElement {i} : {element}\n")
                    logger.info(f"[{i}] Unread aria-label: {aria_label}")
                    email_data = await self._extract_email_data(element, i)
                    if email_data:
                        emails.append(email_data)
                except Exception as e:
                    logger.warning(f"Failed to process unread email {i}: {str(e)}")

            return emails

        except Exception as e:
            logger.error(f"Failed to get unread emails: {str(e)}")
            return []

    async def _extract_email_data(self, element, index: int) -> Optional[EmailMessage]:
        try:
        # Click the email to open it fully
            await self.human_simulator.human_click(element)
            await self.page.wait_for_timeout(3000)  # Small delay for content to load

            # Optionally wait for known content selector
            await self.page.wait_for_selector('div[role="heading"] span[title]', timeout=10000)

            # Now extract subject and sender 
            subject_locator = self.page.locator('div[role="heading"] span[title]')
            subject = await subject_locator.first.get_attribute("title") \
                    or await subject_locator.first.text_content() \
                    or f"Subject {index}"

            sender_span = self.page.locator('span[title]')
            sender_name = await sender_span.first.text_content() or f"Sender {index}"
            sender_email = await sender_span.first.get_attribute("title") or f"sender{index}@example.com"

            logger.info(f"Sender name: {sender_name}, email: {sender_email}, subject: {subject}")
            return EmailMessage(
                id=f"email_{index}_{sender_email}",
                sender_name=sender_name.strip(),
                sender_email=sender_email.strip(),
                subject=subject.strip(),
                body="",  # Optionally extract using open_email()
                timestamp="",
                is_unread=True
            )
        except Exception as e:
            logger.warning(f"Failed to extract email data: {str(e)}")
            return None
        
    async def open_email(self, email: EmailMessage) -> Optional[str]:
        """Open email and get full content"""
        try:
            # Find and click the email
            email_locator = self.page.locator(f'text="{email.subject}"').first
            await self.human_simulator.human_click(email_locator)
            await self.human_simulator.page_load_delay()
            
            # Extract email body content
            body_selectors = [
                    '.email-body',
                    '.message-body',
                    '[role="main"]',
                    '.content'
                ]
                
            for selector in body_selectors:
                    try:
                        body_element = self.page.locator(selector).first
                        if await body_element.is_visible(timeout=5000):
                            return await body_element.text_content()
                    except:
                        continue
                
            return None
        
        except Exception as e:
            logger.error(f"Failed to open email: {str(e)}")
            return None
    
    async def send_reply(self, original_email: EmailMessage, reply_content: str) -> bool:
        """Send reply to an email"""
        try:
            # Look for reply button
            reply_selectors = [
                'button:has-text("Reply")',
                '[aria-label*="Reply"]',
                '.reply-button',
                '#reply'
            ]
            
            for selector in reply_selectors:
                try:
                    reply_button = self.page.locator(selector).first
                    if await reply_button.is_visible(timeout=5000):
                        await self.human_simulator.human_click(reply_button)
                        break
                except:
                    continue
            
            await self.human_simulator.page_load_delay()
            
            # Find compose area
            compose_selectors = [
                '[role="textbox"]',
                '.compose-body',
                'textarea',
                '.editor'
            ]
            
            compose_area = None
            for selector in compose_selectors:
                try:
                    compose_area = self.page.locator(selector).first
                    if await compose_area.is_visible(timeout=5000):
                        break
                except:
                    continue
            
            if not compose_area:
                raise Exception("Could not find compose area")
            
            # Type reply content
            await self.human_simulator.human_type(compose_area, reply_content)
            
            # Find and click send button
            send_selectors = [
                'button:has-text("Send")',
                '[aria-label*="Send"]',
                '.send-button',
                '#send'
            ]
            
            for selector in send_selectors:
                try:
                    send_button = self.page.locator(selector).first
                    if await send_button.is_visible(timeout=5000):
                        await self.human_simulator.human_click(send_button)
                        await self.human_simulator.page_load_delay()
                        logger.info(f"Reply sent to {original_email.sender_email}")
                        return True
                except:
                    continue
            
            raise Exception("Could not find send button")
            
        except Exception as e:
            logger.error(f"Failed to send reply: {str(e)}")
            return False
    
    async def close_browser(self):
        """Clean up browser resources"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self._playwright:
                await self._playwright.stop()
            logger.info("Browser closed")
        except Exception as e:
            logger.error(f"There was a problem in closing the browser : {e}")