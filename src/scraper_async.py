# import re
# import asyncio
# import aiohttp
# from bs4 import BeautifulSoup
# from urllib.parse import urljoin, urlparse

# STRICT_EMAIL_RE = re.compile(
#     r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
# )

# def clean_email(raw_email: str):
#     """
#     Clean junk text before/after email and validate it.
#     Returns a valid email or None.
#     """
#     if not raw_email:
#         return None

#     # Remove whitespace and common separators
#     email = raw_email.strip().lower()

#     # Remove leading junk (numbers, symbols)
#     email = re.sub(r'^[^a-zA-Z]+', '', email)

#     # Remove trailing junk (words, numbers)
#     email = re.sub(r'[^a-zA-Z]+$', '', email)

#     # Remove embedded junk around @
#     email = re.sub(r'\s+', '', email)

#     # Validate strictly
#     if STRICT_EMAIL_RE.match(email):
#         return email

#     return None



# EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
# HEADERS = {
#     "User-Agent": "Mozilla/5.0 (compatible; CampScraper/1.0)"
# }

# SEM = asyncio.Semaphore(5)  # 🔒 concurrency limit

# def is_valid_url(url):
#     return url and isinstance(url, str) and url.startswith(("http://", "https://"))

# async def fetch(session, url):
#     async with SEM:
#         try:
#             async with session.get(url, timeout=15) as resp:
#                 if resp.status != 200:
#                     return None
#                 return await resp.text()
#         except:
#             return None

# async def scrape_page(session, url):
#     html = await fetch(session, url)
#     if not html:
#         return {"emails": [], "facebook": None, "instagram": None}

#     soup = BeautifulSoup(html, "lxml")
#     text = soup.get_text()

#     raw_emails = EMAIL_RE.findall(text)
#     emails = []

#     for e in raw_emails:
#         cleaned = clean_email(e)
#         if cleaned:
#             emails.append(cleaned)

#     emails = list(set(emails))


#     facebook = None
#     instagram = None

#     for a in soup.find_all("a", href=True):
#         href = a["href"].strip()
#         if "facebook.com" in href and not facebook:
#             facebook = href
#         if "instagram.com" in href and not instagram:
#             instagram = href

#     return {
#         "emails": emails,
#         "facebook": facebook,
#         "instagram": instagram
#     }




# async def scrape_website(website):
#     if not is_valid_url(website):
#         return None

#     urls = {website.rstrip("/")}
#     for path in ["/contact", "/about", "/contact-us"]:
#         urls.add(website.rstrip("/") + path)

#     async with aiohttp.ClientSession(headers=HEADERS) as session:
#         # 1️⃣ Scrape website pages
#         tasks = [scrape_page(session, url) for url in urls]
#         results = await asyncio.gather(*tasks)

#         best = {"emails": [], "facebook": None, "instagram": None}

#         for res in results:
#             if not res:
#                 continue
#             if res["emails"]:
#                 return res  # 🔥 Email found → stop immediately
#             if not best["facebook"] and res["facebook"]:
#                 best["facebook"] = res["facebook"]
#             if not best["instagram"] and res["instagram"]:
#                 best["instagram"] = res["instagram"]

#         # 2️⃣ If NO email but Facebook exists → scrape Facebook
#         if best["facebook"]:
#             fb_email = await scrape_facebook_email(session, best["facebook"])
#             if fb_email:
#                 best["emails"] = [fb_email]
#                 return best

#         return best



# async def scrape_facebook_email(session, fb_url):
#     """
#     Attempt to extract email from Facebook page HTML.
#     Works best for m.facebook.com or static pages.
#     """
#     try:
#         # Force mobile version (much easier to scrape)
#         if "facebook.com" in fb_url and not fb_url.startswith("https://m."):
#             fb_url = fb_url.replace("https://www.", "https://m.")
#             fb_url = fb_url.replace("https://facebook.com", "https://m.facebook.com")

