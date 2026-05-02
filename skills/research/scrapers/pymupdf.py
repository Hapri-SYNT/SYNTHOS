import os
import requests
import tempfile
from urllib.parse import urlparse
from langchain_community.document_loaders import PyMuPDFLoader

class PyMuPDFScraper:
    def __init__(self, link, session=None):
        self.link = link
        self.session = session

    def is_url(self) -> bool:
        try:
            result = urlparse(self.link)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def scrape(self) -> tuple[str, list[str], str]:
        try:
            if self.is_url():
                try:
                    response = requests.get(self.link, timeout=(5, 30), stream=True)
                    response.raise_for_status()
                except requests.exceptions.SSLError:
                    response = requests.get(self.link, timeout=(5, 30), stream=True, verify=False)
                    response.raise_for_status()

                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                    temp_filename = temp_file.name
                    for chunk in response.iter_content(chunk_size=8192):
                        temp_file.write(chunk)

                loader = PyMuPDFLoader(temp_filename)
                doc = loader.load()
                os.remove(temp_filename)
            else:
                loader = PyMuPDFLoader(self.link)
                doc = loader.load()

            image = []
            content = "\n".join(page.page_content for page in doc)
            title = doc[0].metadata.get("title", "") if doc else ""
            return content, image, title

        except requests.exceptions.Timeout:
            print(f"Download timed out. Please check the link : {self.link}")
            return "", [], ""
        except Exception as e:
            print(f"Error loading PDF : {self.link} {e}")
            return "", [], ""
