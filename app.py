import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Ad Attribution & ROAS Dashboard", layout="wide")
st.title("📊 ROAS Report by Platform and Ad")

# File uploads
with st.sidebar:
    st.header("📁 Upload Your CSVs")
    shopify_file = st.file_uploader("🛒 Shopify Orders CSV", type="csv")
    meta_file = st.file_uploader("📘 Meta Ads CSV", type="csv")
    google_file = st.file_uploader("🔍 Google Ads CSV", type="csv")

# Load Shopify data
def load_shopify(file):
    try:
        df = pd.read_csv(file, quotechar='"', skiprows=[1], skip_blank_lines=True)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Shopify CSV Error: {e}")
        return pd.DataFrame()

# Load Meta Ads data
def load_meta(file):
    try:
        df = pd.read_csv(file)
        df = df.rename(columns={"Ad name": "ad_name", "Amount spent (USD)": "spend"})
        df["Platform"] = "Meta Ads"
        return df[["ad_name", "spend", "Platform"]]
    except Exception as e:
        st.error(f"Meta CSV Error: {e}")
        return pd.DataFrame()

# Load Google Ads using only Total: Account row
def load_google_fixed(file):
    try:
        lines = file.getvalue().decode("utf-8").splitlines()
        trimmed = "\n".join(lines[2:])  # Skip title and date range
        df = pd.read_csv(io.StringIO(trimmed), delimiter=",")
        df.columns = df.columns.str.strip()

        total_row = df[df["Campaign status"].str.strip() == "Total: Account"]
        if total_row.empty:
            raise ValueError("Missing 'Total: Account' row in Google Ads report")

        spend = total_row["Cost"].astype(float).values[0]
        return pd.DataFrame([{
            "ad_name": "Total Account Spend",
            "spend": spend,
            "Platform": "Google Ads"
        }])
    except Exception as e:
        st.error(f"Google CSV processing failed: {e}")
        return pd.DataFrame()

# Platform tagging logic (final fix)
def identify_platform(row):
    src = str(row.get("Order UTM source", "")).lower()
    med = str(row.get("Order UTM medium", "")).lower()
    ref = str(row.get("Order referrer name", "")).lower()

    if src == "google" and med == "ad":
        return "Google Ads"
    elif ref in ["facebook", "instagram"] or src in ["fb", "ig", "facebook", "instagram"]:
        return "Meta Ads"
    else:
        return "Other"

# ROAS by platform
def platform_summary(shopify_df, spend_df):
    shopify_df["Platform"] = shopify_df.apply(identify_platform, axis=1)
    revenue = shopify_df[shopify_df["Platform"].isin(["Google Ads", "Meta Ads"])].groupby("Platform").agg(
        Orders=("Orders", "sum"),
        Revenue=("Total sales", "sum")
    ).reset_index()
    spend = spend_df.groupby("Platform").agg(Spend=("spend", "sum")).reset_index()
    summary = pd.merge(revenue, spend, on="Platform", how="inner")
    summary["ROAS"] = summary["Revenue"] / summary["Spend"]
    return summary

# ROAS by ad
def ad_summary(shopify_df, spend_df):
    shopify_df["Platform"] = shopify_df.apply(identify_platform, axis=1)
    shopify_df = shopify_df.rename(columns={"Order UTM campaign": "ad_name"})
    sales = shopify_df[shopify_df["Platform"].isin(["Google Ads", "Meta Ads"])].groupby(["Platform", "ad_name"]).agg(
        Orders=("Orders", "sum"),
        Revenue=("Total sales", "sum")
    ).reset_index()
    merged = pd.merge(sales, spend_df, on=["Platform", "ad_name"], how="inner")
    merged["ROAS"] = merged["Revenue"] / merged["spend"]
    return merged

# Load + combine
shopify_df = load_shopify(shopify_file) if shopify_file else pd.DataFrame()
meta_df = load_meta(meta_file) if meta_file else pd.DataFrame()
google_df = load_google_fixed(google_file) if google_file else pd.DataFrame()
spend_df = pd.concat([meta_df, google_df], ignore_index=True)

# Output
if not shopify_df.empty and not spend_df.empty:
    st.subheader("📊 ROAS by Platform")
    platform_df = platform_summary(shopify_df, spend_df)
    st.dataframe(platform_df, use_container_width=True)

    st.subheader("📣 ROAS by Ad Campaign")
    ad_df = ad_summary(shopify_df, spend_df)
    st.dataframe(ad_df, use_container_width=True)
else:
    st.warning("Upload both Shopify and at least one ad platform CSV to see ROAS reporting.")

