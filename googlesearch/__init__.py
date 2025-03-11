"""googlesearch is a Python library for searching Google, easily."""
from time import sleep
from bs4 import BeautifulSoup
from requests import get
from urllib.parse import unquote # to decode the url
from .user_agents import get_useragent
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
from seleniumbase import Driver

class PlaywrightResponse:
    """
    A minimal "response-like" class to mimic requests.Response enough
    that your downstream code can check .status_code or .text.
    """
    def __init__(self, status_code: int, html: str):
        self.status_code = status_code
        self._html = html

    @property
    def text(self):
        return self._html

    def raise_for_status(self):
        if self.status_code < 200 or self.status_code >= 300:
            raise RuntimeError(f"HTTP status code: {self.status_code}")

    # Optionally, you can add .content or other methods if needed.
    @property
    def content(self):
        return self._html.encode("utf-8")
    
    
def _fetch_playwright(
    url: str,
    user_agent: str,
    timeout: int,
    selector: str = None,
):
    """
    Launches a browser via undetected_chromedriver (Selenium), navigates to `url`,
    optionally waits for `selector` to appear, and returns the HTML
    as a PlaywrightResponse.

    :param url: The URL to navigate to.
    :param user_agent: The user-agent string to use for the browser page.
    :param timeout: Timeout in seconds for page load / selector wait.
    :param selector: An optional CSS selector to wait for (e.g. "div.YrbPuc").
    :return: A PlaywrightResponse with .status_code and .text.
    """
    # Set up Chrome options similar to your original Playwright arguments
    # options = uc.ChromeOptions()
    # options.add_argument("--disable-blink-features=AutomationControlled")
    # options.add_argument("--no-sandbox")
    # options.add_argument(f"--user-agent={user_agent}")
    # Initialize undetected_chromedriver (which includes stealth measures by default)
    # driver = uc.Chrome(options=options)
    driver = Driver(uc=True, headless=True)
    # Set the page load timeout (in seconds)
    driver.set_page_load_timeout(timeout)
    
    try:
        # Navigate to the URL
        driver.get(url)
        
        # If a CSS selector is provided, wait for it to be visible on the page.
        if selector:
            try:
                WebDriverWait(driver, timeout).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, selector))
                )
            except Exception as e:
                print(f"Warning: Selector '{selector}' not found before timeout. Error: {e}")
        
        # Retrieve the final HTML source of the page
        final_html = driver.page_source
        
        # Write the HTML to a file
        with open('/Users/johnsokol/Desktop/google_headless.html', 'w', encoding='utf-8') as f:
            f.write(final_html)
    
        # Build the response object
        response_obj = PlaywrightResponse(status_code=200, html=final_html)
    
    finally:
        # Ensure the browser is closed regardless of success or failure
        driver.quit()
    
    return response_obj


def _req(
    term,
    results,
    lang,
    start,
    proxies,
    timeout,
    safe,
    ssl_verify,
    region,
    javascript=False
):
    """
    Make a Google search request.
    - If javascript=False, uses plain requests (no JavaScript).
    - If javascript=True, uses requests-html (Pyppeteer) to render JS
      and waits for CSS selector "div.YrbPuc".

    :param term: Search term (string)
    :param results: Number of results (int)
    :param lang: Language parameter (e.g. 'en')
    :param start: Starting result index for pagination
    :param proxies: Dict of HTTP proxies or None
    :param timeout: Request/render timeout (seconds)
    :param safe: Safe search mode (e.g. 'off' or 'active')
    :param ssl_verify: Whether to verify SSL (bool)
    :param region: 'gl' parameter for region (e.g. 'US')
    :param javascript: If True, render JavaScript via Pyppeteer
    :return: A Response-like object. If javascript=True, it's an
             AsyncHTMLResponse from requests-html. If javascript=False,
             it's a normal requests.Response.
    """
    url = "https://www.google.com/search"
    headers = {
        "User-Agent": get_useragent(),
        "Accept": "*/*"
    }
    params = {
        "q": term,
        "num": results + 2,  # So we don't trigger multiple requests
        "hl": lang,
        "start": start,
        "safe": safe,
        "gl": region
    }
    cookies = {
        "CONSENT": "PENDING+987",  # Attempt to bypass Google's consent page
        "SOCS": "CAESHAgBEhIaAB"
    }
    
    base_url = "https://www.google.com/search"
    
    url = requests.Request("GET", base_url, params=params).prepare().url

    # ---------------------------
    # 1) Plain requests mode
    # ---------------------------
    if not javascript:
        resp = get(
            url=url,
            headers=headers,
            params=params,
            proxies=proxies,
            timeout=timeout,
            verify=ssl_verify,
            cookies=cookies
        )
        resp.raise_for_status()
        return resp

    # ---------------------------
    # 2) JavaScript rendering mode
    # ---------------------------
    else:
        # Use Playwright
        # Example: Wait for "div.YrbPuc" as a snippet container
        selector = "div.YrbPuc"
        # If your page loads a different snippet or other dynamic content,
        # change the selector or remove it if not needed.
        resp = _fetch_playwright(
            url=url,
            user_agent=get_useragent(),
            timeout=timeout,
            selector=selector
        )
        resp.raise_for_status()
        return resp

