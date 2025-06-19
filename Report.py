import streamlit as st
import pandas as pd

# Set up page config
st.set_page_config(page_title="ASIN Suppression Dashboard", layout="wide")

# Sidebar
st.sidebar.title("📊 ASIN Suppression Filter")
st.sidebar.markdown("Shows ASINs suppressed for more than 7 consecutive days.")

# Title and description
st.title("🚫 Suppressed ASINs Report")
st.markdown(
    """
    This dashboard highlights ASINs that were suppressed for **more than 7 consecutive days**  
    based on the uploaded suppression Excel file.
    """
)

# Upload Excel file
uploaded_file = st.file_uploader("📤 Upload Suppression Excel File", type=["xlsx"])
if uploaded_file:
    # Read the Excel file
    df = pd.read_excel(uploaded_file)

    # Identify date columns only (we assume the first 3 are: ASIN, SKU, Total Suppressed Day)
    date_columns = [col for col in df.columns if pd.to_datetime(str(col), errors='coerce') is not pd.NaT]

    # Ensure we work only with suppression-relevant columns
    suppression_data = df[['ASIN', 'SKU'] + date_columns]

    # Function to check for suppression > 7 consecutive days
    def has_long_suppression(row, threshold=7):
        try:
            values = row[2:].astype(int).values  # only date columns
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

    # Apply logic to find suppressed ASINs
    suppressed_df = suppression_data[suppression_data.apply(has_long_suppression, axis=1)]

    st.metric("✅ Total ASINs Checked", value=len(df))
    st.metric("🚨 Suppressed ASINs Found", value=len(suppressed_df))

    # Show table
    st.dataframe(suppressed_df, use_container_width=True)

    # CSV Download
    csv = suppressed_df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download Suppressed ASINs", data=csv, file_name="suppressed_asins.csv", mime="text/csv")

else:
    st.info("Please upload an Excel file with suppression data to begin.")
