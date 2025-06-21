import streamlit as st
import pandas as pd
import os

DATA_FILE = "suppression_data.csv"

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

# --------- Streamlit UI ----------
st.set_page_config(page_title="ASIN Suppression Tracker", layout="wide")
st.title("🚫 ASIN Suppression Tracker (Append-only)")

col1, col2 = st.columns(2)
with col1:
    uploaded_file = st.file_uploader("📤 Upload Daily Suppression Excel File", type=["xlsx"])
with col2:
    if st.button("🧹 Reset All Data"):
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)
            st.success("✅ All stored data has been cleared.")
        else:
            st.info("ℹ️ No data to delete.")

# --------- Handle Upload ---------
if uploaded_file:
    new_df = pd.read_excel(uploaded_file)

    # Check if required columns exist
    required_columns = {'ASIN', 'SKU'}
    if not required_columns.issubset(new_df.columns):
        st.error("❌ Uploaded file must contain 'ASIN' and 'SKU' columns.")
        st.stop()

    # Detect new date columns
    new_dates = [col for col in new_df.columns if pd.to_datetime(str(col), errors='coerce') is not pd.NaT]
    uploaded_dates = {normalize_date_str(col) for col in new_dates}

    if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
        existing_df = pd.read_csv(DATA_FILE)
        existing_dates = {
            normalize_date_str(col) for col in existing_df.columns if normalize_date_str(col)
        }

        overlap = uploaded_dates.intersection(existing_dates)
        if overlap:
            st.warning("⚠️ Date(s) from this upload already exist in stored data.")
            st.info(f"🗓️ Overlapping Dates: {', '.join(overlap)}")
            if not st.checkbox("✅ I confirm I still want to upload and store it"):
                st.stop()

        # Append rows as-is (no merge)
        all_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        all_df = new_df

    all_df.to_csv(DATA_FILE, index=False)
    st.success("✅ Data stored successfully.")
else:
    all_df = pd.read_csv(DATA_FILE) if os.path.exists(DATA_FILE) else pd.DataFrame()

# --------- Filter Section ---------
if not all_df.empty:
    all_dates = [col for col in all_df.columns if normalize_date_str(col)]
    all_dates_dt = [pd.to_datetime(col) for col in all_dates if pd.to_datetime(col, errors='coerce') is not pd.NaT]

    months = sorted({d.strftime("%B") for d in all_dates_dt})
    years = sorted({str(d.year) for d in all_dates_dt})

    with st.expander("🔍 Filter by Month & Year"):
        selected_month = st.selectbox("📅 Month", ["All"] + months)
        selected_year = st.selectbox("📆 Year", ["All"] + years)

    # Determine selected date columns
    filtered_cols = []
    for col in all_df.columns:
        if normalize_date_str(col):
            try:
                d = pd.to_datetime(col)
                if (selected_month == "All" or d.strftime("%B") == selected_month) and \
                   (selected_year == "All" or str(d.year) == selected_year):
                    filtered_cols.append(col)
            except:
                continue

    if filtered_cols:
        filtered_df = all_df[['ASIN', 'SKU'] + filtered_cols]
        st.success(f"✅ Showing data for {selected_month} {selected_year}".strip("All"))
    else:
        filtered_df = pd.DataFrame()
        st.warning("⚠️ No data available for selected Month/Year.")
else:
    filtered_df = pd.DataFrame()

# --------- Alert Detection ---------
if not filtered_df.empty:
    alert_df = detect_streaks(filtered_df)

    st.metric("📦 Total Rows in Filtered Data", len(filtered_df))
    st.metric("🚨 Suppressed > 7 Days", len(alert_df))

    st.subheader("🚨 Suppression Alerts")
    st.dataframe(alert_df, use_container_width=True)

    alert_csv = alert_df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download Alert Report", alert_csv, "suppressed_alerts.csv", "text/csv")

    with open(DATA_FILE, "rb") as f:
        st.download_button("📁 Download Full Dataset", f, "suppression_data.csv", "text/csv")
else:
    st.info("Upload data to begin or adjust filters.")
