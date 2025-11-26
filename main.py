from config.settings import API_KEY, OUTPUT_FILE
from modules.serpapi_fetch import fetch_leads
from modules.email_scraper import extract_email
from modules.excel_manager import append_to_excel
from modules.utils import log_message
import pandas as pd

def generate_leads(queries, api_key=API_KEY, output_file=OUTPUT_FILE):
    all_leads = []

    for q in queries:
        print(f"🔍 Searching: {q}")
        places = fetch_leads(q, API_KEY)

        for place in places:
            website = place.get("website")
            email = extract_email(website)

            lead = {
                "Name": place.get("title"),
                "Category": place.get("category"),
                "Address": place.get("address"),
                "Phone": place.get("phone"),
                "Website": website,
                "Email": email,
                "Rating": place.get("rating"),
                "Reviews": place.get("reviews")
            }
            all_leads.append(lead)
            
    df_new = pd.DataFrame(all_leads)
    
    append_to_excel(all_leads, OUTPUT_FILE)
    log_message(f"Added {len(all_leads)} new leads")
    print(f"Added {len(all_leads)} new leads")
    
    return df_new

if __name__ == "__main__":
    print("Enter multiple queries separated by comma:")
    user_input = input("Search: ")

    queries = [q.strip() for q in user_input.split(",")]

    generate_leads(queries)
