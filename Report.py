import streamlit as st
import pandas as pd
import os
from datetime import datetime

DATA_FILE = "suppression_data.csv"
SUPPRESSION_LOG_FILE = "monthly_suppressed_log.csv"

# --------- Utilities ----------
def normalize_date_str(col):
    try:
        return pd.to_datetime(col).strftime("%Y-%m-%d")
    except:
        return None

def detect_streaks(df, threshold=7):
    date_cols = [col for col in df.columns if pd.to_datetime(str(col), errors='coerce') is not pd.NaT]
    streak_data = df[['ASIN', 'SKU'] + date_cols]

    def has_long_suppression(row):
        try:
            values = row[2:].astype(int).values
        except:
            return False
        count = 0
        for val in values:
            if val == 1:
                count += 1
                if count > threshold:
                    return True
            else:
                count = 0
        return False

    return streak_data[streak_data.apply(has_long_suppression, axis=1)]

def extract_monthly_suppressions(df):
    date_cols = [col for col in df.columns if normalize_date_str(col)]
    rows = []
    for _, row in df.iterrows():
        asin = row['ASIN']
        sku = row['SKU']
        for col in date_cols:
            try:
                if str(row[col]).strip() == "1":
                    rows.append({"ASIN": asin, "SKU": sku, "Suppressed Date": normalize_date_str(col)})
            except:
                continue
    log_df = pd.DataFrame(rows)
    log_df.to_csv(SUPPRESSION_LOG_FILE, index=False)
    return log_df

# --------- UI Setup ----------
st.set_page_config(page_title="ASIN Suppression Tracker", layout="wide")
st.title("🚫 ASIN Suppression Tracker")

col1, col2 = st.columns(2)
with col1:
    uploaded_file = st.file_uploader("📄 Upload Daily Suppression Excel File", type=["xlsx"])
with col2:
    if st.button("🩹 Reset All Data"):
        for file in [DATA_FILE, SUPPRESSION_LOG_FILE]:
            if os.path.exists(file):
                os.remove(file)
        st.success("✅ All stored data has been cleared.")

# --------- Handle Upload ---------
if uploaded_file:
    new_df = pd.read_excel(uploaded_file)
    required_columns = {'ASIN', 'SKU'}
    if not required_columns.issubset(new_df.columns):
        st.error("❌ Uploaded file must contain 'ASIN' and 'SKU' columns.")
        st.stop()

    new_dates = [col for col in new_df.columns if pd.to_datetime(str(col), errors='coerce') is not pd.NaT]
    uploaded_dates = {normalize_date_str(col) for col in new_dates}

    if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
        existing_df = pd.read_csv(DATA_FILE)
        existing_dates = {normalize_date_str(col) for col in existing_df.columns if normalize_date_str(col)}
        overlap = uploaded_dates.intersection(existing_dates)
        if overlap:
            st.warning("⚠️ Date(s) from this upload already exist.")
            st.info(f"🗓️ Overlapping Dates: {', '.join(overlap)}")
            if not st.checkbox("✅ I confirm I still want to upload and store it"):
                st.stop()
        all_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        all_df = new_df

    all_df.to_csv(DATA_FILE, index=False)
    extract_monthly_suppressions(all_df)
    st.success("✅ Data stored and monthly suppression log updated.")
else:
    all_df = pd.read_csv(DATA_FILE) if os.path.exists(DATA_FILE) else pd.DataFrame()

# --------- Filter Section ---------
if not all_df.empty:
    all_dates = [col for col in all_df.columns if normalize_date_str(col)]
    all_dates_dt = [pd.to_datetime(col) for col in all_dates if pd.to_datetime(col, errors='coerce') is not pd.NaT]

    months = sorted({d.strftime("%B") for d in all_dates_dt})
    years = sorted({str(d.year) for d in all_dates_dt})

    with st.expander("🔍 Filters"):
        selected_month = st.selectbox("📅 Month", ["All"] + months)
        selected_year = st.selectbox("📆 Year", ["All"] + years)

        use_range = st.checkbox("📆 Apply Date Range Filter")
        if use_range:
            min_date = min(all_dates_dt)
            max_date = max(all_dates_dt)
            start_date = st.date_input("Start Date", value=min_date, min_value=min_date, max_value=max_date)
            end_date = st.date_input("End Date", value=max_date, min_value=min_date, max_value=max_date)
        else:
            start_date = None
            end_date = None

    filtered_cols = []
    for col in all_df.columns:
        if normalize_date_str(col):
            try:
                d = pd.to_datetime(col)
                if ((selected_month == "All" or d.strftime("%B") == selected_month) and
                    (selected_year == "All" or str(d.year) == selected_year) and
                    (not use_range or (start_date <= d.date() <= end_date))):
                    filtered_cols.append(col)
            except:
                continue

    if filtered_cols:
        temp_df = all_df[['ASIN', 'SKU'] + filtered_cols].copy()
        total_rows = temp_df.shape[0]
        filtered_df = temp_df[temp_df[filtered_cols].apply(lambda row: any(row == 1), axis=1)]
        suppressed_rows = filtered_df.shape[0]
        if not filtered_df.empty:
            st.success("✅ Showing filtered suppression data.")
        else:
            st.warning("⚠️ No ASINs with suppression in this filter.")
    else:
        filtered_df = pd.DataFrame()
        total_rows = 0
        suppressed_rows = 0
        st.warning("⚠️ No matching columns found in filter.")
else:
    filtered_df = pd.DataFrame()
    total_rows = 0
    suppressed_rows = 0

# --------- Alerts & Downloads ---------
if not filtered_df.empty:
    alert_df = detect_streaks(filtered_df)
    st.metric("📦 Total ASIN Entries (Filtered Range)", total_rows)
    st.metric("📈 Suppressed > 7 Days", len(alert_df))

    st.subheader("🚨 Suppression Alerts")
    st.dataframe(alert_df, use_container_width=True)

    alert_csv = alert_df.to_csv(index=False).encode("utf-8")
    st.download_button("📅 Download Alert Report", alert_csv, "suppressed_alerts.csv", "text/csv")

    with open(DATA_FILE, "rb") as f:
        st.download_button("📁 Download Full Stored Data", f, "suppression_data.csv", "text/csv")

    if os.path.exists(SUPPRESSION_LOG_FILE):
        log_df = pd.read_csv(SUPPRESSION_LOG_FILE)
        st.subheader("📘 Monthly Suppressed ASINs (No Streak Required)")
        st.dataframe(log_df, use_container_width=True)
        log_csv = log_df.to_csv(index=False).encode("utf-8")
        st.download_button("📅 Download Monthly Suppressed Log", log_csv, "monthly_suppressed_log.csv", "text/csv")
else:
    st.info("Upload data to begin or adjust filters.")
