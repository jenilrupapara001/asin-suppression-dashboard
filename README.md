# ASIN Suppression Dashboard 📊

This Streamlit dashboard analyzes ASIN suppression data and detects SKUs suppressed for more than 7 consecutive days.

## 🚀 How to Run

1. Clone the repo:

git clone https://github.com/your-username/asin-suppression-dashboard.git


2. Install dependencies:

- pip install -r requirements.txt


3. Run the app:

## 🧾 Input Format

- Upload an Excel file (`.xlsx`) with these columns:
- `ASIN`, `SKU`, followed by date columns (e.g., `2025-05-01`, `2025-05-02`, ...)
- Suppression data should be `0` (not suppressed) or `1` (suppressed)
