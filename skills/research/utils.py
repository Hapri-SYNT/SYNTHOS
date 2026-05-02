# skills/research/utils.py
from bs4 import BeautifulSoup

def clean_soup(soup):
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return soup

def get_text_from_soup(soup):
    return soup.get_text(separator=' ', strip=True)

def extract_title(soup):
    title_tag = soup.find('title')
    return title_tag.get_text(strip=True) if title_tag else ""

def get_relevant_images(soup, base_url):
    from urllib.parse import urljoin
    images = []
    for img in soup.find_all('img', src=True):
        src = img['src']
        if src.startswith('http'):
            images.append(src)
        else:
            images.append(urljoin(base_url, src))
    return images[:5]
