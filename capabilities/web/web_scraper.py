"""
Web Scraper Service Module
==========================

Enhanced web search for NEXA AI - fetches actual content from the web
and returns readable text that NEXA can use to answer questions.

Unlike the basic search_web (which just opens Google in a browser),
this service ACTUALLY scrapes web pages and extracts text content.

All functions require ONLINE mode (internet connection).

Features:
- Smart web search with intelligent source routing
- Wikipedia API integration (free, no key) for factual queries
- Dedicated extractors for Wikipedia, IMDB, Stack Overflow
- DuckDuckGo search (no API key needed) + Google fallback
- Web page text extraction via BeautifulSoup
- Query intent detection for optimal source selection
- Content deduplication and noise filtering
- Source priority ranking (knowledge sites first)

Dependencies:
- requests: HTTP client (already in requirements)
- beautifulsoup4: HTML parsing (pip install beautifulsoup4)
- No API keys required - 100% free

Author: Nexa AI Team
Phase: 18 - YouTube Integration + Enhanced Web Search
"""

import logging
import re
import time
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import quote_plus, urlparse, unquote

logger = logging.getLogger(__name__)

# Optional imports
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("⚠️ requests not installed. Web scraping unavailable.")

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    logger.warning("⚠️ beautifulsoup4 not installed. Web scraping limited. Install: pip install beautifulsoup4")


