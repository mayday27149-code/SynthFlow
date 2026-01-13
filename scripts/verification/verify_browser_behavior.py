import sys
import os
import time

# Add src to path (adjusted for scripts/verification/ location)
# ../../src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from synthflow.core.browser_manager import BrowserContextManager
from synthflow.core.human_simulator import HumanSimulator

def verify_browser_behavior():
    print("--- Verifying BrowserContextManager & HumanSimulator ---")
    print(f"Working Directory: {os.getcwd()}")
    
    # 1. Test Singleton
    manager1 = BrowserContextManager(headless=False) # Visible mode
    manager2 = BrowserContextManager()
    
    if manager1 is manager2:
        print("[PASS] Singleton pattern verified.")
    else:
        print("[FAIL] Singleton pattern failed.")
        
    # 2. Test Browser Launch
    print("Launching browser...")
    try:
        manager1.start()
    except Exception as e:
        print(f"[FAIL] Failed to start browser: {e}")
        return
    
    page = manager1.get_page()
    simulator = HumanSimulator(page)
    
    # 3. Demo Human Interaction
    target_url = "https://www.bing.com"
    print(f"Navigating to {target_url}...")
    try:
        page.goto(target_url)
    except Exception as e:
         print(f"[FAIL] Navigation failed: {e}")
         manager1.stop()
         return
    
    # Wait for search box (Bing's search box usually has ID 'sb_form_q' or name 'q')
    search_box = "#sb_form_q" 
    
    try:
        print("Waiting for search box...")
        page.wait_for_selector(search_box, timeout=5000)
        
        print("Demonstrating human-like typing...")
        simulator.type(search_box, "SynthFlow Verify")
        
        print("Demonstrating human-like click...")
        # Just click the box again to show movement
        simulator.click(search_box)
        print("[PASS] Interaction executed without error.")
        
    except Exception as e:
        print(f"[WARN] Interaction demo skipped (element not found): {e}")
    
    # 4. Simulate persistence
    print("\n[INSTRUCTION] The browser should now be open.")
    print("Waiting for 5 seconds...")
    time.sleep(5)
        
    print("\nClosing browser...")
    manager1.stop()
    print("Verification completed.")

if __name__ == "__main__":
    verify_browser_behavior()
