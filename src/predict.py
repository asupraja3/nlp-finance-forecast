# --- src/predict.py ---
# This script is the "Run Inference" step of your workflow.
# It is designed to be executed by your Airflow DAG's 'run_inference' task.
#
# Its job is to:
# 1. Load the pre-trained PipelineModel from the '/models' directory.
# 2. Load the latest features from the '/processed' features.parquet file.
# 3. Apply the model to the latest data to generate a prediction.
# 4. Save this prediction to a single CSV file in the '/streamlit' directory.

import sys
import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import col
from pyspark.ml import PipelineModel  # Note: We load a PipelineModel, not Pipeline


# --- Function 1: Run Inference ---
def run_inference(spark):
    """
    Main function to load the model and run prediction.
    """

    # --- Define File Paths ---
    MODEL_PATH = "/usr/local/airflow/models/stock_predictor_model"
    DATA_PATH = "/usr/local/airflow/data/processed/features.parquet"

    # This is the critical output file your Streamlit app will read
    # and your 'update_streamlit_app' DAG task will 'touch'.
    OUTPUT_PATH = "/usr/local/airflow/streamlit/prediction_output.csv"

    # Ensure the /streamlit directory exists
    os.makedirs("/usr/local/airflow/streamlit", exist_ok=True)

    print(f"Starting inference...")

    # --- 1. Load the Trained Model ---
    try:
        print(f"Loading model from {MODEL_PATH}...")
        # Load the *entire* pipeline (assembler + model)
        # This ensures our new data is processed exactly the same way
        model = PipelineModel.load(MODEL_PATH)
        print("Model loaded successfully.")
    except Exception as e:
        print(f"Error loading model from {MODEL_PATH}: {e}")
        print("Did the 'train.py' script run and save the model?")
        return

    # --- 2. Load the Latest Data ---
    try:
        print(f"Loading latest data from {DATA_PATH}...")
        # We only want to predict for the *most recent day*
        # We order by Date descending and take the top 1.
        latest_data = spark.read.parquet(DATA_PATH) \
            .orderBy(col("Date").desc()) \
            .limit(1)

        if latest_data.count() == 0:
            print("Error: No data found in features.parquet.")
            return

        print("Latest data to predict on:")
        latest_data.show()

    except Exception as e:
        print(f"Error loading data from {DATA_PATH}: {e}")
        return

    # --- 3. Run Inference ---
    # Apply the model to the new data
    # The model's pipeline will automatically:
    # 1. Assemble the 'features' vector
    # 2. Run the Logistic Regression
    # 3. Add 'rawPrediction', 'probability', and 'prediction' columns
    print("Running model.transform() to generate prediction...")
    predictions_df = model.transform(latest_data)

    print("Prediction generated.")

    # --- 4. Format and Save Prediction ---

    # Select only the columns we care about for the Streamlit app
    # 'prediction' is the final 0.0 or 1.0
    output_df = predictions_df.select(
        col("Date"),
        col("Close"),
        col("sentiment_score"),
        col("prediction")
    )

    # --- Real-Time AI Engineer Connection ---
    # Spark is a distributed system, so writing a CSV
    # normally creates a folder with many 'part-0000x' files.
    # A Streamlit app needs *one* simple CSV.
    # The standard "handoff" is to convert the small, final
    # result to a Pandas DataFrame, which can easily write a single file.

    try:
        print(f"Saving prediction to {OUTPUT_PATH}...")

        # Convert the tiny (1-row) Spark DataFrame to a Pandas DataFrame
        prediction_pandas_df = output_df.toPandas()

        # Use Pandas to write to a single, clean CSV file
        prediction_pandas_df.to_csv(OUTPUT_PATH, index=False, header=True)

        print("Prediction saved successfully.")
        print("Output:")
        print(prediction_pandas_df)

    except Exception as e:
        print(f"Error saving prediction to CSV: {e}")


# --- Main execution ---
if __name__ == "__main__":
    try:
        spark = SparkSession.builder \
            .appName("StockModelInference") \
            .master("local[*]") \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.driver.memory", "2g") \
            .config("spark.executor.memory", "2g") \
            .config("spark.sql.shuffle.partitions", "10") \
            .getOrCreate()

        spark.sparkContext.setLogLevel("WARN")
        print("SparkSession created.")

        run_inference(spark)

        spark.stop()
        print("SparkSession stopped.")

    except Exception as e:
        print(f"Error initializing SparkSession: {e}")
        sys.exit(1)