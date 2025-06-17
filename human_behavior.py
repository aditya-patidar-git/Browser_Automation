"""
Human-like behavior simulation for browser automation.
"""
import asyncio
import random
from typing import Optional
from playwright.async_api import Page, Locator
from config import ThrottlingConfig

class HumanBehaviorSimulator:
    """Simulates human-like behavior in browser automation"""
    
    def __init__(self, config: ThrottlingConfig):
        self.config = config
    
    async def random_delay(self, min_delay: Optional[float] = None, max_delay: Optional[float] = None):
        """Add random delay between actions"""
        min_d = min_delay or self.config.min_action_delay
        max_d = max_delay or self.config.max_action_delay
        delay = random.uniform(min_d, max_d)
        await asyncio.sleep(delay)
    
    async def human_type(self, element: Locator, text: str, clear_first: bool = True):
        """Type text with human-like delays"""
        if clear_first:
            await element.clear()
            await self.random_delay(0.5, 1.0)
        
        for char in text:
            await element.type(char)
            delay = random.uniform(self.config.min_typing_delay, self.config.max_typing_delay)
            await asyncio.sleep(delay)
    
    async def human_click(self, element: Locator):
        """Click with human-like delay"""
        await self.random_delay(0.5, 1.5)
        await element.click()
        await self.random_delay()
    
    async def scroll_randomly(self, page: Page):
        """Perform random scrolling to mimic human behavior"""
        viewport_size = page.viewport_size
        if not viewport_size:
            return
        
        # Random scroll amount
        scroll_amount = random.randint(100, 300)
        direction = random.choice([-1, 1])
        
        await page.mouse.wheel(0, scroll_amount * direction)
        await self.random_delay(1.0, 2.0)
    
    async def mouse_movement(self, page: Page):
        """Simulate natural mouse movements"""
        viewport_size = page.viewport_size
        if not viewport_size:
            return
        
        # Move to random position
        x = random.randint(100, viewport_size['width'] - 100)
        y = random.randint(100, viewport_size['height'] - 100)
        
        await page.mouse.move(x, y)
        await self.random_delay(0.5, 1.0)
    
    async def page_load_delay(self):
        """Wait for page load with human-like delay"""
        delay = random.uniform(
            self.config.min_page_load_delay, 
            self.config.max_page_load_delay
        )
        await asyncio.sleep(delay)