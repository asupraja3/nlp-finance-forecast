import yfinance as yf
import pandas as pd
import os
import logging

# --- Configuration ---
# We are choosing Apple Inc. (AAPL) as our target stock.
# It's a well-known, high-volume stock with plenty of news coverage.
TICKER = "AAPL"
START_DATE = "2015-01-01"
END_DATE = "2024-12-31"

# Define the file paths for saving our raw data.
# Using a structured path like this is a best practice.
RAW_DATA_DIR = r"D:\Work_USA\AIML\Projects\nlp-finance-forecast\data\raw"
STOCK_PRICES_FILE = os.path.join(RAW_DATA_DIR, "stock_prices.csv")
NEWS_DATA_INSTRUCTIONS_FILE = os.path.join(RAW_DATA_DIR, "news_data_readme.txt")

# Setup basic logging to see the script's progress.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fetch_stock_data(ticker, start, end, filepath):
    """
    Downloads historical stock price data from Yahoo Finance and saves it to a CSV file.

    Args:
        ticker (str): The stock ticker symbol.
        start (str): The start date for the data in 'YYYY-MM-DD' format.
        end (str): The end date for the data in 'YYYY-MM-DD' format.
        filepath (str): The path to save the CSV file.
    """
    logging.info(f"Starting download for {ticker} stock data from {start} to {end}.")
    try:
        # Use yfinance to download the data for the specified ticker and date range.
        stock_df = yf.download(ticker, start=start, end=end)

        if stock_df.empty:
            logging.warning(f"No data found for ticker {ticker}. It might be delisted or incorrect.")
            return

        # The index is the date, which is what we need. Let's reset it to a column.
        stock_df.reset_index(inplace=True)

        # Save the DataFrame to the specified CSV file.
        stock_df.to_csv(filepath, index=False)
        logging.info(f"Successfully saved stock data to {filepath}")

    except Exception as e:
        logging.error(f"An error occurred while downloading or saving stock data: {e}")

def create_news_data_instructions(filepath):
    """
    Creates a README file instructing the user on how to get the news data.
    This is necessary because the news dataset requires a manual download from Kaggle.
    """
    instructions = """
    Financial News Data - Manual Download Required
    ===============================================

    This project requires a financial news dataset from Kaggle.
    Due to Kaggle's terms of service, this file cannot be automatically downloaded by the script.

    Instructions:
    1. Go to the following URL: https://www.kaggle.com/datasets/miguelaenlle/financial-news-for-stock-market-prediction
    2. Click the "Download" button. You may need to create a free Kaggle account.
    3. Unzip the downloaded file. You will find a file named 'all-data.csv'.
    4. RENAME 'all-data.csv' to 'news_data.csv'.
    5. PLACE the 'news_data.csv' file inside the 'data/raw/' directory, right next to this README.

    Once 'news_data.csv' is in place, you can proceed with the next steps of the project.
    """
    with open(filepath, 'w') as f:
        f.write(instructions)
    logging.info(f"Created news data instructions file at {filepath}")


if __name__ == "__main__":
    # Ensure the target directory for our raw data exists.
    # The `exist_ok=True` flag means the command won't fail if the directory already exists.
    os.makedirs(RAW_DATA_DIR, exist_ok=True)
    logging.info(f"Ensured that the directory '{RAW_DATA_DIR}' exists.")

    # --- Execute the functions ---
    # 1. Fetch and save the stock price data.
    fetch_stock_data(TICKER, START_DATE, END_DATE, STOCK_PRICES_FILE)

    # 2. Create the instruction file for the manual news data download.
    create_news_data_instructions(NEWS_DATA_INSTRUCTIONS_FILE)

    logging.info("Data acquisition script finished.")
