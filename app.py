import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Ad Attribution & ROAS Dashboard", layout="wide")
st.title("📊 ROAS Report by Platform and Ad")

# File uploads
with st.sidebar:
    st.header("📁 Upload Your CSVs")
    current_shopify_file = st.file_uploader("🛒 Current Month Shopify CSV", type="csv")
    historical_shopify_files = st.file_uploader("🕰️ Historical Shopify CSVs", type="csv", accept_multiple_files=True)
    meta_file = st.file_uploader("📘 Meta Ads CSV", type="csv")
    google_file = st.file_uploader("🔍 Google Ads CSV", type="csv")
    show_comparison = st.checkbox("📆 Show Monthly Comparison Table")

# Loaders
def load_shopify(file):
    try:
        df = pd.read_csv(file, quotechar='"', skiprows=[1])
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Shopify CSV Error: {e}")
        return pd.DataFrame()

def load_shopify_multiple(files):
    dfs = []
    for file in files:
        try:
            df = pd.read_csv(file, quotechar='"', skiprows=[1])
            df.columns = df.columns.str.strip()
            dfs.append(df)
        except Exception as e:
            st.error(f"Shopify CSV Error: {e}")
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

def load_meta(file):
    try:
        df = pd.read_csv(file)
        df = df.rename(columns={"Ad name": "ad_name", "Amount spent (USD)": "spend"})
        df["Platform"] = "Meta Ads"
        return df[["ad_name", "spend", "Platform"]]
    except Exception as e:
        st.error(f"Meta CSV Error: {e}")
        return pd.DataFrame()

def load_google(file):
    try:
        lines = file.getvalue().decode("utf-8").splitlines()
        trimmed = "\n".join(lines[2:])
        df = pd.read_csv(io.StringIO(trimmed), delimiter=",")
        df.columns = df.columns.str.strip()
        total_row = df[df["Campaign status"].str.strip() == "Total: Account"]
        if total_row.empty:
            raise ValueError("Missing 'Total: Account' row")
        spend = pd.to_numeric(total_row["Cost"], errors="coerce").values[0]
        return pd.DataFrame([{
            "ad_name": "Account Total",
            "spend": spend,
            "Platform": "Google Ads"
        }])
    except Exception as e:
        st.error(f"Google Ads CSV Error: {e}")
        return pd.DataFrame()

# Platform detection
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

# ROAS summary tables
def platform_summary(shopify_df, spend_df):
    shopify_df["Platform"] = shopify_df.apply(identify_platform, axis=1)
    filtered = shopify_df[shopify_df["Platform"].isin(["Google Ads", "Meta Ads"])]
    revenue = filtered.groupby("Platform").agg(
        Orders=("Orders", "sum"),
        Revenue=("Total sales", "sum")
    ).reset_index()
    spend = spend_df.groupby("Platform").agg(Spend=("spend", "sum")).reset_index()
    summary = pd.merge(revenue, spend, on="Platform", how="inner")
    summary["ROAS"] = summary["Revenue"] / summary["Spend"]
    return summary

def ad_summary(shopify_df, spend_df):
    shopify_df["Platform"] = shopify_df.apply(identify_platform, axis=1)
    shopify_df = shopify_df.rename(columns={"Order UTM campaign": "ad_name"})
    meta_only = shopify_df[shopify_df["Platform"] == "Meta Ads"]
    sales = meta_only.groupby(["Platform", "ad_name"]).agg(
        Orders=("Orders", "sum"),
        Revenue=("Total sales", "sum")
    ).reset_index()
    spend = spend_df[spend_df["Platform"] == "Meta Ads"]
    merged = pd.merge(sales, spend, on=["Platform", "ad_name"], how="inner")
    merged["ROAS"] = merged["Revenue"] / merged["spend"]
    return merged

# Final comparison logic
def comparison_table(full_df):
    try:
        full_df = full_df.copy()
        full_df = full_df.dropna(subset=["Customer last order date"])
        full_df["Customer last order date"] = pd.to_datetime(full_df["Customer last order date"], errors="coerce")
        full_df = full_df.dropna(subset=["Customer last order date"])
        full_df["Total sales"] = pd.to_numeric(full_df["Total sales"], errors="coerce")
        full_df = full_df[full_df["Total sales"] > 0]
        full_df["Platform"] = full_df.apply(identify_platform, axis=1)
        full_df["Month"] = full_df["Customer last order date"].dt.to_period("M").dt.to_timestamp()
        filtered = full_df[full_df["Platform"].isin(["Google Ads", "Meta Ads"])]
        monthly = (
            filtered.groupby(["Platform", "Month"])
            .agg(Revenue=("Total sales", "sum"))
            .sort_values(["Platform", "Month"])
            .reset_index()
        )
        monthly["MoM % Change"] = (
            monthly.groupby("Platform")["Revenue"].pct_change() * 100
        ).round(2)
        monthly["Revenue"] = monthly["Revenue"].round(2)
        monthly["Month"] = monthly["Month"].dt.strftime("%Y-%m")
        return monthly
    except Exception as e:
        st.error(f"Comparison table error: {e}")
        return pd.DataFrame()

# Load data
current_shopify_df = load_shopify(current_shopify_file) if current_shopify_file else pd.DataFrame()
historical_shopify_df = load_shopify_multiple(historical_shopify_files) if historical_shopify_files else pd.DataFrame()
meta_df = load_meta(meta_file) if meta_file else pd.DataFrame()
google_df = load_google(google_file) if google_file else pd.DataFrame()
spend_df = pd.concat([meta_df, google_df], ignore_index=True)

# ROAS + Ads (from current month only)
if not current_shopify_df.empty and not spend_df.empty:
    st.subheader("📊 ROAS by Platform")
    st.dataframe(platform_summary(current_shopify_df, spend_df), use_container_width=True)

    st.subheader("📣 ROAS by Meta Ad Campaign")
    st.dataframe(ad_summary(current_shopify_df, spend_df), use_container_width=True)

# Comparison Table (from historical + current merged)
if show_comparison and (not historical_shopify_df.empty or not current_shopify_df.empty):
    full_comparison_df = pd.concat([historical_shopify_df, current_shopify_df], ignore_index=True)
    st.subheader("📆 Monthly Revenue Comparison")
    st.dataframe(comparison_table(full_comparison_df), use_container_width=True)

