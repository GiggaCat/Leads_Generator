from serpapi import GoogleSearch
from config.settings import API_KEY

def fetch_leads(query, api_key):
    params = {
        "engine": "google_maps",
        "q": query,
        "type": "search",
        "api_key": API_KEY
    }

    search = GoogleSearch(params)
    results = search.get_dict()

    return results.get("local_results", [])
