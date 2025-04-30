import streamlit as st
import pandas as pd

st.set_page_config(page_title="Ad Attribution & ROAS Dashboard", layout="wide")
st.title("📊 Multi-Channel Attribution & ROAS Dashboard")

# --- File Uploads ---
with st.sidebar:
    st.header("📁 Upload CSVs")
    shopify_file = st.file_uploader("🛒 Shopify Orders CSV", type="csv")
    google_file = st.file_uploader("🔍 Google Ads CSV", type="csv")
    meta_file = st.file_uploader("📘 Meta Ads CSV", type="csv")

# --- Load Data ---
@st.cache_data
def load_shopify_csv(file):
    if file is None:
        return pd.DataFrame()
    try:
        df = pd.read_csv(file, quotechar='"', skip_blank_lines=True, skiprows=[1])
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Shopify CSV error: {e}")
        return pd.DataFrame()

@st.cache_data
def load_other_csv(file):
    if file is None:
        return pd.DataFrame()
    try:
        return pd.read_csv(file)
    except:
        return pd.DataFrame()

shopify_df = load_shopify_csv(shopify_file)
google_df = load_other_csv(google_file)
meta_df = load_other_csv(meta_file)

# --- Helper Functions ---
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

def clean_spend_data(df, platform_name):
    if df is None or df.empty:
        return pd.DataFrame(columns=["campaign", "spend", "ad_name", "platform"])
    df.columns = df.columns.str.lower().str.strip()
    if platform_name == "Meta Ads" and "amount spent (usd)" in df.columns:
        df["spend"] = df["amount spent (usd)"]
    elif platform_name == "Google Ads" and "cost" in df.columns:
        df["spend"] = df["cost"]
    else:
        return pd.DataFrame(columns=["campaign", "spend", "ad_name", "platform"])
    df["platform"] = platform_name
    return df[["campaign", "spend", "ad_name", "platform"]]

def aggregate_platform_summary(shopify_df, spend_df):
    rev = shopify_df[shopify_df["Platform"].isin(["Meta Ads", "Google Ads"])].groupby("Platform").agg(
        Orders=("Orders", "sum"),
        Revenue=("Total sales", "sum")
    ).reset_index()
    spend_summary = spend_df.groupby("platform").agg(
        Spend=("spend", "sum")
    ).reset_index()
    merged = pd.merge(rev, spend_summary, left_on="Platform", right_on="platform", how="left").drop(columns="platform")
    merged["ROAS"] = merged["Revenue"] / merged["Spend"]
    return merged

def aggregate_ad_summary(shopify_df, spend_df):
    sales = shopify_df.groupby(["Platform", "Order UTM campaign"]).agg(
        Orders=("Orders", "sum"),
        Revenue=("Total sales", "sum")
    ).reset_index()
    ads = pd.merge(sales, spend_df, left_on="Order UTM campaign", right_on="campaign", how="inner")
    ads["ROAS"] = ads["Revenue"] / ads["spend"]
    return ads

# --- Main App ---
if not shopify_df.empty:
    shopify_df["Platform"] = shopify_df.apply(identify_platform, axis=1)
    shopify_df["customer_id"] = shopify_df.get("Order referrer name", pd.Series(range(len(shopify_df))))
    shopify_df["is_new_customer"] = ~shopify_df.duplicated(subset=["customer_id"], keep='first')

    google_spend = clean_spend_data(google_df, "Google Ads")
    meta_spend = clean_spend_data(meta_df, "Meta Ads")
    combined_spend = pd.concat([google_spend, meta_spend])

    # --- ROAS by Platform ---
    if not combined_spend.empty:
        st.subheader("📈 ROAS by Platform")
        platform_summary = aggregate_platform_summary(shopify_df, combined_spend)
        st.dataframe(platform_summary, use_container_width=True)

    # --- ROAS by Ad Campaign ---
    st.subheader("📣 ROAS by Ad Campaign")
    ad_summary = aggregate_ad_summary(shopify_df, combined_spend)
    st.dataframe(ad_summary[["platform", "campaign", "ad_name", "spend", "Orders", "Revenue", "ROAS"]], use_container_width=True)

    # --- New Customers ---
    st.subheader("🧍‍♂️ New Customers by Platform")
    new_cust_summary = shopify_df[shopify_df["is_new_customer"]].groupby("Platform").agg(
        New_Customers=("is_new_customer", "count")
    ).reset_index()
    st.dataframe(new_cust_summary, use_container_width=True)
else:
    st.warning("Please upload a valid Shopify CSV to begin.")
