import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Ad Attribution & ROAS Dashboard", layout="wide")

st.title("📊 Multi-Channel Attribution & ROAS Dashboard")
st.markdown("Upload your **Shopify**, **Google Ads**, and **Meta Ads** CSVs below to generate performance reports by platform.")

# --- File Uploads ---
with st.sidebar:
    st.header("📁 Upload Your CSVs")
    shopify_file = st.file_uploader("🛒 Shopify Orders CSV", type="csv")
    google_file = st.file_uploader("🔍 Google Ads CSV (optional)", type="csv")
    meta_file = st.file_uploader("📘 Meta Ads CSV (optional)", type="csv")

# --- Load Data ---
@st.cache_data
def load_csv(file):
    try:
        return pd.read_csv(file)
    except:
        try:
            return pd.read_csv(file, sep='\t')
        except Exception as e:
            st.error(f"Failed to parse file: {e}")
            return None

shopify_df = load_csv(shopify_file) if shopify_file else None
google_df = load_csv(google_file) if google_file else None
meta_df = load_csv(meta_file) if meta_file else None

# --- Helper Functions ---
def identify_platform(row):
    src = str(row.get("Order UTM source", "")).lower()
    med = str(row.get("Order UTM medium", "")).lower()
    ref = str(row.get("Order referrer name", "")).lower()

    if src == "google" and med == "ad":
        return "Google Ads"
    elif src == "google":
        return "Google Organic"
    elif src in ["facebook", "meta", "instagram"] and med == "ad":
        return "Meta Ads"
    elif ref in ["google", "bing", "yahoo"]:
        return "Search (Organic)"
    elif ref in ["facebook", "instagram"]:
        return "Social (Organic)"
    elif src != "":
        return src.title()
    else:
        return "Other"

def clean_spend_data(df, platform_name):
    if df is None:
        return pd.DataFrame(columns=["campaign", "spend", "ad_name"])
    df.columns = df.columns.str.lower()
    df = df.rename(columns=lambda x: x.strip())
    if "spend" in df.columns and "campaign" in df.columns:
        df["platform"] = platform_name
        return df[["campaign", "spend", "ad_name", "platform"]]
    else:
        return pd.DataFrame(columns=["campaign", "spend", "ad_name", "platform"])

# --- Attribution and Summary ---
if shopify_df is not None:
    st.subheader("📦 Shopify Performance Summary")

    shopify_df["Platform"] = shopify_df.apply(identify_platform, axis=1)

    grouped = shopify_df.groupby("Platform").agg(
        Orders=("Orders", "sum"),
        Sales=("Total sales", "sum")
    ).reset_index()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("🧾 Total Orders", int(shopify_df["Orders"].sum()))
    with col2:
        st.metric("💰 Total Sales", f"${shopify_df['Total sales'].sum():,.2f}")

    st.markdown("### 📈 Sales by Platform")
    fig = px.bar(grouped, x="Platform", y="Sales", text_auto=".2s", color="Platform")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 📊 Orders by Platform")
    fig2 = px.pie(grouped, names="Platform", values="Orders", title="Order Distribution")
    st.plotly_chart(fig2, use_container_width=True)

    st.markdown("### 🧮 Raw Data by Platform")
    st.dataframe(grouped, use_container_width=True)

    # --- ROAS CALCULATION ---
    st.subheader("📊 ROAS by Platform")

    google_spend_df = clean_spend_data(google_df, "Google Ads")
    meta_spend_df = clean_spend_data(meta_df, "Meta Ads")
    spend_df = pd.concat([google_spend_df, meta_spend_df])

    campaign_sales = shopify_df.groupby(["Platform", "Order UTM campaign"]).agg(
        Attributed_Sales=("Total sales", "sum"),
        Orders=("Orders", "sum")
    ).reset_index()

    if not spend_df.empty:
        merged = pd.merge(campaign_sales, spend_df, left_on="Order UTM campaign", right_on="campaign", how="inner")
        merged["ROAS"] = merged["Attributed_Sales"] / merged["spend"]
        merged_summary = merged.groupby("platform").agg(
            Spend=("spend", "sum"),
            Revenue=("Attributed_Sales", "sum"),
            ROAS=("ROAS", "mean")
        ).reset_index()
        st.dataframe(merged_summary)

        st.markdown("### 🔝 Top Performing Ads by ROAS")
        top_ads = merged.sort_values(by="ROAS", ascending=False)[
            ["ad_name", "platform", "spend", "Attributed_Sales", "ROAS"]
        ].head(10)
        st.dataframe(top_ads, use_container_width=True)
    else:
        st.info("Upload ad spend data for Meta and/or Google to calculate ROAS.")
else:
    st.warning("Please upload a Shopify CSV to begin.")