'''
def _req(term, results, lang, start, proxies, timeout, safe, ssl_verify, region):
    resp = get(
        url="https://www.google.com/search",
        headers={
            "User-Agent": get_useragent(),
            "Accept": "*/*"
        },
        params={
            "q": term,
            "num": results + 2,  # Prevents multiple requests
            "hl": lang,
            "start": start,
            "safe": safe,
            "gl": region,
        },
        proxies=proxies,
        timeout=timeout,
        verify=ssl_verify,
        cookies = {
            'CONSENT': 'PENDING+987', # Bypasses the consent page
            'SOCS': 'CAESHAgBEhIaAB',
        }
    )
    resp.raise_for_status()
    return resp
'''

class SearchResult:
    def __init__(self, url, title, description):
        self.url = url
        self.title = title
        self.description = description

    def __repr__(self):
        return f"SearchResult(url={self.url}, title={self.title}, description={self.description})"


def search(term, num_results=10, lang="en", proxy=None, advanced=False, sleep_interval=0, timeout=5, safe="active", ssl_verify=None, region=None, start_num=0, unique=False, javascript=False):
    """Search the Google search engine"""

    # Proxy setup
    proxies = {"https": proxy, "http": proxy} if proxy and (proxy.startswith("https") or proxy.startswith("http")) else None

    start = start_num
    fetched_results = 0  # Keep track of the total fetched results
    fetched_links = set() # to keep track of links that are already seen previously

    while fetched_results < num_results:
        # Send request
        
        if not javascript:
            resp = _req(term, num_results - start,
                        lang, start, proxies, timeout, safe, ssl_verify, region)
        else:
            resp = _req(term, num_results - start,
                        lang, start, proxies, timeout, safe, ssl_verify, region, javascript=True)
            
            yield BeautifulSoup(resp.text, "html.parser")
        
        # put in file - comment for debugging purpose
        # with open('google.html', 'w') as f:
        #     f.write(resp.text)
        
        # Parse
        soup = BeautifulSoup(resp.text, "html.parser")
        result_block = soup.find_all("div", class_="ezO2md")
        new_results = 0  # Keep track of new results in this iteration

        for result in result_block:
            # Find the link tag within the result block
            link_tag = result.find("a", href=True)
            # Find the title tag within the link tag
            title_tag = link_tag.find("span", class_="CVA68e") if link_tag else None
            # Find the description tag within the result block
            description_tag = result.find("span", class_="FrIlee")

            # Check if all necessary tags are found
            if link_tag and title_tag and description_tag:
                # Extract and decode the link URL
                link = unquote(link_tag["href"].split("&")[0].replace("/url?q=", "")) if link_tag else ""
            # Extract and decode the link URL
            link = unquote(link_tag["href"].split("&")[0].replace("/url?q=", "")) if link_tag else ""
            # Check if the link has already been fetched and if unique results are required
            if link in fetched_links and unique:
                continue  # Skip this result if the link is not unique
            # Add the link to the set of fetched links
            fetched_links.add(link)
            # Extract the title text
            title = title_tag.text if title_tag else ""
            # Extract the description text
            description = description_tag.text if description_tag else ""
            # Increment the count of fetched results
            fetched_results += 1
            # Increment the count of new results in this iteration
            new_results += 1
            # Yield the result based on the advanced flag
            if advanced:
                yield SearchResult(link, title, description)  # Yield a SearchResult object
            else:
                yield link  # Yield only the link

            if fetched_results >= num_results:
                break  # Stop if we have fetched the desired number of results

        if new_results == 0:
            #If you want to have printed to your screen that the desired amount of queries can not been fulfilled, uncomment the line below:
            #print(f"Only {fetched_results} results found for query requiring {num_results} results. Moving on to the next query.")
            break  # Break the loop if no new results were found in this iteration

        start += 10  # Prepare for the next set of results
        sleep(sleep_interval)
