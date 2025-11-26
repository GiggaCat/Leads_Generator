import io
import os
import tempfile
from datetime import datetime

import pandas as pd
import streamlit as st

# Try to import your existing backend (we won't modify them).
from config import settings
from modules import serpapi_fetch, email_scraper, excel_manager, utils

# ---------------------------
# Helper wrappers (robust)
# ---------------------------
def safe_fetch_leads(query, api_key):
    """
    Try calling fetch_leads with common signatures:
    1) fetch_leads(query, api_key)
    2) fetch_leads(query)
    Return list (or empty list on error)
    """
    try:
        # Preferred signature: (query, api_key)
        return serpapi_fetch.fetch_leads(query, api_key)
    except TypeError:
        try:
            # Older signature: (query,)
            return serpapi_fetch.fetch_leads(query)
        except Exception as e:
            st.error(f"fetch_leads failed for '{query}': {e}")
            utils.log_message(f"fetch_leads error: {e}")
            return []
    except Exception as e:
        st.error(f"fetch_leads failed for '{query}': {e}")
        utils.log_message(f"fetch_leads error: {e}")
        return []

def safe_append_to_excel(dataframe_or_list, out_file):
    """
    Try common append_to_excel signatures:
    1) append_to_excel(list_of_dicts, out_file)
    2) append_to_excel(pd.DataFrame, out_file)
    3) excel_manager.append_to_excel(dataframe, out_file)
    If not available, fallback to pandas to_excel (append by reading/writing).
    """
    try:
        # try direct call with list first (some backends expect list)
        try:
            return excel_manager.append_to_excel(dataframe_or_list, out_file)
        except TypeError:
            # maybe it expects a DataFrame
            if isinstance(dataframe_or_list, list):
                df = pd.DataFrame(dataframe_or_list)
            else:
                df = dataframe_or_list
            return excel_manager.append_to_excel(df, out_file)
    except Exception as e:
        # fallback: manual append using pandas + openpyxl
        try:
            if isinstance(dataframe_or_list, list):
                df_new = pd.DataFrame(dataframe_or_list)
            else:
                df_new = dataframe_or_list

            # If file exists, read and concat (preserve whatever formatting may be lost).
            if os.path.exists(out_file):
                df_old = pd.read_excel(out_file)
                df_combined = pd.concat([df_old, df_new], ignore_index=True)
            else:
                df_combined = df_new

            df_combined.to_excel(out_file, index=False)
            return True
        except Exception as e2:
            st.error(f"Failed to save to Excel: {e2}")
            utils.log_message(f"Excel save error: {e2}")
            return False

def safe_extract_email(url):
    try:
        return email_scraper.extract_email(url)
    except TypeError:
        # maybe function signature differs; try calling differently or return None
        try:
            return email_scraper.extract_email(url)
        except Exception:
            return None
    except Exception:
        return None

# ---------------------------
# Streamlit UI & logic
# ---------------------------

# Page config
st.set_page_config(page_title="Leads Generator", layout="wide", initial_sidebar_state="expanded")

