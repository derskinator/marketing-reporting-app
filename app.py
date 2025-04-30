import streamlit as st
import pandas as pd

st.title("Marketing Attribution & Performance Report")

# --- File Uploads ---
st.sidebar.header("Upload CSVs")
google_file = st.sidebar.file_uploader("Google Ads CSV", type="csv")
meta_file = st.sidebar.file_uploader("Meta Ads CSV", type="csv")
shopify_file = st.sidebar.file_uploader("Shopify Orders CSV", type="csv")

def read_csv(file):
    try:
        return pd.read_csv(file)
    except Exception as e:
        st.error(f"Failed to load file: {e}")
        return None

# Load files
google_df = read_csv(google_file) if google_file else None
meta_df = read_csv(meta_file) if meta_file else None
shopify_df = read_csv(shopify_file) if shopify_file else None

# --- Helper Functions ---
def extract_platform(utm_source):
    if pd.isna(utm_source):
        return "Unknown"
    source = utm_source.lower()
    if "facebook" in source or "meta" in source or "instagram" in source:
        return "Meta"
    elif "google" in source:
        return "Google"
    else:
        return "Other"

def summarize_performance(shopify_df):
    if 'utm_source' not in shopify_df.columns and 'referrer_url' not in shopify_df.columns:
        return pd.DataFrame(columns=["Platform", "Revenue", "New Customers", "Orders"])
    
    utm_source = shopify_df['utm_source'] if 'utm_source' in shopify_df.columns else shopify_df['referrer_url']
    shopify_df['platform'] = utm_source.apply(extract_platform)
    shopify_df['is_new'] = ~shopify_df['customer_id'].duplicated(keep='first')

    summary = shopify_df.groupby('platform').agg(
        Revenue=('total_price', 'sum'),
        New_Customers=('is_new', 'sum'),
        Orders=('id', 'count')
    ).reset_index()

    return summary

def top_ads(shopify_df, ad_df, platform_label):
    if ad_df is None or shopify_df is None:
        return pd.DataFrame(columns=["Ad Name", "Attributed Revenue", "Orders"])
    
    if 'utm_campaign' not in shopify_df.columns or 'campaign' not in ad_df.columns:
        return pd.DataFrame(columns=["Ad Name", "Attributed Revenue", "Orders"])
    
    merged = pd.merge(
        shopify_df,
        ad_df,
        left_on='utm_campaign',
        right_on='campaign',
        how='inner'
    )
    top = merged.groupby('ad_name').agg(
        Attributed_Revenue=('total_price', 'sum'),
        Orders=('id', 'count')
    ).reset_index().sort_values(by='Attributed_Revenue', ascending=False).head(10)
    top['Platform'] = platform_label
    return top

# --- Display Data Previews ---
st.subheader("Preview Uploaded Data")
if google_df is not None:
    st.write("Google Ads", google_df.head())
if meta_df is not None:
    st.write("Meta Ads", meta_df.head())
if shopify_df is not None:
    st.write("Shopify Orders", shopify_df.head())

# --- Report: Shopify Summary ---
if shopify_df is not None:
    st.subheader("Platform Performance Summary")
    perf_summary = summarize_performance(shopify_df)
    st.dataframe(perf_summary)

# --- Report: Top Performing Ads ---
if shopify_df is not None:
    st.subheader("Top Performing Ads (by UTM Campaign Matching)")
    top_meta = top_ads(shopify_df, meta_df, "Meta")
    top_google = top_ads(shopify_df, google_df, "Google")
    combined_top_ads = pd.concat([top_meta, top_google], ignore_index=True)
    st.dataframe(combined_top_ads)

st.markdown("---")
st.info("Upload any combination of Google, Meta, and Shopify CSVs to generate this report.")
