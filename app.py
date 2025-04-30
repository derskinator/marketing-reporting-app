def comparison_table(shopify_df):
    try:
        # Drop blank or invalid dates
        shopify_df = shopify_df.dropna(subset=["Customer last order date"])
        shopify_df["Customer last order date"] = pd.to_datetime(shopify_df["Customer last order date"], errors="coerce")
        shopify_df = shopify_df.dropna(subset=["Customer last order date"])

        # Drop invalid revenue rows
        shopify_df["Total sales"] = pd.to_numeric(shopify_df["Total sales"], errors="coerce")
        shopify_df = shopify_df[shopify_df["Total sales"] > 0]

        # Identify platform and assign month
        shopify_df["Platform"] = shopify_df.apply(identify_platform, axis=1)
        shopify_df["Month"] = shopify_df["Customer last order date"].dt.to_period("M").dt.to_timestamp()

        # Filter only Meta and Google Ads
        filtered = shopify_df[shopify_df["Platform"].isin(["Google Ads", "Meta Ads"])]

        # Group and aggregate
        monthly = (
            filtered.groupby(["Platform", "Month"])
            .agg(Revenue=("Total sales", "sum"))
            .sort_values(["Platform", "Month"])
            .reset_index()
        )

        # Limit to only months in your uploads (Mar and Apr 2025)
        allowed_months = pd.to_datetime(["2025-03-01", "2025-04-01"])
        monthly = monthly[monthly["Month"].isin(allowed_months)]

        # Calculate % change
        monthly["MoM % Change"] = (
            monthly.groupby("Platform")["Revenue"].pct_change() * 100
        ).round(2)

        # Clean display
        monthly["Revenue"] = monthly["Revenue"].round(2)
        monthly["Month"] = monthly["Month"].dt.strftime("%Y-%m")

        return monthly

    except Exception as e:
        st.error(f"Comparison table error: {e}")
        return pd.DataFrame()

