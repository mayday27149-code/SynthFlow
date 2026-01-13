import os
import shutil
from typing import Optional, Dict, Any
from playwright.sync_api import sync_playwright, BrowserContext, Page, Playwright

class BrowserContextManager:
    """
    Manages a persistent browser context (singleton).
    Ensures that browser state (cookies, local storage) is preserved across executions
    if the process stays alive, or persisted to disk for future runs.
    """
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(BrowserContextManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, 
                 user_data_dir: str = None, 
                 headless: bool = False,
                 args: list = None):
        """
        Initialize the browser manager.
        
        Args:
            user_data_dir: Path to store user data (cookies, etc.). Defaults to ./browser_data
            headless: Whether to run in headless mode. Defaults to False (visible).
            args: Additional command line arguments for the browser.
        """
        if hasattr(self, 'playwright'):
            # Already initialized
            return
            
        self.playwright: Optional[Playwright] = None
        self.context: Optional[BrowserContext] = None
        self.user_data_dir = user_data_dir or os.path.join(os.getcwd(), "browser_data")
        self.headless = headless
        
        # Default args to mimic a real user and avoid some bot detection
        self.browser_args = args or [
            "--start-maximized",
            "--no-sandbox",
            "--disable-infobars",
            "--disable-blink-features=AutomationControlled" # Helps with some basic bot detection
        ]

    def start(self):
        """Starts the persistent browser context if not already running."""
        if self.context:
            return

        self.playwright = sync_playwright().start()
        
        # Create directory if it doesn't exist
        if not os.path.exists(self.user_data_dir):
            os.makedirs(self.user_data_dir)

        print(f"[BrowserContextManager] Launching browser with user data dir: {self.user_data_dir}")
        
        try:
            self.context = self.playwright.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=self.headless,
                args=self.browser_args,
                viewport=None, # Disable viewport emulation to allow maximizing
                # user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" # Optional: set a fixed UA
            )
            
            # Anti-detection scripts
            # This is a basic measure; for advanced stealth, use playwright-stealth
            self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
        except Exception as e:
            # Handle User Data Dir locking issue
            if "SingletonLock" in str(e) or "user data directory is already in use" in str(e):
                print(f"[BrowserContextManager] WARNING: Browser already running in {self.user_data_dir}. Attempting to connect or ignoring...")
                # NOTE: We cannot easily 'connect' to a persistent context unless we launched it with CDP port.
                # For now, we just fail gracefully or ask user to close.
                raise RuntimeError(f"Browser is already running! Please close all Chrome instances using {self.user_data_dir} or restart the tool.") from e
            
            print(f"[BrowserContextManager] Failed to launch browser: {e}")
            self.stop()
            raise e

    def get_page(self) -> Page:
        """Returns the current active page or creates a new one."""
        if not self.context:
            self.start()
            
        if not self.context.pages:
            return self.context.new_page()
            
        # Return the last active page (usually the visible one)
        return self.context.pages[-1]

    def open_url(self, url: str) -> Page:
        """Navigates to a URL using the active page."""
        page = self.get_page()
        page.goto(url)
        return page

    def stop(self):
        """Closes the browser and stops Playwright."""
        if self.context:
            self.context.close()
            self.context = None
            
        if self.playwright:
            self.playwright.stop()
            self.playwright = None

    def __del__(self):
        """Destructor to ensure cleanup."""
        self.stop()