#         async with session.get(fb_url, timeout=15) as resp:
#             if resp.status != 200:
#                 return None

#             html = await resp.text()

#             # 🔹 REGEX EMAIL EXTRACTION (BEST METHOD)
#             raw_emails = EMAIL_RE.findall(html)
#             for e in raw_emails:
#                 cleaned = clean_email(e)
#                 if cleaned:
#                     return cleaned
#             return None


#     except Exception:
#         return None



# changes to solve 5.2 error in render

import re
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin

STRICT_EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CampScraper/1.0)"
}

# Limits concurrency to 5 simultaneous HTTP requests
SEM = asyncio.Semaphore(5)

# --- Utilities ---
def clean_email(raw_email: str):
    if not raw_email:
        return None
    email = raw_email.strip().lower()
    email = re.sub(r'^[^a-zA-Z]+', '', email)
    email = re.sub(r'[^a-zA-Z]+$', '', email)
    email = re.sub(r'\s+', '', email)
    if STRICT_EMAIL_RE.match(email):
        return email
    return None

def is_valid_url(url):
    return url and isinstance(url, str) and url.startswith(("http://", "https://"))

# --- HTTP Fetch with retries ---
async def fetch(session, url, retries=3):
    for attempt in range(retries):
        try:
            async with SEM:
                async with session.get(url, timeout=15) as resp:
                    if resp.status == 200:
                        return await resp.text()
                    elif 500 <= resp.status < 600:
                        # Server errors, retry
                        await asyncio.sleep(2 ** attempt)
                    else:
                        return None
        except Exception:
            await asyncio.sleep(2 ** attempt)
    return None

# --- Scrape a single page ---
async def scrape_page(session, url):
    html = await fetch(session, url)
    if not html:
        return {"emails": [], "facebook": None, "instagram": None}

    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text()

    emails = list({clean_email(e) for e in EMAIL_RE.findall(text) if clean_email(e)})

    facebook = None
    instagram = None
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if "facebook.com" in href and not facebook:
            facebook = href
        if "instagram.com" in href and not instagram:
            instagram = href

    return {"emails": emails, "facebook": facebook, "instagram": instagram}

# --- Scrape Facebook email (mobile version) ---
async def scrape_facebook_email(session, fb_url):
    try:
        if "facebook.com" in fb_url and not fb_url.startswith("https://m."):
            fb_url = fb_url.replace("https://www.", "https://m.")
            fb_url = fb_url.replace("https://facebook.com", "https://m.facebook.com")
        html = await fetch(session, fb_url)
        if not html:
            return None
        for e in EMAIL_RE.findall(html):
            cleaned = clean_email(e)
            if cleaned:
                return cleaned
    except Exception:
        return None
    return None

# --- Scrape a website (main entry point) ---
async def scrape_website(session, website):
    if not is_valid_url(website):
        return None

    urls = {website.rstrip("/")}
    for path in ["/contact", "/about", "/contact-us"]:
        urls.add(website.rstrip("/") + path)

    tasks = [scrape_page(session, url) for url in urls]
    results = await asyncio.gather(*tasks)

    best = {"emails": [], "facebook": None, "instagram": None}

    for res in results:
        if not res:
            continue
        if res["emails"]:
            return res
        if not best["facebook"] and res["facebook"]:
            best["facebook"] = res["facebook"]
        if not best["instagram"] and res["instagram"]:
            best["instagram"] = res["instagram"]

    if best["facebook"]:
        fb_email = await scrape_facebook_email(session, best["facebook"])
        if fb_email:
            best["emails"] = [fb_email]
            return best

    return best

# --- Batch Scraper ---
async def scrape_batch(websites, batch_size=100):
    results = []
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        for i in range(0, len(websites), batch_size):
            batch = websites[i:i + batch_size]
            tasks = [scrape_website(session, site) for site in batch]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
    return results

# --- Example Usage ---
# websites = ["https://example1.com", "https://example2.com", ...]
# asyncio.run(scrape_batch(websites))
