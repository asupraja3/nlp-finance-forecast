# This script is the "Train Model" step of your workflow.
# It is designed to be executed by your Airflow DAG's 'train_prediction_model' task.
#
# Its job is to:
# 1. Load the final feature-engineered data from '/processed'.
# 2. Create a binary target variable (label) for our model to predict.
# 3. Assemble features into a vector.
# 4. Split the data into training and testing sets (chronologically).
# 5. Train a PySpark MLlib classification model.
# 6. Evaluate the model and print its performance.
# 7. Save the trained model to the '/models' directory.

import sys
import os
from pyspark.sql import SparkSession, Window
from pyspark.sql.functions import col, lag, lead, when, lit, row_number
from pyspark.ml import Pipeline
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.classification import LogisticRegression
from pyspark.ml.evaluation import BinaryClassificationEvaluator


# --- Function 1: Create Target Variable (Label) ---
def create_label(df):
    """
    Creates the target variable (label) for our model.
    We'll frame this as a classification problem:
    "Will the price be higher tomorrow?" (1 = Yes, 0 = No)
    """
    print("Creating target label...")

    # Define a window to look 'forward' one day
    # We order by Date to ensure 'lead' gets the *next* day's price
    window_spec = Window.orderBy("Date")

    # 1. Get tomorrow's closing price
    df_with_lead = df.withColumn(
        "Next_Day_Close",
        lead(col("Close"), 1).over(window_spec)
    )

    # 2. Create the binary label
    # Label = 1 if Next_Day_Close > current 'Close', otherwise 0
    df_with_label = df_with_lead.withColumn(
        "label",
        when(col("Next_Day_Close") > col("Close"), 1.0).otherwise(0.0)
    )

    # 3. Clean up
    # The last row will have a 'null' Next_Day_Close and label.
    # We must drop this row as we cannot train on it.
    final_df = df_with_label.dropna(subset=["Next_Day_Close"])

    print("Label creation complete. Target column is 'label'.")
    final_df.select("Date", "Close", "Next_Day_Close", "label").show(5)

    return final_df


# --- Function 2: Main Training Logic ---
def train_model(spark):
    """
    Main function to run the end-to-end model training pipeline.
    """

    # --- Define File Paths ---
    INPUT_PATH = "/usr/local/airflow/data/processed/features.parquet"
    MODEL_OUTPUT_PATH = "/usr/local/airflow/models/stock_predictor_model"

    # Ensure the /models directory exists
    # This path is relative to the Airflow worker
    os.makedirs("/usr/local/airflow/models", exist_ok=True)

    print(f"Starting model training...")
    print(f"Loading features from: {INPUT_PATH}")

    # --- 1. Load Processed Data ---
    try:
        features_df = spark.read.parquet(INPUT_PATH)
        features_df = features_df.orderBy("Date")
        print("Processed data loaded successfully.")
    except Exception as e:
        print(f"Error loading processed data from {INPUT_PATH}: {e}")
        print("Did the 'feature_engineering.py' script run successfully?")
        return

    # --- 2. Create Target Variable ---
    labeled_df = create_label(features_df)

    # --- 3. Assemble Features ---
    # PySpark ML models require all feature columns to be in a
    # single vector column.

    # These are the "signals" we created in the last step
    feature_columns = [
        "SMA_5",
        "lag_close_1",
        "sentiment_score",
        "Volume",  # Let's add Volume as a feature too
        "Open",
        "High",
        "Low"
    ]

    print(f"Assembling features: {feature_columns}")

    # VectorAssembler: The "bundler"
    assembler = VectorAssembler(
        inputCols=feature_columns,
        outputCol="features",
        handleInvalid="skip"  # Skip rows with nulls in these features
    )

    # --- 4. Split Data (Chronologically) ---
    # For time-series, we CANNOT do a random split.
    # We must train on the past to predict the future.
    # We'll use an 80/20 split.

    print("Splitting data into train and test sets (80/20 chronological)...")

    # Sort chronologically
    ordered_df = labeled_df.orderBy("Date").withColumn(
        "row_num", row_number().over(Window.orderBy("Date"))
    )

    # Compute cutoff index (80%)
    total_rows = ordered_df.count()
    cut_index = int(total_rows * 0.8)

    train_data = ordered_df.filter(col("row_num") <= cut_index).drop("row_num")
    test_data = ordered_df.filter(col("row_num") > cut_index).drop("row_num")

    print(f"Training data count: {train_data.count()}")
    print(f"Test data count: {test_data.count()}")

    # --- 5. Define Model and Pipeline ---
    # We'll use Logistic Regression for our binary (0/1) classification
    lr = LogisticRegression(
        featuresCol="features",
        labelCol="label",
        maxIter=10,
        regParam=0.1  # Regularization to prevent overfitting
    )

    # A Pipeline chains the assembler and model together.
    # This is best practice: it ensures the same steps
    # are applied to both training and test data.
    pipeline = Pipeline(stages=[assembler, lr])

    # --- 6. Train the Model ---
    print("Training the Logistic Regression model...")
    model = pipeline.fit(train_data)
    print("Model training complete.")

    # --- 7. Evaluate the Model ---
    print("Evaluating model performance on test data...")
    predictions = model.transform(test_data)

    # We use AUC-ROC, a standard metric for classification.
    # 0.5 = random guessing
    # 1.0 = perfect model
    evaluator = BinaryClassificationEvaluator(
        labelCol="label",
        rawPredictionCol="rawPrediction",
        metricName="areaUnderROC"
    )

    auc = evaluator.evaluate(predictions)
    print(f"Model Performance: Test Set AUC (Area Under ROC) = {auc:.4f}")

    # --- Real-Time AI Engineer Connection ---
    # At Citadel, an AUC of 0.55 might be *highly* profitable if traded
    # frequently. An AUC of 0.7+ would be considered extremely strong
    # for a financial prediction model. We are not looking for 0.99;
    # if we got that, it would mean our model is "leaking" future data
    # (e.g., we accidentally included tomorrow's price as a feature).
    if auc > 0.98:
        print("Warning: High AUC! Check for data leakage.")

    # --- 8. Save the Model ---
    try:
        print(f"Saving model to {MODEL_OUTPUT_PATH}...")
        # 'overwrite' lets us re-run the DAG
        model.write().overwrite().save(MODEL_OUTPUT_PATH)
        print("Model saved successfully.")
    except Exception as e:
        print(f"Error saving model: {e}")


# --- Main execution ---
if __name__ == "__main__":
    try:
        spark = SparkSession.builder \
            .appName("StockModelTraining") \
            .getOrCreate()

        spark.sparkContext.setLogLevel("WARN")
        print("SparkSession created.")

        train_model(spark)

        spark.stop()
        print("SparkSession stopped.")

    except Exception as e:
        print(f"Error initializing SparkSession: {e}")
        sys.exit(1)