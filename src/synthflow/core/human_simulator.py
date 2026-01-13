import time
import random
from typing import Optional
from playwright.sync_api import Page, Locator

class HumanSimulator:
    """
    Simulates human-like interactions to avoid bot detection.
    Provides methods for natural mouse movement, clicking, and typing.
    """
    def __init__(self, page: Page):
        self.page = page

    def _random_sleep(self, min_s: float = 0.1, max_s: float = 0.5):
        time.sleep(random.uniform(min_s, max_s))

    def move_mouse_to(self, selector: str) -> bool:
        """
        Moves mouse to the target element with randomized trajectory logic (simplified).
        Returns True if successful, False if element not found/visible.
        """
        try:
            loc = self.page.locator(selector).first
            # Wait for element to be attached/visible for a short moment if needed
            # But here we assume caller handles waiting.
            if not loc.is_visible():
                return False
                
            box = loc.bounding_box()
            if not box:
                return False

            # Target point: Randomize within the element's bounding box
            # We avoid the absolute edges (keep within inner 80%)
            target_x = box['x'] + (box['width'] * random.uniform(0.1, 0.9))
            target_y = box['y'] + (box['height'] * random.uniform(0.1, 0.9))
            
            # Steps determines the speed/smoothness. 
            # 1 step is instant. 20-50 steps feels more natural.
            steps = random.randint(10, 30)
            
            self.page.mouse.move(target_x, target_y, steps=steps)
            return True
        except Exception as e:
            print(f"[HumanSimulator] Move failed: {e}")
            return False

    def click(self, selector: str):
        """
        Human-like click: Move to element -> Pause -> Mouse Down -> Pause -> Mouse Up.
        """
        if self.move_mouse_to(selector):
            self._random_sleep(0.1, 0.3) # Hesitation before click
            self.page.mouse.down()
            self._random_sleep(0.05, 0.15) # Click duration
            self.page.mouse.up()
        else:
            # Fallback to standard click if manual move fails
            # This ensures robustness if element is weirdly positioned
            self.page.click(selector)

    def type(self, selector: str, text: str, delay_range: tuple = (0.05, 0.2)):
        """
        Human-like typing: Click to focus -> Type char by char with variable delays.
        """
        # Ensure focus
        self.click(selector)
        
        # Clear field first? 
        # For now, we assume we just type. If clear is needed, it should be a separate action
        # or we can simulate Ctrl+A -> Backspace.
        
        for char in text:
            self.page.keyboard.type(char)
            # Random delay between keystrokes
            time.sleep(random.uniform(*delay_range))
            
            # Occasionally pause longer (simulating thinking or checking source)
            if random.random() < 0.05:
                self._random_sleep(0.3, 0.8)