# Dark mode CSS + small animations
st.markdown(
    """
    <style>
    /* Dark background */
    .reportview-container, .main, .block-container {background:#0f1720; color:#e6eef8;}
    /* Sidebar */
    .css-1d391kg { background: linear-gradient(180deg,#071026 0%, #0b1530 100%); }
    /* Cards */
    .card { background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01)); padding:12px; border-radius:10px; box-shadow: 0 6px 18px rgba(2,6,23,0.6); }
    /* Animated button hover */
    .stButton>button { transition: transform 0.12s ease-in-out; }
    .stButton>button:hover { transform: translateY(-3px); }
    /* Table header highlight */
    .stDataFrame thead tr th { background: rgba(255,255,255,0.04) !important; }
    /* small fade-in animation */
    @keyframes fadeInUp {
      from {opacity:0; transform: translateY(8px);}
      to {opacity:1; transform: translateY(0);}
    }
    .animate { animation: fadeInUp 0.35s ease both; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Sidebar
with st.sidebar:
    st.markdown("## ⚙️ Settings", unsafe_allow_html=True)
    # SerpAPI key input (allow user to add their own)
    api_from_config = getattr(settings, "API_KEY", "")
    serpapi_key = st.text_input("SerpAPI Key (you can paste your own)", value=api_from_config, type="password")
    st.caption("If left empty, will try config.settings.API_KEY if available.")
    st.markdown("---")

    # File uploader to choose existing excel (user's own output file)
    user_file = st.file_uploader("📁 Upload an existing Excel to append (optional)", type=["xlsx", "xls"])
    st.markdown("If you upload a file, the app will append new leads into it (keeps your formatting if excel_manager supports it).")
    st.markdown("---")

    # Skip email scraping option
    skip_email = st.checkbox("Skip email scraping (faster)", value=False)

    st.markdown("---")
    st.markdown("## UI")
    dark_toggle = st.checkbox("Dark UI (keep)", value=True, disabled=True)
    st.markdown("---")
    st.caption("Developed by you — runs on your machine. No backend changes required.")

# Main layout
st.title("🚀 Leads Generator — Streamlit UI")
st.write("Enter one or multiple search queries (comma separated). Example: `cafes in Delhi, salons in Jaipur`")

# Input area
queries_input = st.text_area("Search queries (comma separated)", placeholder="cafes in Delhi, gyms in Gurgaon", height=80)
queries = [q.strip() for q in queries_input.split(",") if q.strip()]

# Additional controls
col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    max_results = st.number_input("Max places per query (approx)", min_value=1, max_value=100, value=20, step=1)
with col2:
    sample_mode = st.checkbox("Preview only (don't save)", value=False)
with col3:
    run_button = st.button("🔎 Generate Leads", key="generate")

# Space for results
results_placeholder = st.empty()

# Helper to get output file path
def get_output_file_path(uploaded_file):
    if uploaded_file:
        # Save uploaded to temp path and use it as the output file
        temp_dir = tempfile.gettempdir()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join(temp_dir, f"user_uploaded_{ts}.xlsx")
        with open(out_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return out_path
    else:
        # default output in project output folder
        default_name = getattr(settings, "OUTPUT_FILE", "output/all_leads.xlsx")
        # ensure folder exists
        folder = os.path.dirname(default_name) or "."
        if folder and not os.path.exists(folder):
            try:
                os.makedirs(folder, exist_ok=True)
            except Exception:
                pass
        return default_name

# Main run logic
if run_button:
    if not queries:
        st.warning("⚠️ Enter at least one query before running.")
    else:
        if not serpapi_key:
            # still try config
            serpapi_key = getattr(settings, "API_KEY", None)
            if not serpapi_key:
                st.warning("No SerpAPI key provided and none found in config.settings. Provide a key to continue.")
                st.stop()

        output_file_path = get_output_file_path(user_file)

        progress = st.progress(0)
        all_leads = []
        total_queries = len(queries)
        for i, q in enumerate(queries, start=1):
            progress.progress(int((i - 1) / total_queries * 100))
            st.info(f"Searching: **{q}**")
            places = safe_fetch_leads(q, serpapi_key)

            # limit results
            if places is None:
                places = []
            if isinstance(places, (list, tuple)):
                places = places[:int(max_results)]
            else:
                # sometimes serpapi returns dict with list inside; try to extract
                if isinstance(places, dict):
                    candidate = places.get("local_results") or places.get("results") or list(places.values())
                    if isinstance(candidate, list):
                        places = candidate[:int(max_results)]
                    else:
                        places = []

            for place in places:
                website = place.get("website") if isinstance(place, dict) else None
                email = None
                if not skip_email and website:
                    email = safe_extract_email(website)

                lead = {
                    "Name": place.get("title") if isinstance(place, dict) else None,
                    "Category": place.get("category") if isinstance(place, dict) else None,
                    "Address": place.get("address") if isinstance(place, dict) else None,
                    "Phone": place.get("phone") if isinstance(place, dict) else None,
                    "Website": website,
                    "Email": email,
                    "Rating": place.get("rating") if isinstance(place, dict) else None,
                    "Reviews": place.get("reviews") if isinstance(place, dict) else None,
                    "Search Query": q
                }
                all_leads.append(lead)

        progress.progress(100)

        # Convert to DataFrame for preview/stats
        df_new = pd.DataFrame(all_leads)

        # Remove duplicates locally by Name + Phone if present
        if not df_new.empty and "Name" in df_new.columns and "Phone" in df_new.columns:
            before = len(df_new)
            df_new.drop_duplicates(subset=["Name", "Phone"], inplace=True)
            after = len(df_new)
            utils.log_message(f"Deduped new leads: {before}->{after}")

        # Summary stats
        total_new = len(df_new)
        has_email = df_new["Email"].notna().sum() if "Email" in df_new.columns else 0
        no_website = df_new["Website"].isna().sum() if "Website" in df_new.columns else 0

        # Preview & dashboard
        with results_placeholder.container():
            st.markdown("### Preview & Dashboard", unsafe_allow_html=True)
            st.markdown(f"<div class='card animate'>"
                        f"<b>Total new leads:</b> {total_new} &nbsp; • &nbsp; "
                        f"<b>With email:</b> {has_email} &nbsp; • &nbsp; "
                        f"<b>Without website:</b> {no_website}"
                        f"</div>", unsafe_allow_html=True)

            st.markdown("#### Lead Preview (first 200 rows)")
            if df_new.empty:
                st.info("No leads found for these queries.")
            else:
                st.dataframe(df_new.head(200), use_container_width=True)

            # Download new leads as Excel
            if not df_new.empty:
                towrite = io.BytesIO()
                df_new.to_excel(towrite, index=False, engine="openpyxl")
                towrite.seek(0)
                st.download_button(
                    label="📥 Download new leads (xlsx)",
                    data=towrite,
                    file_name=f"new_leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        # Save (append) if not preview-only
        if not sample_mode and not df_new.empty:
            st.info(f"Appending {len(df_new)} leads to: `{output_file_path}`")
            ok = safe_append_to_excel(df_new, output_file_path)
            if ok:
                st.success(f"✅ Saved/updated: {output_file_path}")
                utils.log_message(f"Appended {len(df_new)} leads to {output_file_path}")
            else:
                st.error("Failed to append leads. Check logs or file permissions.")

        # final summary
        st.balloons()
        st.success(f"Done — Generated {total_new} leads. Preview above. {'(not saved)' if sample_mode else ''}")

# Footer / help
st.markdown("---")
st.markdown("**Tips:**\n\n- If you upload your own Excel, the app will use that as the output base file (it will be saved to a temp path). \n- If you change the Excel file name in `config.settings.OUTPUT_FILE`, the app will use the new name automatically. \n- Toggle *Skip email scraping* to speed up runs.\n\nIf you want additional UI features (filters, map view, scheduled runs), tell me and I'll add them!")


