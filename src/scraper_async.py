import re
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

STRICT_EMAIL_RE = re.compile(
    r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
)

def clean_email(raw_email: str):
    """
    Clean junk text before/after email and validate it.
    Returns a valid email or None.
    """
    if not raw_email:
        return None

    # Remove whitespace and common separators
    email = raw_email.strip().lower()

    # Remove leading junk (numbers, symbols)
    email = re.sub(r'^[^a-zA-Z]+', '', email)

    # Remove trailing junk (words, numbers)
    email = re.sub(r'[^a-zA-Z]+$', '', email)

    # Remove embedded junk around @
    email = re.sub(r'\s+', '', email)

    # Validate strictly
    if STRICT_EMAIL_RE.match(email):
        return email

    return None



EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CampScraper/1.0)"
}

SEM = asyncio.Semaphore(5)  # 🔒 concurrency limit

def is_valid_url(url):
    return url and isinstance(url, str) and url.startswith(("http://", "https://"))

async def fetch(session, url):
    async with SEM:
        try:
            async with session.get(url, timeout=15) as resp:
                if resp.status != 200:
                    return None
                return await resp.text()
        except:
            return None

async def scrape_page(session, url):
    html = await fetch(session, url)
    if not html:
        return {"emails": [], "facebook": None, "instagram": None}

    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text()

    raw_emails = EMAIL_RE.findall(text)
    emails = []

    for e in raw_emails:
        cleaned = clean_email(e)
        if cleaned:
            emails.append(cleaned)

    emails = list(set(emails))


    facebook = None
    instagram = None

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if "facebook.com" in href and not facebook:
            facebook = href
        if "instagram.com" in href and not instagram:
            instagram = href

    return {
        "emails": emails,
        "facebook": facebook,
        "instagram": instagram
    }

# async def scrape_website(website):
#     if not is_valid_url(website):
#         return None

#     urls = {website.rstrip("/")}
#     for path in ["/contact", "/about", "/contact-us"]:
#         urls.add(website.rstrip("/") + path)

#     async with aiohttp.ClientSession(headers=HEADERS) as session:
#         tasks = [scrape_page(session, url) for url in urls]
#         results = await asyncio.gather(*tasks)

#     for res in results:
#         if res and (res["emails"] or res["facebook"] or res["instagram"]):
#             return res

#     return {"emails": [], "facebook": None, "instagram": None}


async def scrape_website(website):
    if not is_valid_url(website):
        return None

    urls = {website.rstrip("/")}
    for path in ["/contact", "/about", "/contact-us"]:
        urls.add(website.rstrip("/") + path)

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        # 1️⃣ Scrape website pages
        tasks = [scrape_page(session, url) for url in urls]
        results = await asyncio.gather(*tasks)

        best = {"emails": [], "facebook": None, "instagram": None}

        for res in results:
            if not res:
                continue
            if res["emails"]:
                return res  # 🔥 Email found → stop immediately
            if not best["facebook"] and res["facebook"]:
                best["facebook"] = res["facebook"]
            if not best["instagram"] and res["instagram"]:
                best["instagram"] = res["instagram"]

        # 2️⃣ If NO email but Facebook exists → scrape Facebook
        if best["facebook"]:
            fb_email = await scrape_facebook_email(session, best["facebook"])
            if fb_email:
                best["emails"] = [fb_email]
                return best

        return best



async def scrape_facebook_email(session, fb_url):
    """
    Attempt to extract email from Facebook page HTML.
    Works best for m.facebook.com or static pages.
    """
    try:
        # Force mobile version (much easier to scrape)
        if "facebook.com" in fb_url and not fb_url.startswith("https://m."):
            fb_url = fb_url.replace("https://www.", "https://m.")
            fb_url = fb_url.replace("https://facebook.com", "https://m.facebook.com")

        async with session.get(fb_url, timeout=15) as resp:
            if resp.status != 200:
                return None

            html = await resp.text()

            # 🔹 REGEX EMAIL EXTRACTION (BEST METHOD)
            raw_emails = EMAIL_RE.findall(html)
            for e in raw_emails:
                cleaned = clean_email(e)
                if cleaned:
                    return cleaned
            return None


    except Exception:
        return None
