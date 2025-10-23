# --- src/feature_engineering.py ---
# This script is the core "Process Data (PySpark + NLP)" step of your workflow.
# It is designed to be executed by your Airflow DAG's BashOperator.
#
# Its job is to:
# 1. Load the raw stock and news data from the '/pre-processed' directory.
# 2. Clean and transform the data (e.g., fix types, handle junk rows).
# 3. Engineer "technical" features from stock prices (e.g., moving averages).
# 4. Engineer "sentiment" features from news headlines using a FinBERT NLP model.
# 5. Join these two feature sets together by date.
# 6. Save the final, model-ready data to the '/processed' directory.

import sys
import os
from pyspark.sql import SparkSession, Window
from pyspark.sql.functions import (
    col,
    avg,
    lag,
    udf,
    to_date,
    concat_ws,
    regexp_replace,
    coalesce,
    lit
)
from pyspark.sql.types import FloatType, StringType, DoubleType, DateType

# --- Real-Time AI Engineer Connection: Model Loading ---
# In a real-time system at a firm like Citadel, this NLP model would NOT
# be loaded from disk like this. It would be a pre-loaded, microservice
# that the Spark job calls via an API.
# Loading a heavy 'transformers' model inside a Spark UDF is slow
# and inefficient for high-frequency trading.
#
# For our project, we load it directly.
try:
    from transformers import pipeline

    # We initialize the FinBERT sentiment model.
    # This model is specifically trained on financial text.
    print("Loading FinBERT sentiment pipeline...")
    # Using "pipeline" handles all the tokenization and model logic for us.
    sentiment_pipeline = pipeline(
        "sentiment-analysis",
        model="ProsusAI/finbert"
    )
    print("FinBERT model loaded successfully.")
except ImportError:
    print("Error: 'transformers' library not found.")
    print("Please install it in your Airflow environment: pip install transformers")
    sys.exit(1)
except Exception as e:
    print(f"Error loading FinBERT model: {e}")
    print("Ensure an internet connection is available for the first download.")
    sys.exit(1)


# --- Function 1: NLP Sentiment UDF ---
def get_sentiment_score(text_batch):
    """
    Applies the FinBERT model to a batch of text.

    FinBERT returns a list of dictionaries, e.g.:
    [{'label': 'positive', 'score': 0.9}, {'label': 'negative', 'score': 0.05}, ...]

    We'll simplify this to a single score: positive_score - negative_score
    A score of +0.9 means very positive, -0.8 means very negative.
    """
    try:
        results = []
        # Process each text string in the batch (Spark sends data in batches)
        for text in text_batch:
            # Handle empty or null text
            if not text or text.strip() == "":
                results.append(0.0)
                continue

            # Run the sentiment analysis pipeline
            scores = sentiment_pipeline(text)

            # Default to neutral
            sentiment_score = 0.0

            # Sum up the scores based on their label
            for s in scores:
                if s['label'] == 'positive':
                    sentiment_score += s['score']
                elif s['label'] == 'negative':
                    sentiment_score -= s['score']
                # We ignore 'neutral' to make the signal clearer

            results.append(sentiment_score)
        return results
    except Exception as e:
        # On any error, just return a neutral score
        print(f"Error in sentiment UDF: {e}")
        return [0.0] * len(text_batch)


# --- Register the UDF with Spark ---
# We register our Python function as a PySpark User-Defined Function (UDF).
# This allows us to call our Python/FinBERT code on each row of the Spark DataFrame.
# NOTE: Pandas UDFs (vectorized) are much faster, but this is simpler to understand.
sentiment_udf = udf(lambda text: get_sentiment_score([text])[0], FloatType())


