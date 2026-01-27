from tavily import TavilyClient
from .base import BaseTool
import os

class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Search the web for information. Args: {'query': 'your search query'}"
    
    def __init__(self):
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY not found in environment")
        self.client = TavilyClient(api_key=api_key)
    
    def execute(self, query):
        """Search the web and return results"""
        try:
            print(f"[WebSearch] Searching for: {query}")
            
            response = self.client.search(
                query=query,
                max_results=10
            )
            
            formatted_results = []
            for result in response.get('results', []):
                formatted_results.append({
                    "title": result.get('title', ''),
                    "url": result.get('url', ''),
                    "snippet": result.get('content', '')
                })
            
            return {
                "success": True,
                "data": formatted_results
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

