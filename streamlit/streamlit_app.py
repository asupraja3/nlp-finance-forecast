# --- streamlit_app.py ---
# This is the user-facing dashboard for your project.
# It's the "5. 📊 Update Streamlit App" step.
#
# This script does one simple thing:
# 1. It continuously reads the 'prediction_output.csv' file.
# 2. It displays the prediction in a clean, human-readable way.
#
# How to run this (from your project's root directory):
# 1. Make sure you have streamlit installed: pip install streamlit pandas
# 2. Create a 'streamlit' directory if it doesn't exist: mkdir streamlit
# 3. Save this file as 'streamlit/app.py'
# 4. Run it from the *root* directory: streamlit run streamlit/app.py
#
# Your Airflow DAG saves the file to '/opt/airflow/streamlit/prediction_output.csv'
# When running locally, we'll adjust the path.

import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- Configuration ---
st.set_page_config(
    page_title="AI Stock Predictor",
    page_icon="📈",
    layout="wide"
)

# --- File Path ---
# This is the single "handoff" file between your Airflow pipeline and your dashboard.
# Your 'predict.py' writes to this file.
# Your 'update_streamlit_app' task 'touches' this file.
# This app *reads* from this file.
# PREDICTION_FILE_PATH = r"D:\Work_USA\AIML\Projects\nlp-finance-forecast\streamlit\prediction_output.csv"

from pathlib import Path

# 1) allow override via env (e.g., S3/Blob/HTTP URL in the future)
CSV_ENV = os.getenv("PREDICTION_CSV", "").strip()

# 2) local fallback to a file inside the repo (commit a tiny sample CSV)
DEFAULT_CSV = Path(__file__).parent / "prediction_output.csv"

PREDICTION_FILE_PATH = CSV_ENV if CSV_ENV else str(DEFAULT_CSV)

# --- Function to Load Data ---

# @st.cache_data(ttl=60): This is a "magic" Streamlit function.
# It tells Streamlit to cache (save) the result of this function for 60 seconds.
# After 60 seconds, it will re-run the function, automatically loading
# the new data from your 'prediction_output.csv' file.
# This gives you a near-real-time dashboard.
@st.cache_data(ttl=60)
def load_prediction_data(file_path):
    """
    Loads the latest prediction from the CSV file.
    We add a 'load_time' to show when the cache refreshes.
    """
    print(f"[{datetime.now()}] Attempting to load data from {file_path}...")

    # Check if the file exists
    if not os.path.exists(file_path):
        print("File not found.")
        return None, None

    try:
        # Read the prediction file
        df = pd.read_csv(file_path)

        # Check if the file is empty
        if df.empty:
            print("File is empty.")
            return None, None

        # Get the *most recent* prediction (should be the last row)
        latest_prediction = df.iloc[-1]
        print("Data loaded successfully.")

        # We return the data and the time we loaded it
        return latest_prediction, datetime.now()

    except pd.errors.EmptyDataError:
        print("File is empty (Pandas EmptyDataError).")
        return None, None
    except Exception as e:
        print(f"Error loading data: {e}")
        return None, None


# --- Main Dashboard UI ---
st.title("📈 AI Stock Sentiment Predictor")
st.subheader("Live Prediction from Airflow ML Pipeline")

# --- 1. Load Data ---
data, load_time = load_prediction_data(PREDICTION_FILE_PATH)

# --- 2. Display Prediction ---
if data is not None:
    # Get the values from the loaded data
    prediction_date = data['Date']
    prediction = data['prediction']
    sentiment = data['sentiment_score']

    st.markdown(f"#### Last Prediction for Market Date: `{prediction_date}`")

    # Create two columns for a clean layout
    col1, col2 = st.columns(2)

    # --- Column 1: The Final Prediction ---
    with col1:
        st.markdown("### Model Prediction")
        if prediction == 1.0:
            # Display a "BUY" signal
            st.metric(
                label="Prediction: Price will go UP ⬆️",
                value="Recommendation: BUY",
                delta="Positive Outlook"
            )
        else:
            # Display a "SELL" signal
            st.metric(
                label="Prediction: Price will go DOWN ⬇️",
                value="Recommendation: SELL/HOLD",
                delta="Negative Outlook",
                delta_color="inverse"  # Makes the delta red
            )

    # --- Column 2: The Key Feature ---
    with col2:
        st.markdown("### Key Feature: Sentiment")
        # Display the sentiment score that drove this prediction
        st.metric(
            label="Daily FinBERT Sentiment Score",
            value=f"{sentiment:.4f}"
        )
        st.info("This is the average sentiment score from all news headlines for that day.")

    # --- 3. Display Raw Data ---
    st.subheader("Raw Prediction Output")
    st.write(f"This is the raw data loaded from `{PREDICTION_FILE_PATH}`.")
    # We convert the single row (a Series) to a DataFrame and Transpose it (T)
    # so it's easier to read.
    st.dataframe(data.to_frame().T, use_container_width=True)

else:
    # --- Handle Case: No Data ---
    st.error(f"Prediction file not found or is empty.")
    st.info(
        f"Waiting for the Airflow DAG 'stock_sentiment_training_pipeline' to run and create `{PREDICTION_FILE_PATH}`.")
    st.warning("Once the DAG runs, this page will auto-update within 60 seconds.")

# --- Footer ---
st.caption(f"Page last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
if load_time:
    st.caption(f"Data file loaded at: {load_time.strftime('%Y-%m-%d %H:%M:%S')}")

# Add a manual refresh button
if st.button("Refresh Now"):
    # This clears the cache and re-runs the whole script
    st.cache_data.clear()
    st.rerun()