# --- Function 2: Main Data Processing ---
def process_data(spark):
    """
    Main function to run the end-to-end data processing pipeline.
    """

    # --- Define File Paths ---
    # These paths are INSIDE the Airflow environment, matching your DAG.
    # We assume the 'stage_raw_files' task already ran.
    #
    # Input paths
    STOCK_DATA_PATH = "/opt/airflow/data/pre-processed/stock_prices.csv"
    NEWS_DATA_PATH = "/opt/airflow/data/pre-processed/news_data.csv"

    # Output path
    OUTPUT_PATH = "/opt/airflow/data/processed/features.parquet"

    print(f"Starting data processing...")
    print(f"Reading stock data from: {STOCK_DATA_PATH}")
    print(f"Reading news data from: {NEWS_DATA_PATH}")

    # --- 1. Load and Clean Stock Data ---
    # Based on our data inspection, we must:
    # 1. Skip the first junk row ('AAPL', 'AAPL', ...)
    # 2. Cast columns from string to their correct types.
    try:
        stock_df = spark.read.option("header", "true").csv(STOCK_DATA_PATH)

        # 1. Filter out the bad header row
        stock_df = stock_df.filter(col("Date") != "AAPL") \
            .filter(col("Date").isNotNull())

        # 2. Cast columns to correct types
        stock_df = stock_df.withColumn("Date", to_date(col("Date"), "yyyy-MM-dd")) \
            .withColumn("Close", col("Close").cast(DoubleType())) \
            .withColumn("High", col("High").cast(DoubleType())) \
            .withColumn("Low", col("Low").cast(DoubleType())) \
            .withColumn("Open", col("Open").cast(DoubleType())) \
            .withColumn("Volume", col("Volume").cast(DoubleType()))

        # Drop any rows that failed casting
        stock_df = stock_df.dropna(subset=["Date", "Close"])

        print("Stock data loaded and cleaned.")
        stock_df.printSchema()

    except Exception as e:
        print(f"Error loading stock data: {e}")
        return

    # --- 2. Load and Clean News Data ---
    # Based on our data inspection, we must:
    # 1. Combine all 25 'TopN' columns into one big string.
    # 2. Clean the byte-string prefixes (e.g., b"..." or b'...')
    # 3. Cast 'Date' column.
    try:
        news_df = spark.read.option("header", "true").csv(NEWS_DATA_PATH)

        # 1. Create a list of the 'TopN' columns
        headline_cols = [f"Top{i}" for i in range(1, 26)]

        # Coalesce each column to handle nulls (replace null with empty string)
        # Then, clean the byte-string prefixes/suffixes
        cleaned_headline_cols = []
        for c in headline_cols:
            # Handle nulls
            coalesced_col = coalesce(col(c), lit(""))
            # Remove b"..." and b'...'
            cleaned_col = regexp_replace(coalesced_col, "^b[\"']", "")
            cleaned_col = regexp_replace(cleaned_col, "[\"']$", "")
            cleaned_headline_cols.append(cleaned_col)

        # 2. Combine all 25 cleaned columns into a single string, separated by a space
        news_df = news_df.withColumn(
            "all_headlines",
            concat_ws(" ", *cleaned_headline_cols)
        )

        # 3. Cast Date and select only the columns we need
        news_df = news_df.withColumn("Date", to_date(col("Date"), "yyyy-MM-dd")) \
            .select("Date", "all_headlines")

        print("News data loaded and cleaned.")
        news_df.printSchema()

    except Exception as e:
        print(f"Error loading news data: {e}")
        return

    # --- 3. Engineer Technical Features ---
    # We'll create two simple features:
    # 1. SMA_5: 5-day Simple Moving Average of the 'Close' price.
    # 2. lag_close_1: Yesterday's 'Close' price.

    # Define a Window. This tells Spark "group by date".
    # This window is just for the lag feature.
    window_spec_orderByDate = Window.orderBy("Date")

    # This window is for the 5-day moving average.
    # It includes the current row and the 4 previous rows.
    window_spec_5day = Window.orderBy("Date").rowsBetween(-4, 0)

    features_df = stock_df.withColumn(
        "SMA_5",
        avg(col("Close")).over(window_spec_5day)
    ).withColumn(
        "lag_close_1",
        lag(col("Close"), 1).over(window_spec_orderByDate)
    )

    print("Technical features engineered.")

    # --- 4. Apply NLP Sentiment Analysis ---
    # Apply our UDF to the 'all_headlines' column
    # This is the most compute-intensive step.
    print("Applying sentiment analysis UDF... (This may take a while)")
    sentiment_df = news_df.withColumn(
        "sentiment_score",
        sentiment_udf(col("all_headlines"))
    ).select("Date", "sentiment_score")

    # The data has multiple headlines per day, but they are already combined.
    # If we had multiple rows per day, we would group by Date and average the sentiment.
    # Our data is 1-row-per-day, so we're good.

    print("Sentiment analysis complete.")

    # --- 5. Join Features and Sentiment ---
    # We'll do a 'left' join:
    # Keep all rows from 'features_df' (stock data)
    # and join any matching 'sentiment_df' (news data) rows.
    final_df = features_df.join(
        sentiment_df,
        on="Date",
        how="left"
    )

    print("Stock features and sentiment features joined.")

    # --- 6. Final Cleaning and Saving ---

    # After the join, days with no news will have 'null' for 'sentiment_score'.
    # We'll fill these with 0.0 (neutral sentiment).
    final_df = final_df.fillna(0.0, subset=["sentiment_score"])

    # The first few rows will have 'null' for 'lag_close_1' and 'SMA_5'
    # (e.g., day 1 has no "yesterday").
    # A model cannot be trained on nulls, so we drop these rows.
    final_df = final_df.dropna()

    # --- Save Output as Parquet ---
    # Parquet is a columnar format, much more efficient for ML than CSV.
    # 'overwrite' mode ensures the job can be re-run.
    try:
        print(f"Saving final features to {OUTPUT_PATH}...")
        final_df.write.mode("overwrite").parquet(OUTPUT_PATH)
        print("Processing complete. Final features saved.")

        print("Final Data Schema:")
        final_df.printSchema()

        print("Example of final data:")
        final_df.show(5)

    except Exception as e:
        print(f"Error saving final data to Parquet: {e}")


# --- Main execution ---
if __name__ == "__main__":

    # --- Function 3: SparkSession Initialization ---
    # This is the entry point for any PySpark application.
    # We get or create a 'SparkSession'.
    try:
        spark = SparkSession.builder \
            .appName("StockFeatureEngineering") \
            .getOrCreate()

        # Set log level to WARN to reduce console spam
        spark.sparkContext.setLogLevel("WARN")

        print("SparkSession created.")

        # Run the main processing logic
        process_data(spark)

        # Stop the SparkSession
        spark.stop()
        print("SparkSession stopped.")

    except Exception as e:
        print(f"Error initializing SparkSession: {e}")
        sys.exit(1)