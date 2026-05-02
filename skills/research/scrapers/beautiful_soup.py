from bs4 import BeautifulSoup
from urllib.parse import urljoin
from ..utils import get_relevant_images, extract_title, get_text_from_soup, clean_soup  # asumsikan utils ada

class BeautifulSoupScraper:
    def __init__(self, link, session=None):
        self.link = link
        self.session = session or requests.Session()

    def scrape(self):
        try:
            response = self.session.get(self.link, timeout=4)
            soup = BeautifulSoup(
                response.content, "lxml", from_encoding=response.encoding
            )
            soup = clean_soup(soup)
            content = get_text_from_soup(soup)
            image_urls = get_relevant_images(soup, self.link)
            title = extract_title(soup)
            return content, image_urls, title
        except Exception as e:
            print("Error! : " + str(e))
            return "", [], ""
