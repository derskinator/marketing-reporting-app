import streamlit as st
import pandas as pd

st.set_page_config(page_title="Ad Attribution & ROAS Dashboard", layout="wide")
st.title("📊 ROAS Report by Platform and Ad")

# --- File Uploads ---
with st.sidebar:
    st.header("📁 Upload Your CSVs")
    shopify_file = st.file_uploader("🛒 Shopify Orders CSV", type="csv")
    meta_file = st.file_uploader("📘 Meta Ads CSV", type="csv")
    google_file = st.file_uploader("🔍 Google Ads CSV", type="csv")

# --- Robust Loaders ---
@st.cache_data
def load_shopify(file):
    try:
        df = pd.read_csv(file, quotechar='"', skiprows=[1], skip_blank_lines=True)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Shopify CSV Error: {e}")
        return pd.DataFrame()

@st.cache_data
def load_google(file):
    try:
        return pd.read_csv(file, encoding="utf-8", skip_blank_lines=True, on_bad_lines="skip")
    except Exception as e:
        st.error(f"Google CSV Error: {e}")
        return pd.DataFrame()

@st.cache_data
def load_meta(file):
    try:
        return pd.read_csv(file, encoding="utf-8")
    except Exception as e:
        st.error(f"Meta CSV Error: {e}")
        return pd.DataFrame()

# --- Load Uploaded Data ---
shopify_df = load_shopify(shopify_file) if shopify_file else pd.DataFrame()
meta_df = load_meta(meta_file) if meta_file else pd.DataFrame()
google_df = load_google(google_file) if google_file else pd.DataFrame()

# --- Identify Platform ---
def identify_platform(row):
    src = str(row.get("Order UTM source", "")).lower()
    med = str(row.get("Order UTM medium", "")).lower()
    ref = str(row.get("Order referrer name", "")).lower()
    if (src == "google" and med == "ad") or ("google" in ref and med == "ad"):
        return "Google Ads"
    elif (src in ["fb", "facebook", "ig", "instagram"] and med == "ad") or ref in ["facebook", "instagram"]:
        return "Meta Ads"
    elif src == "google":
        return "Google Organic"
    elif ref in ["google", "bing", "yahoo"]:
        return "Search (Organic)"
    elif src:
        return src.title()
    else:
        return "Other"

# --- Clean Spend Data ---
def clean_meta(df):
    if df.empty or "Ad name" not in df.columns or "Amount spent (USD)" not in df.columns:
        return pd.DataFrame()
    df = df.rename(columns={"Ad name": "ad_name", "Amount spent (USD)": "spend"})
    df["platform"] = "Meta Ads"
    return df[["ad_name", "spend", "platform"]]

def clean_google(df):
    df.columns = df.columns.str.lower().str.strip()
    if df.empty or "campaign" not in df.columns or "cost" not in df.columns:
        return pd.DataFrame()
    df = df.rename(columns={"cost": "spend", "campaign": "ad_name"})
    df["platform"] = "Google Ads"
    return df[["ad_name", "spend", "platform"]]

# --- Aggregate Reports ---
def platform_summary(shopify_df, spend_df):
    shopify_df["Platform"] = shopify_df.apply(identify_platform, axis=1)
    revenue = shopify_df.groupby("Platform").agg(
        Orders=("Orders", "sum"),
        Revenue=("Total sales", "sum")
    ).reset_index()
    spend = spend_df.groupby("platform").agg(Spend=("spend", "sum")).reset_index()
    summary = pd.merge(revenue, spend, left_on="Platform", right_on="platform", how="inner").drop(columns="platform")
    summary["ROAS"] = summary["Revenue"] / summary["Spend"]
    return summary

def ad_summary(shopify_df, spend_df):
    shopify_df["Platform"] = shopify_df.apply(identify_platform, axis=1)
    shopify_df = shopify_df.rename(columns={"Order UTM campaign": "ad_name"})
    sales = shopify_df.groupby(["Platform", "ad_name"]).agg(
        Orders=("Orders", "sum"),
        Revenue=("Total sales", "sum")
    ).reset_index()
    merged = pd.merge(sales, spend_df, on=["Platform", "ad_name"], how="inner")
    merged["ROAS"] = merged["Revenue"] / merged["spend"]
    return merged

# --- MAIN ---
if not shopify_df.empty:
    meta_clean = clean_meta(meta_df)
    google_clean = clean_google(google_df)
    all_spend = pd.concat([meta_clean, google_clean], ignore_index=True)

    if not all_spend.empty:
        st.subheader("📊 ROAS by Platform")
        platform_df = platform_summary(shopify_df, all_spend)
        st.dataframe(platform_df, use_container_width=True)

        st.subheader("📣 ROAS by Ad Campaign")
        ad_df = ad_summary(shopify_df, all_spend)
        st.dataframe(ad_df, use_container_width=True)
    else:
        st.warning("Upload Meta or Google ad spend to see ROAS reports.")
else:
    st.warning("Please upload a valid Shopify CSV to begin.")
