import streamlit as st
import pandas as pd
import os

DATA_FILE = "suppression_data.csv"

def normalize_date_str(col):
    try:
        return pd.to_datetime(col).strftime("%Y-%m-%d")
    except:
        return None

# ---------- Final Merge Logic ----------
def safe_merge(existing_df, new_df):
    if not existing_df.empty:
        existing_df = existing_df.set_index(['ASIN', 'SKU'])
    else:
        existing_df = pd.DataFrame()

    new_df = new_df.set_index(['ASIN', 'SKU'])
    merged_df = new_df.combine_first(existing_df)

    merged_df = merged_df.reset_index()
    merged_df.to_csv(DATA_FILE, index=False)
    return merged_df

# ---------- Detect ASINs Suppressed > 7 Days ----------
def detect_streaks(df, threshold=7):
    date_columns = [col for col in df.columns if pd.to_datetime(str(col), errors='coerce') is not pd.NaT]
    streak_data = df[['ASIN', 'SKU'] + date_columns]

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

    alert_df = streak_data[streak_data.apply(has_long_suppression, axis=1)]
    return alert_df

st.set_page_config(page_title="ASIN Suppression Tracker", layout="wide")
st.title("🚫 ASIN Suppression Tracker")
st.markdown("Upload your daily Excel file. Alerts are generated for ASINs suppressed more than **7 consecutive days**.")

col1, col2 = st.columns(2)
with col1:
    uploaded_file = st.file_uploader("📤 Upload Daily Suppression Excel File", type=["xlsx"])
with col2:
    if st.button("🧹 Reset All Data"):
        if os.path.exists(DATA_FILE):
            try:
                os.remove(DATA_FILE)
                st.success("✅ All stored data has been cleared.")
            except Exception as e:
                st.error(f"❌ Failed to delete data: {e}")
        else:
            st.info("ℹ️ No stored data found.")

if uploaded_file:
    new_df = pd.read_excel(uploaded_file)
    new_dates = [col for col in new_df.columns if pd.to_datetime(str(col), errors='coerce') is not pd.NaT]
    cleaned_df = new_df[['ASIN', 'SKU'] + new_dates]

    if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
        existing_df = pd.read_csv(DATA_FILE)

        existing_dates = {
            normalize_date_str(col) for col in existing_df.columns if normalize_date_str(col)
        }
        uploaded_dates = {
            normalize_date_str(col) for col in new_dates if normalize_date_str(col)
        }

        overlapping_dates = uploaded_dates.intersection(existing_dates)

        if overlapping_dates:
            st.warning("⚠️ Some of the date columns in this upload already exist in the stored data.")
            st.info(f"🗓️ Overlapping Dates: {', '.join(overlapping_dates)}")

            if not st.checkbox("✅ I confirm I want to overwrite these dates"):
                st.stop()

        combined_df = safe_merge(existing_df, cleaned_df)
        st.success("✅ New data merged and saved.")
    else:
        combined_df = safe_merge(pd.DataFrame(), cleaned_df)
        st.success("✅ Data uploaded and saved.")

    alert_df = detect_streaks(combined_df)
    st.metric("📦 Total ASINs Tracked", len(combined_df))
    st.metric("🚨 ASINs Suppressed > 7 Days", len(alert_df))

    st.subheader("🚨 Suppression Alerts")
    st.dataframe(alert_df, use_container_width=True)

    alert_csv = alert_df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download Alert Report", data=alert_csv, file_name="suppressed_asins_alerts.csv", mime="text/csv")

    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "rb") as f:
            st.download_button(
                label="📁 Download Full Stored Dataset (All Uploads)",
                data=f,
                file_name="all_uploaded_asin_data.csv",
                mime="text/csv"
            )
else:
    st.info("Please upload today's Excel file to begin.")
