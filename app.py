import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Ad Attribution & ROAS Dashboard", layout="wide")
st.title("\U0001F4CA ROAS Report by Platform and Ad")

# Upload section
with st.sidebar:
    st.header("\U0001F4C1 Upload Your CSVs")
    current_shopify_file = st.file_uploader("🛒 Latest Shopify CSV (Current Month)", type="csv")
    historical_shopify_files = st.file_uploader("📆 Historical Shopify CSVs (Optional)", type="csv", accept_multiple_files=True)
    meta_file = st.file_uploader("\U0001F4D8 Meta Ads CSV", type="csv")
    google_file = st.file_uploader("\U0001F50D Google Ads CSV", type="csv")
    show_comparison = st.checkbox("\U0001F4C6 Show Monthly & Yearly Comparison Table")

# Loaders
def load_shopify(file):
    try:
        df = pd.read_csv(file, quotechar='"', skiprows=[1], skip_blank_lines=True)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Shopify CSV Error: {e}")
        return pd.DataFrame()

def load_historical_shopify(files):
    dfs = []
    for file in files:
        try:
            df = pd.read_csv(file, quotechar='"', skiprows=[1], skip_blank_lines=True)
            df.columns = df.columns.str.strip()
            dfs.append(df)
        except Exception as e:
            st.error(f"Historical Shopify CSV Error: {e}")
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

def load_google_account_total(file):
    try:
        lines = file.getvalue().decode("utf-8").splitlines()
        trimmed = "\n".join(lines[2:])
        df = pd.read_csv(io.StringIO(trimmed), delimiter=",")
        df.columns = df.columns.str.strip()
        total_row = df[df["Campaign status"].str.strip() == "Total: Account"]
        if total_row.empty:
            raise ValueError("Missing 'Total: Account' row")
        spend = pd.to_numeric(total_row["Cost"], errors="coerce").values[0]
        return pd.DataFrame([{ "ad_name": "Account Total", "spend": spend, "Platform": "Google Ads" }])
    except Exception as e:
        st.error(f"Google spend load failed: {e}")
        return pd.DataFrame()

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

def platform_summary(shopify_df, spend_df):
    shopify_df["Platform"] = shopify_df.apply(identify_platform, axis=1)
    filtered = shopify_df[shopify_df["Platform"].isin(["Google Ads", "Meta Ads"])]
    revenue = filtered.groupby("Platform").agg(Orders=("Orders", "sum"), Revenue=("Total sales", "sum")).reset_index()
    spend = spend_df.groupby("Platform").agg(Spend=("spend", "sum")).reset_index()
    summary = pd.merge(revenue, spend, on="Platform", how="inner")
    summary["ROAS"] = summary["Revenue"] / summary["Spend"]
    return summary

def ad_summary(shopify_df, spend_df):
    shopify_df["Platform"] = shopify_df.apply(identify_platform, axis=1)
    shopify_df = shopify_df.rename(columns={"Order UTM campaign": "ad_name"})
    meta_only = shopify_df[shopify_df["Platform"] == "Meta Ads"]
    sales = meta_only.groupby(["Platform", "ad_name"]).agg(Orders=("Orders", "sum"), Revenue=("Total sales", "sum")).reset_index()
    spend = spend_df[spend_df["Platform"] == "Meta Ads"]
    merged = pd.merge(sales, spend, on=["Platform", "ad_name"], how="inner")
    merged["ROAS"] = merged["Revenue"] / merged["spend"]
    return merged

def comparison_table(shopify_df):
    try:
        shopify_df["Customer last order date"] = pd.to_datetime(shopify_df["Customer last order date"], errors="coerce")
        shopify_df["Month"] = shopify_df["Customer last order date"].dt.to_period("M").astype(str)
        shopify_df["Platform"] = shopify_df.apply(identify_platform, axis=1)

        monthly = shopify_df[shopify_df["Platform"].isin(["Google Ads", "Meta Ads"])]\
            .groupby(["Platform", "Month"]).agg(Revenue=("Total sales", "sum")).reset_index()

        monthly["Month"] = pd.to_datetime(monthly["Month"])
        current_month = monthly["Month"].max()
        last_month = current_month - pd.DateOffset(months=1)
        last_year = current_month - pd.DateOffset(years=1)

        compare = monthly[monthly["Month"].isin([current_month, last_month, last_year])]
        pivoted = compare.pivot(index="Platform", columns="Month", values="Revenue").reset_index()
        pivoted.columns.name = None
        return pivoted
    except Exception as e:
        st.error(f"Comparison table error: {e}")
        return pd.DataFrame()

# Load and process
current_shopify_df = load_shopify(current_shopify_file) if current_shopify_file else pd.DataFrame()
historical_shopify_df = load_historical_shopify(historical_shopify_files) if historical_shopify_files else pd.DataFrame()
meta_df = load_meta(meta_file) if meta_file else pd.DataFrame()
google_df = load_google_account_total(google_file) if google_file else pd.DataFrame()
spend_df = pd.concat([meta_df, google_df], ignore_index=True)

if not current_shopify_df.empty and not spend_df.empty:
    st.subheader("\U0001F4CA ROAS by Platform")
    st.dataframe(platform_summary(current_shopify_df, spend_df), use_container_width=True)

    st.subheader("\U0001F4A3 ROAS by Meta Ad Campaign")
    st.dataframe(ad_summary(current_shopify_df, spend_df), use_container_width=True)

    if show_comparison and not historical_shopify_df.empty:
        st.subheader("\U0001F4C6 Monthly & Yearly Revenue Comparison")
        st.dataframe(comparison_table(historical_shopify_df), use_container_width=True)
else:
    st.warning("Upload the current month's Shopify file and at least one ad platform file to generate reports.")