class WebScraper:
    """
    Enhanced web search and content extraction for NEXA AI.
    
    Performs actual web searches, scrapes page content, and returns
    readable text that the LLM can use to answer user questions.
    
    Intelligent source routing:
    - Factual questions → Wikipedia API first, then DuckDuckGo
    - Movie/TV questions → IMDB prioritized in search results
    - Tech/coding questions → Stack Overflow prioritized
    - General queries → DuckDuckGo + top 3 page scrapes
    
    Uses DuckDuckGo for search (no API key needed) and BeautifulSoup
    for HTML parsing.
    """
    
    # Common user agent to avoid blocks
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    
    # Maximum content length to return (prevent overwhelming LLM context)
    MAX_CONTENT_LENGTH = 2500  # chars - balanced for Llama 3.1 4K context
    
    # Request timeout
    TIMEOUT = 10  # seconds
    
    # Tags to extract text from
    CONTENT_TAGS = ['p', 'h1', 'h2', 'h3', 'li', 'td', 'th', 'span', 'div', 'blockquote']
    
    # Tags to ignore completely
    IGNORE_TAGS = ['script', 'style', 'nav', 'footer', 'header', 'aside', 
                   'form', 'button', 'iframe', 'noscript', 'svg', 'meta',
                   'link', 'img', 'figure', 'figcaption']
    
    # Noise phrases to filter out of scraped content
    NOISE_PHRASES = [
        'cookie', 'accept cookies', 'privacy policy', 'terms of service',
        'sign up', 'sign in', 'log in', 'subscribe', 'newsletter',
        'advertisement', 'sponsored', 'click here', 'read more',
        'we use cookies', 'consent', 'gdpr', 'manage preferences',
    ]
    
    # High-value domains for source prioritization
    PRIORITY_DOMAINS = {
        'wikipedia.org': 100,
        'en.wikipedia.org': 100,
        'imdb.com': 90,
        'stackoverflow.com': 85,
        'britannica.com': 80,
        'bbc.com': 75,
        'reuters.com': 75,
        'nytimes.com': 70,
        'theguardian.com': 70,
        'github.com': 65,
        'docs.python.org': 65,
        'developer.mozilla.org': 65,
    }
    
    # Query intent keywords for routing
    MOVIE_KEYWORDS = [
        'movie', 'film', 'actor', 'actress', 'director', 'cast', 'rating',
        'imdb', 'box office', 'trailer', 'genre', 'plot', 'series', 'show',
        'tv show', 'season', 'episode', 'netflix', 'hollywood', 'bollywood',
    ]
    
    TECH_KEYWORDS = [
        'how to code', 'programming', 'python', 'javascript', 'error',
        'stack overflow', 'stackoverflow', 'bug', 'fix', 'tutorial',
        'api', 'library', 'framework', 'algorithm', 'function', 'class',
        'syntax', 'debug', 'exception', 'install', 'npm', 'pip',
    ]
    
    WIKI_KEYWORDS = [
        'who is', 'who was', 'what is', 'what are', 'when was', 'when did',
        'where is', 'where was', 'history of', 'definition of', 'meaning of',
        'capital of', 'population of', 'president of', 'born', 'died',
        'founded', 'invented', 'discovered', 'country', 'city', 'planet',
    ]
    
    def __init__(self, config=None):
        """
        Initialize web scraper.
        
        Args:
            config: NexaConfig instance (optional)
        """
        self.config = config
        self._session = None
        self._last_search_results: List[Dict[str, str]] = []
        
        logger.info(f"🌐 Web scraper initialized (requests: {REQUESTS_AVAILABLE}, bs4: {BS4_AVAILABLE})")
    
    def _get_session(self) -> 'requests.Session':
        """Get or create HTTP session with appropriate headers."""
        if self._session is None and REQUESTS_AVAILABLE:
            self._session = requests.Session()
            self._session.headers.update({
                'User-Agent': self.USER_AGENT,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
            })
        return self._session
    
    # ==================== QUERY INTENT DETECTION ====================
    
    def _detect_intent(self, query: str) -> str:
        """
        Detect the type of query to route to the best source.
        
        Args:
            query: User's search query
            
        Returns:
            Intent type: 'wiki', 'movie', 'tech', or 'general'
        """
        q_lower = query.lower()
        
        # Check movie/entertainment intent
        if any(kw in q_lower for kw in self.MOVIE_KEYWORDS):
            return 'movie'
        
        # Check tech/coding intent
        if any(kw in q_lower for kw in self.TECH_KEYWORDS):
            return 'tech'
        
        # Check factual/wiki intent
        if any(kw in q_lower for kw in self.WIKI_KEYWORDS):
            return 'wiki'
        
        return 'general'
    
    # ==================== MAIN SEARCH METHOD ====================
    
    def smart_search(self, query: str) -> str:
        """
        Perform an intelligent web search: detects query intent, routes to
        the best source (Wikipedia/IMDB/StackOverflow/general), scrapes
        results, and returns clean extracted content.
        
        This is the primary function for answering knowledge questions.
        
        Args:
            query: User's question or search query
            
        Returns:
            Extracted web content as readable text, or error message
        """
        try:
            if not REQUESTS_AVAILABLE:
                return "Web search requires the 'requests' library. Install: pip install requests"
            
            if not BS4_AVAILABLE:
                return "Web search requires 'beautifulsoup4'. Install: pip install beautifulsoup4"
            
            logger.info(f"🔍 Smart search: '{query}'")
            
            # Step 1: Detect query intent for smart routing
            intent = self._detect_intent(query)
            logger.info(f"🎯 Query intent: {intent}")
            
            # Step 2: Try direct source first based on intent
            direct_result = None
            
            if intent == 'wiki' or intent == 'general':
                # Try Wikipedia API first — fastest + most reliable for factual queries
                direct_result = self._query_wikipedia_api(query)
                if direct_result:
                    logger.info(f"📚 Wikipedia API answered directly ({len(direct_result)} chars)")
            
            # Step 3: Search DuckDuckGo for broader results
            search_results = self._search_duckduckgo(query)
            
            if not search_results:
                # Fallback: try Google scraping
                search_results = self._search_google_scrape(query)
            
            # Step 4: Prioritize search results by domain quality
            if search_results:
                search_results = self._prioritize_results(search_results, intent)
            
            self._last_search_results = search_results
            
            # Step 5: If we have a Wikipedia direct answer but no search results, return it
            if direct_result and not search_results:
                return f"WEB_SEARCH_RESULT for '{query}':\n{direct_result}\n\n[Source: Wikipedia]"
            
            if not search_results and not direct_result:
                return f"I couldn't find any web results for '{query}'. Try rephrasing your question."
            
            # Step 6: Scrape content from top results using specialized extractors
            combined_content = []
            sources = []
            content_budget = self.MAX_CONTENT_LENGTH
            
            # If we have a Wikipedia direct answer, add it first (highest priority)
            if direct_result:
                trimmed = direct_result[:900]
                combined_content.append(f"[Wikipedia]\n{trimmed}")
                sources.append("Wikipedia (en.wikipedia.org)")
                content_budget -= len(trimmed) + 50
            
            for i, result in enumerate(search_results[:4]):  # Top 4 results
                url = result.get('url', '')
                title = result.get('title', '')
                snippet = result.get('snippet', '')
                
                if not url:
                    continue
                
                # Skip Wikipedia pages if we already have API content
                if direct_result and 'wikipedia.org' in url:
                    continue
                
                # Calculate per-source budget
                remaining_slots = max(1, 3 - len(combined_content))
                per_source = min(800, content_budget // remaining_slots)
                
                if per_source < 100:
                    break  # Not enough budget left
                
                # Use specialized extractor based on domain
                domain = urlparse(url).netloc.lower()
                page_content = None
                
                if 'wikipedia.org' in domain:
                    page_content = self._extract_wikipedia(url)
                elif 'imdb.com' in domain:
                    page_content = self._extract_imdb(url)
                elif 'stackoverflow.com' in domain:
                    page_content = self._extract_stackoverflow(url)
                else:
                    page_content = self._scrape_page(url)
                
                if page_content:
                    trimmed = page_content[:per_source]
                    combined_content.append(f"[Source: {title}]\n{trimmed}")
                    sources.append(f"{title} ({domain})")
                    content_budget -= len(trimmed) + 50
                elif snippet:
                    combined_content.append(f"[Source: {title}]\n{snippet}")
                    sources.append(f"{title} ({domain})")
                    content_budget -= len(snippet) + 50
            
            if not combined_content:
                # Return just the snippets from search results
                lines = []
                for r in search_results[:5]:
                    if r.get('snippet'):
                        lines.append(f"• {r['snippet']}")
                return f"Web results for '{query}':\n" + "\n".join(lines) if lines else f"Found results but couldn't extract content for '{query}'."
            
            # Step 7: Format, deduplicate, and return
            full_content = "\n\n".join(combined_content)
            full_content = self._deduplicate_content(full_content)
            
            # Trim to max length
            if len(full_content) > self.MAX_CONTENT_LENGTH:
                full_content = full_content[:self.MAX_CONTENT_LENGTH] + "..."
            
            # Add source attribution
            source_list = ", ".join(sources[:4])
            result_text = f"WEB_SEARCH_RESULT for '{query}':\n{full_content}\n\n[Sources: {source_list}]"
            
            logger.info(f"✅ Smart search returned {len(full_content)} chars from {len(sources)} sources (intent: {intent})")
            return result_text
            
        except Exception as e:
            logger.error(f"Smart search error: {e}")
            return f"Web search encountered an error: {str(e)}"
    
    def scrape_url(self, url: str) -> str:
        """
        Scrape and extract readable text from a specific URL.
        Uses specialized extractors for known sites.
        
        Args:
            url: Full URL to scrape
            
        Returns:
            Extracted text content
        """
        try:
            if not REQUESTS_AVAILABLE or not BS4_AVAILABLE:
                return "Web scraping requires 'requests' and 'beautifulsoup4' libraries."
            
            domain = urlparse(url).netloc.lower()
            content = None
            
            # Use specialized extractor if available
            if 'wikipedia.org' in domain:
                content = self._extract_wikipedia(url)
            elif 'imdb.com' in domain:
                content = self._extract_imdb(url)
            elif 'stackoverflow.com' in domain:
                content = self._extract_stackoverflow(url)
            else:
                content = self._scrape_page(url)
            
            if content:
                if len(content) > self.MAX_CONTENT_LENGTH:
                    content = content[:self.MAX_CONTENT_LENGTH] + "..."
                return f"Content from {domain}:\n{content}"
            else:
                return f"Couldn't extract readable content from {url}"
                
        except Exception as e:
            logger.error(f"Error scraping URL: {e}")
            return f"Error scraping page: {str(e)}"
    
    # ==================== WIKIPEDIA API (Direct, No Scraping) ====================
    
    def _query_wikipedia_api(self, query: str) -> Optional[str]:
        """
        Query Wikipedia's free REST API for a summary.
        No API key needed. Returns clean text directly.
        
        This is faster and more reliable than scraping Wikipedia pages.
        
        Args:
            query: Search query
            
        Returns:
            Wikipedia summary text or None
        """
        try:
            session = self._get_session()
            
            # Step 1: Search Wikipedia for the best matching article
            search_url = "https://en.wikipedia.org/w/api.php"
            search_params = {
                'action': 'query',
                'list': 'search',
                'srsearch': query,
                'srlimit': 1,
                'format': 'json',
                'utf8': 1,
            }
            
            resp = session.get(search_url, params=search_params, timeout=self.TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            
            results = data.get('query', {}).get('search', [])
            if not results:
                return None
            
            # Step 2: Get the summary of the top result
            page_title = results[0]['title']
            
            # Use Wikipedia REST API for clean summary
            summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote_plus(page_title)}"
            resp = session.get(summary_url, timeout=self.TIMEOUT, headers={
                'User-Agent': 'NexaAI/1.0 (Desktop Assistant; contact@nexa.ai)',
                'Accept': 'application/json',
            })
            resp.raise_for_status()
            summary_data = resp.json()
            
            extract = summary_data.get('extract', '')
            description = summary_data.get('description', '')
            
            if not extract:
                return None
            
            # Format nicely
            result_parts = []
            if description:
                result_parts.append(f"({description})")
            result_parts.append(extract)
            
            wiki_text = f"📚 Wikipedia — {page_title}\n" + "\n".join(result_parts)
            
            logger.info(f"📚 Wikipedia API: '{page_title}' ({len(extract)} chars)")
            return wiki_text
            
        except Exception as e:
            logger.debug(f"Wikipedia API failed: {e}")
            return None
    
    # ==================== SPECIALIZED EXTRACTORS ====================
    
    def _extract_wikipedia(self, url: str) -> Optional[str]:
        """
        Extract content from a Wikipedia page with structured data.
        Optimized for Wikipedia's specific HTML structure.
        
        Args:
            url: Wikipedia URL
            
        Returns:
            Formatted Wikipedia content or None
        """
        try:
            session = self._get_session()
            response = session.get(url, timeout=self.TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Get article title
            title_elem = soup.find('h1', id='firstHeading')
            title = title_elem.get_text(strip=True) if title_elem else 'Unknown'
            
            result_parts = [f"📚 Wikipedia — {title}"]
            
            # Extract infobox data (key structured info)
            infobox = soup.find('table', class_=re.compile(r'infobox|vcard', re.I))
            if infobox:
                info_items = []
                for row in infobox.find_all('tr'):
                    header = row.find('th')
                    data = row.find('td')
                    if header and data:
                        key = header.get_text(strip=True)
                        val = data.get_text(strip=True)
                        # Skip very long or noisy values
                        if val and len(val) < 150 and len(key) < 50:
                            info_items.append(f"  • {key}: {val}")
                
                if info_items:
                    result_parts.append("Key Facts:")
                    result_parts.extend(info_items[:10])  # Top 10 infobox items
            
            # Extract main article paragraphs
            content_div = soup.find('div', id='mw-content-text')
            if content_div:
                paragraphs = []
                for p in content_div.find_all('p', recursive=True):
                    text = p.get_text(strip=True)
                    # Skip citation-heavy or very short paragraphs
                    if text and len(text) > 50:
                        # Remove citation brackets [1] [2] etc
                        text = re.sub(r'\[\d+\]', '', text).strip()
                        if text:
                            paragraphs.append(text)
                
                if paragraphs:
                    result_parts.append("\n" + "\n".join(paragraphs[:4]))  # First 4 paragraphs
            
            result = "\n".join(result_parts)
            logger.info(f"📚 Wikipedia extracted: '{title}' ({len(result)} chars)")
            return result if len(result) > 100 else None
            
        except Exception as e:
            logger.warning(f"Wikipedia extractor failed for {url}: {e}")
            return None
    
    def _extract_imdb(self, url: str) -> Optional[str]:
        """
        Extract content from an IMDB page (movies, TV shows, actors).
        Optimized for IMDB's specific HTML structure.
        
        Args:
            url: IMDB URL
            
        Returns:
            Formatted IMDB content or None
        """
        try:
            session = self._get_session()
            # IMDB sometimes blocks, so use a more realistic header
            headers = {
                'User-Agent': self.USER_AGENT,
                'Accept-Language': 'en-US,en;q=0.9',
            }
            response = session.get(url, timeout=self.TIMEOUT, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            result_parts = ["🎬 IMDB"]
            
            # Get title
            title_elem = soup.find('h1')
            if title_elem:
                result_parts[0] = f"🎬 IMDB — {title_elem.get_text(strip=True)}"
            
            # Get rating
            rating_elem = soup.find('span', class_=re.compile(r'rating', re.I))
            if not rating_elem:
                rating_elem = soup.find('div', {'data-testid': re.compile(r'rating', re.I)})
            if rating_elem:
                rating_text = rating_elem.get_text(strip=True)
                if rating_text and any(c.isdigit() for c in rating_text):
                    result_parts.append(f"⭐ Rating: {rating_text}")
            
            # Get metadata (year, genre, runtime) from the hero metadata section
            meta_items = []
            for meta in soup.find_all('li', class_=re.compile(r'ipc-inline-list', re.I)):
                text = meta.get_text(strip=True)
                if text and len(text) < 100:
                    meta_items.append(text)
            if meta_items:
                result_parts.append(f"Info: {' | '.join(meta_items[:5])}")
            
            # Get plot/description
            plot_elem = soup.find('span', {'data-testid': 'plot-xl'})
            if not plot_elem:
                plot_elem = soup.find('span', {'data-testid': re.compile(r'plot', re.I)})
            if not plot_elem:
                # Fallback: find any plot/storyline section
                plot_elem = soup.find('p', class_=re.compile(r'plot|storyline|summary', re.I))
            if plot_elem:
                plot_text = plot_elem.get_text(strip=True)
                if plot_text:
                    result_parts.append(f"Plot: {plot_text}")
            
            # Get cast list
            cast_items = []
            cast_section = soup.find('div', {'data-testid': 'title-cast'})
            if cast_section:
                for actor in cast_section.find_all('a', {'data-testid': re.compile(r'cast', re.I)})[:8]:
                    name = actor.get_text(strip=True)
                    if name and len(name) > 2:
                        cast_items.append(name)
            if not cast_items:
                # Fallback: look for cast links
                for a in soup.find_all('a', href=re.compile(r'/name/nm\d+'))[:8]:
                    name = a.get_text(strip=True)
                    if name and len(name) > 2:
                        cast_items.append(name)
            if cast_items:
                # Deduplicate while preserving order
                seen = set()
                unique_cast = []
                for name in cast_items:
                    if name not in seen:
                        seen.add(name)
                        unique_cast.append(name)
                result_parts.append(f"Cast: {', '.join(unique_cast[:6])}")
            
            # Get director/creator
            for label in ['Director', 'Directors', 'Creator', 'Creators']:
                dir_elem = soup.find('li', {'data-testid': re.compile(f'title-pc.*{label.lower()}', re.I)})
                if dir_elem:
                    director_text = dir_elem.get_text(strip=True).replace(label, '').strip()
                    if director_text:
                        result_parts.append(f"{label}: {director_text}")
                    break
            
            result = "\n".join(result_parts)
            logger.info(f"🎬 IMDB extracted ({len(result)} chars)")
            return result if len(result) > 50 else None
            
        except Exception as e:
            logger.warning(f"IMDB extractor failed for {url}: {e}")
            return None
    
    def _extract_stackoverflow(self, url: str) -> Optional[str]:
        """
        Extract content from a Stack Overflow question page.
        Gets the question + accepted/top-voted answer.
        
        Args:
            url: Stack Overflow URL
            
        Returns:
            Formatted Q&A content or None
        """
        try:
            session = self._get_session()
            response = session.get(url, timeout=self.TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            result_parts = ["💻 Stack Overflow"]
            
            # Get question title
            title_elem = soup.find('h1', class_=re.compile(r'question-hyperlink|fs-headline', re.I))
            if not title_elem:
                title_elem = soup.find('a', class_='question-hyperlink')
            if not title_elem:
                title_elem = soup.find('h1')
            if title_elem:
                result_parts[0] = f"💻 Stack Overflow — {title_elem.get_text(strip=True)}"
            
            # Get question body (first part)
            question_div = soup.find('div', class_='s-prose', id=re.compile(r'question'))
            if not question_div:
                question_div = soup.find('div', {'id': 'question'})
                if question_div:
                    question_div = question_div.find('div', class_=re.compile(r'post-text|s-prose'))
            
            if question_div:
                q_text = question_div.get_text(strip=True)
                if q_text:
                    result_parts.append(f"Question:\n{q_text[:400]}")
            
            # Get accepted answer (or top-voted answer)
            accepted = soup.find('div', class_=re.compile(r'accepted-answer'))
            if not accepted:
                # Get first answer
                accepted = soup.find('div', class_=re.compile(r'answer'))
            
            if accepted:
                answer_body = accepted.find('div', class_=re.compile(r's-prose|post-text'))
                if answer_body:
                    # Get text content, preserve code blocks
                    answer_parts = []
                    for child in answer_body.children:
                        if hasattr(child, 'name'):
                            if child.name == 'pre' or child.name == 'code':
                                code_text = child.get_text(strip=True)
                                if code_text:
                                    answer_parts.append(f"```\n{code_text[:300]}\n```")
                            else:
                                text = child.get_text(strip=True)
                                if text and len(text) > 10:
                                    answer_parts.append(text)
                    
                    if answer_parts:
                        is_accepted = 'accepted' in (accepted.get('class', []) if isinstance(accepted.get('class'), list) else str(accepted.get('class', '')))
                        label = "✅ Accepted Answer" if is_accepted else "Top Answer"
                        result_parts.append(f"\n{label}:\n" + "\n".join(answer_parts[:6]))
                
                # Get vote count
                vote_elem = accepted.find('div', class_=re.compile(r'vote-count|js-vote-count'))
                if vote_elem:
                    votes = vote_elem.get_text(strip=True)
                    if votes:
                        result_parts.append(f"Votes: {votes}")
            
            result = "\n".join(result_parts)
            logger.info(f"💻 Stack Overflow extracted ({len(result)} chars)")
            return result if len(result) > 80 else None
            
        except Exception as e:
            logger.warning(f"Stack Overflow extractor failed for {url}: {e}")
            return None
    
    # ==================== SEARCH ENGINES ====================
    
    def _search_duckduckgo(self, query: str, num_results: int = 6) -> List[Dict[str, str]]:
        """
        Search DuckDuckGo using the duckduckgo_search library (reliable API).
        Falls back to HTML scraping if library is not installed.
        """
        try:
            from duckduckgo_search import DDGS
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=num_results):
                    results.append({
                        'title': r.get('title', ''),
                        'url': r.get('href', ''),
                        'snippet': r.get('body', ''),
                    })
            if results:
                logger.info(f"🦆 DuckDuckGo returned {len(results)} results for '{query}'")
            else:
                logger.warning(f"🦆 DuckDuckGo returned 0 results for '{query}'")
            return results
        except ImportError:
            logger.warning("duckduckgo_search not installed, falling back to HTML scrape")
            return self._search_duckduckgo_html(query, num_results)
        except Exception as e:
            logger.warning(f"DuckDuckGo API search failed: {e}, trying HTML fallback")
            return self._search_duckduckgo_html(query, num_results)
    
    def _search_duckduckgo_html(self, query: str, num_results: int = 6) -> List[Dict[str, str]]:
        """
        Fallback: Search DuckDuckGo using HTML scraping (fragile, may break).
        """
        try:
            session = self._get_session()
            url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
            response = session.get(url, timeout=self.TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            # Modern DuckDuckGo uses .result__a for links, .result__snippet for snippets
            for result_div in soup.select('.result'):
                title_elem = result_div.select_one('.result__a')
                snippet_elem = result_div.select_one('.result__snippet')
                if not title_elem:
                    continue
                href = title_elem.get('href', '')
                if href.startswith('/l/?uddg='):
                    import urllib.parse
                    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                    actual_url = parsed.get('uddg', [''])[0]
                else:
                    actual_url = href
                if not actual_url or not actual_url.startswith('http'):
                    continue
                results.append({
                    'title': title_elem.get_text(strip=True),
                    'url': actual_url,
                    'snippet': snippet_elem.get_text(strip=True) if snippet_elem else '',
                })
                if len(results) >= num_results:
                    break
            if not results:
                logger.warning(f"🦆 DuckDuckGo HTML scrape returned 0 results for '{query}'")
            else:
                logger.info(f"🦆 DuckDuckGo HTML returned {len(results)} results for '{query}'")
            return results
        except Exception as e:
            logger.warning(f"DuckDuckGo HTML search failed: {e}")
            return []
    
    def _search_google_scrape(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """
        Fallback: scrape Google search results (modern selectors, robust error handling).
        """
        try:
            session = self._get_session()
            url = f"https://www.google.com/search?q={quote_plus(query)}&hl=en"
            response = session.get(url, timeout=self.TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            # Modern Google: .yuRUbf a for links, .VwiC3b for snippets
            for g in soup.select('div.g'):
                title_elem = g.select_one('h3')
                link_elem = g.select_one('.yuRUbf a') or g.select_one('a[href]')
                snippet_elem = g.select_one('.VwiC3b') or g.select_one('.IsZvec') or g.select_one('span.st')
                if not title_elem or not link_elem:
                    continue
                href = link_elem.get('href', '')
                if not href.startswith('http'):
                    continue
                results.append({
                    'title': title_elem.get_text(strip=True),
                    'url': href,
                    'snippet': snippet_elem.get_text(strip=True) if snippet_elem else '',
                })
                if len(results) >= num_results:
                    break
            if not results:
                logger.warning(f"🔍 Google scrape returned 0 results for '{query}' (HTML scrape)")
            else:
                logger.info(f"🔍 Google scrape returned {len(results)} results for '{query}'")
            return results
        except Exception as e:
            logger.warning(f"Google scrape failed: {e}")
            return []
    
    # ==================== RESULT PRIORITIZATION ====================
    
    def _prioritize_results(self, results: List[Dict[str, str]], intent: str) -> List[Dict[str, str]]:
        """
        Re-rank search results based on domain quality and query intent.
        High-value sources (Wikipedia, IMDB, SO) float to the top.
        
        Args:
            results: List of search results
            intent: Query intent type
            
        Returns:
            Re-ranked results list
        """
        def score(result):
            url = result.get('url', '')
            domain = urlparse(url).netloc.lower()
            
            # Base score from domain priority
            base = 0
            for d, s in self.PRIORITY_DOMAINS.items():
                if d in domain:
                    base = s
                    break
            
            # Intent-specific boosting
            if intent == 'movie' and 'imdb.com' in domain:
                base += 50
            elif intent == 'tech' and 'stackoverflow.com' in domain:
                base += 50
            elif intent == 'wiki' and 'wikipedia.org' in domain:
                base += 50
            
            return base
        
        return sorted(results, key=score, reverse=True)
    
    # ==================== GENERIC PAGE SCRAPING ====================
    
    def _scrape_page(self, url: str) -> Optional[str]:
        """
        Scrape a web page and extract readable text content.
        Includes noise filtering and content deduplication.
        
        Args:
            url: URL to scrape
            
        Returns:
            Cleaned text content or None
        """
        try:
            session = self._get_session()
            response = session.get(url, timeout=self.TIMEOUT)
            response.raise_for_status()
            
            # Only process HTML content
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' not in content_type and 'application/xhtml' not in content_type:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unwanted tags
            for tag in soup.find_all(self.IGNORE_TAGS):
                tag.decompose()
            
            # Also remove cookie/consent banners and ad divs
            for tag in soup.find_all(class_=re.compile(r'cookie|consent|gdpr|banner|popup|modal|overlay|advert|sidebar', re.I)):
                tag.decompose()
            for tag in soup.find_all(id=re.compile(r'cookie|consent|gdpr|banner|popup|modal|overlay|advert', re.I)):
                tag.decompose()
            
            # Try to find main content area (more refined selectors)
            main_content = (
                soup.find('main') or 
                soup.find('article') or 
                soup.find(id=re.compile(r'^(content|main|body|post|article)$', re.I)) or
                soup.find(class_=re.compile(r'^(content|main|article|post|entry|story)(-|_)?(body|text|content)?$', re.I)) or
                soup.find('div', role='main') or
                soup.find('body')
            )
            
            if not main_content:
                return None
            
            # Extract text from content tags
            paragraphs = []
            seen_text = set()  # Deduplication
            
            for tag in main_content.find_all(self.CONTENT_TAGS):
                text = tag.get_text(strip=True)
                if not text or len(text) < 25:
                    continue
                
                # Skip noise
                text_lower = text.lower()
                if any(noise in text_lower for noise in self.NOISE_PHRASES):
                    continue
                
                # Deduplication (skip near-duplicate text)
                text_key = text[:80].lower()
                if text_key in seen_text:
                    continue
                seen_text.add(text_key)
                
                paragraphs.append(text)
            
            if paragraphs:
                return '\n'.join(paragraphs[:15])  # First 15 unique paragraphs
            
            # Fallback: get all text
            text = main_content.get_text(separator='\n', strip=True)
            lines = [line.strip() for line in text.split('\n') 
                     if line.strip() and len(line.strip()) > 25
                     and not any(noise in line.lower() for noise in self.NOISE_PHRASES)]
            return '\n'.join(lines[:20]) if lines else None
            
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout scraping {url}")
            return None
        except Exception as e:
            logger.warning(f"Failed to scrape {url}: {e}")
            return None
    
    # ==================== CONTENT POST-PROCESSING ====================
    
    def _deduplicate_content(self, content: str) -> str:
        """
        Remove duplicate/near-duplicate sentences across sources.
        
        Args:
            content: Combined content from multiple sources
            
        Returns:
            Deduplicated content
        """
        lines = content.split('\n')
        seen = set()
        unique_lines = []
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                unique_lines.append(line)
                continue
            
            # Use first 60 chars as dedup key (catches near-duplicates)
            key = stripped[:60].lower()
            if key in seen:
                continue
            seen.add(key)
            unique_lines.append(line)
        
        return '\n'.join(unique_lines)
    
    def cleanup(self):
        """Close HTTP session."""
        if self._session:
            try:
                self._session.close()
            except Exception:
                pass
            self._session = None
