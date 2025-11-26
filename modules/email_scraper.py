import requests
from bs4 import BeautifulSoup
import re

def extract_email(url):
    if not url:
        return None

    try:
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text()

        emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)

        return emails[0] if emails else None
    except:
        return None
