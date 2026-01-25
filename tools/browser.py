from playwright.sync_api import sync_playwright
from .base import BaseTool
import time
import os

class BrowserTool(BaseTool):
    name = "browse_website"
    description = "Visit a website and extract content. Args: {'url': 'https://example.com', 'action': 'extract_text'}"
    
    def execute(self, url, action="extract_text", selector=None):
        """Visit a website and perform actions"""
        try:
            print(f"[Browser] Visiting: {url}")
            
            with sync_playwright() as p:
                # Launch browser in headless mode (no GUI needed)
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Set realistic user agent
                page.set_extra_http_headers({
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
                })
                
                # Visit the page
                page.goto(url, wait_until="networkidle", timeout=30000)
                time.sleep(2)  # Let page fully load
                
                if action == "extract_text":
                    if selector:
                        # Extract specific element
                        element = page.query_selector(selector)
                        text = element.inner_text() if element else "Element not found"
                    else:
                        # Extract main content (remove nav, footer, etc.)
                        text = page.evaluate("""() => {
                            // Remove common non-content elements
                            ['nav', 'footer', 'header', 'aside', '.ad', '.advertisement'].forEach(sel => {
                                document.querySelectorAll(sel).forEach(el => el.remove());
                            });
                            return document.body.innerText;
                        }""")
                    
                    # Clean up text
                    cleaned_text = '\n'.join(line.strip() for line in text.split('\n') if line.strip())
                    # Limit length to avoid overwhelming the LLM
                    if len(cleaned_text) > 3000:
                        cleaned_text = cleaned_text[:3000] + "... (truncated)"
                    
                    result = {
                        "success": True,
                        "data": {
                            "url": url,
                            "text": cleaned_text,
                            "title": page.title()
                        }
                    }
                
                elif action == "screenshot":
                    # Take screenshot
                    screenshot_path = f"~/ai-agent/output/screenshot_{int(time.time())}.png"
                    screenshot_path = os.path.expanduser(screenshot_path)
                    page.screenshot(path=screenshot_path)
                    
                    result = {
                        "success": True,
                        "data": {
                            "url": url,
                            "screenshot": screenshot_path,
                            "title": page.title()
                        }
                    }
                
                else:
                    result = {
                        "success": False,
                        "error": f"Unknown action: {action}"
                    }
                
                browser.close()
                return result
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
