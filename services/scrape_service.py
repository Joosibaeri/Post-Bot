import httpx
from bs4 import BeautifulSoup
import structlog

logger = structlog.get_logger(__name__)

async def scrape_url(url: str) -> str:
    """Scrape the main text content from a URL."""
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove scripts and styles
            for script in soup(["script", "style"]):
                script.decompose()
                
            text = soup.get_text(separator=' ', strip=True)
            # Limit the text length to avoid token explosion
            return text[:6000]
    except Exception as e:
        logger.error("scrape_url_failed", url=url, error=str(e))
        raise Exception(f"Failed to scrape URL: {str(e)}")
