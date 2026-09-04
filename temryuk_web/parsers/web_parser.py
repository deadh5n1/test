"""
Web site parser using HTTP requests and BeautifulSoup.
"""
import aiohttp
from bs4 import BeautifulSoup
from typing import List
from datetime import datetime

from parsers.base import BaseParser, NewsItem


class WebParser(BaseParser):
    """Parser for regular web sites."""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
    
    async def parse(self, url: str) -> List[NewsItem]:
        """Parse news from a web site."""
        news_items = []
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=self.timeout) as response:
                    if response.status != 200:
                        return []
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Extract news items (customize selectors based on target site)
                    # This is a generic implementation - adjust for specific sites
                    articles = soup.find_all('article', limit=20)
                    
                    for article in articles:
                        title_elem = article.find(['h1', 'h2', 'h3'], class_=lambda x: x and ('title' in x.lower() or 'headline' in x.lower()))
                        if not title_elem:
                            title_elem = article.find(['h1', 'h2', 'h3'])
                        
                        if not title_elem:
                            continue
                        
                        title = title_elem.get_text(strip=True)
                        
                        # Get content
                        content_elem = article.find('p', class_=lambda x: x and ('summary' in x.lower() or 'excerpt' in x.lower()))
                        if not content_elem:
                            content_elem = article.find('p')
                        
                        content = content_elem.get_text(strip=True) if content_elem else ""
                        
                        # Get URL
                        link_elem = article.find('a', href=True)
                        news_url = link_elem['href'] if link_elem else url
                        
                        if not news_url.startswith('http'):
                            # Make absolute URL
                            from urllib.parse import urljoin
                            news_url = urljoin(url, news_url)
                        
                        news_items.append(NewsItem(
                            title=title,
                            content=content,
                            url=news_url,
                            published_at=datetime.utcnow()
                        ))
        
        except Exception as e:
            print(f"Error parsing {url}: {e}")
        
        return news_items
