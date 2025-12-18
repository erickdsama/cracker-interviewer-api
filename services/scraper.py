import requests
from bs4 import BeautifulSoup
# from playwright.sync_api import sync_playwright # Uncomment when ready to use Playwright
from ..core.logger import get_logger

logger = get_logger(__name__)

class ScraperService:
    def scrape_url(self, url: str) -> str:
        # Basic static scraping for now
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
                
            text = soup.get_text()
            
            # Break into lines and remove leading/trailing space on each
            lines = (line.strip() for line in text.splitlines())
            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            # Drop blank lines
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return ""

    def search_company(self, company_name: str) -> str:
        """
        Searches for the company and returns a summary of its about/careers page.
        """
        try:
            from duckduckgo_search import DDGS
            
            with DDGS() as ddgs:
                # Search for company careers or about page
                results = list(ddgs.text(f"{company_name} careers about interview process", max_results=3))
                
                if not results:
                    return f"No information found for {company_name}."
                
                # For now, just return the snippets from the search results
                # In a full implementation, we would visit the URLs and scrape them
                summary = f"Information about {company_name}:\n"
                for res in results:
                    summary += f"- {res['title']}: {res['body']}\n"
                    
                return summary
        except Exception as e:
            logger.error(f"Error searching company {company_name}: {e}")
            return f"Could not retrieve information for {company_name}."

    def scrape_reddit(self, query: str) -> str:
        """
        Searches Reddit for the query and returns a summary of discussions.
        """
        try:
            from duckduckgo_search import DDGS
            
            with DDGS() as ddgs:
                # Search specifically on reddit.com
                results = list(ddgs.text(f"site:reddit.com {query}", max_results=5))
                
                if not results:
                    return f"No Reddit discussions found for {query}."
                
                summary = f"Reddit discussions about {query}:\n"
                for res in results:
                    summary += f"- {res['title']}: {res['body']}\n"
                    
                return summary
        except Exception as e:
            logger.error(f"Error scraping Reddit for {query}: {e}")
            return f"Could not retrieve Reddit information for {query}."

scraper_service = ScraperService()
