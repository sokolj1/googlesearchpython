"""googlesearch is a Python library for searching Google, easily."""
from time import sleep
from bs4 import BeautifulSoup
from requests import get
from urllib.parse import unquote  # to decode the url
from .user_agents import get_useragent
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
from seleniumbase import Driver
from fake_useragent import UserAgent as FakeUserAgent
from urllib.parse import urlparse
import zipfile
import os

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

def create_proxy_auth_extension(proxy_host, proxy_port, proxy_user, proxy_pass, scheme='http', plugin_path=None):
    if plugin_path is None:
        plugin_path = 'proxy_auth_plugin.zip'

    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        }
    }
    """

    background_js = f"""
    var config = {{
        mode: "fixed_servers",
        rules: {{
            singleProxy: {{
                scheme: "{scheme}",
                host: "{proxy_host}",
                port: parseInt({proxy_port})
            }},
            bypassList: ["localhost"]
        }}
    }};

    chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{}});

    function callbackFn(details) {{
        return {{
            authCredentials: {{
                username: "{proxy_user}",
                password: "{proxy_pass}"
            }}
        }};
    }}

    chrome.webRequest.onAuthRequired.addListener(
        callbackFn,
        {{urls: ["<all_urls>"]}},
        ["blocking"]
    );
    """

    with zipfile.ZipFile(plugin_path, 'w') as zp:
        zp.writestr("manifest.json", manifest_json)
        zp.writestr("background.js", background_js)

    return plugin_path

def setup_seleniumbase_parameters(proxy_url):

    if proxy_url:
        # Parse the proxy URL
        parsed = urlparse(proxy_url)
        proxy_scheme = parsed.scheme
        proxy_netloc = parsed.netloc

        if '@' in proxy_netloc:
            # Extract authentication and proxy server details
            auth_info, host_info = proxy_netloc.split('@')
            proxy_user, proxy_pass = auth_info.split(':')
            proxy_host, proxy_port = host_info.split(':')
        else:
            # No authentication in proxy URL
            proxy_host, proxy_port = proxy_netloc.split(':')
            proxy_user = ''
            proxy_pass = ''

        # Create the proxy authentication extension
        pluginfile = create_proxy_auth_extension(
            proxy_host=proxy_host,
            proxy_port=proxy_port,
            proxy_user=proxy_user,
            proxy_pass=proxy_pass,
            scheme=proxy_scheme
        )

    else:
        pluginfile = None

    # Generate a random mobile user agent
    ua = FakeUserAgent()
    user_agent = ua.random

    return pluginfile, user_agent

def _fetch_playwright(
    url: str,
    user_agent: str,
    timeout: int,
    selector: str = None,
    proxies: dict = None, 
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
    if proxies:
        print("Using proxies: {}".format(proxies))
        proxy_url = proxies.get('https') or proxies.get('http')
        pluginfile, user_agent = setup_seleniumbase_parameters(proxy_url)
    else:
        pluginfile = None
        # Generate a random mobile user agent
        ua = FakeUserAgent()
        user_agent = ua.random
    
    driver = Driver(
                    browser='chrome',
                    uc=True, 
                    headless=True, 
                    agent=user_agent, 
                    extension_zip=pluginfile,
                    incognito=True,
                    disable_csp=True)
    # Set the page load timeout (in seconds)
    driver.set_page_load_timeout(timeout)

    try:
        # Navigate to the URL
        driver.get(url)

        # If a CSS selector is provided, wait for it to be visible on the page.
        if selector:
            try:
                WebDriverWait(driver, timeout).until(
                    EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, selector))
                )
            except Exception as e:
                print(
                    f"Warning: Selector '{selector}' not found before timeout. Error: {e}")

        # Retrieve the final HTML source of the page
        final_html = driver.page_source

        # Write the HTML to a file
        with open('google_headless.html', 'w', encoding='utf-8') as f:
            f.write(final_html)

        # Build the response object
        response_obj = PlaywrightResponse(status_code=200, html=final_html)
        
    except Exception as e:
        raise e
    
    finally:
        # Ensure the browser is closed regardless of success or failure
        driver.quit()
        
        # Clean up the plugin file
        if pluginfile and os.path.exists(pluginfile):
            os.remove(pluginfile)

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
            selector=selector, 
            proxies=proxies
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
    proxies = {"https": proxy, "http": proxy} if proxy and (
        proxy.startswith("https") or proxy.startswith("http")) else None

    start = start_num
    fetched_results = 0  # Keep track of the total fetched results
    fetched_links = set()  # to keep track of links that are already seen previously

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
            title_tag = link_tag.find(
                "span", class_="CVA68e") if link_tag else None
            # Find the description tag within the result block
            description_tag = result.find("span", class_="FrIlee")

            # Check if all necessary tags are found
            if link_tag and title_tag and description_tag:
                # Extract and decode the link URL
                link = unquote(link_tag["href"].split("&")[0].replace(
                    "/url?q=", "")) if link_tag else ""
            # Extract and decode the link URL
            link = unquote(link_tag["href"].split("&")[0].replace(
                "/url?q=", "")) if link_tag else ""
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
                # Yield a SearchResult object
                yield SearchResult(link, title, description)
            else:
                yield link  # Yield only the link

            if fetched_results >= num_results:
                break  # Stop if we have fetched the desired number of results

        if new_results == 0:
            # If you want to have printed to your screen that the desired amount of queries can not been fulfilled, uncomment the line below:
            # print(f"Only {fetched_results} results found for query requiring {num_results} results. Moving on to the next query.")
            break  # Break the loop if no new results were found in this iteration

        start += 10  # Prepare for the next set of results
        sleep(sleep_interval)
