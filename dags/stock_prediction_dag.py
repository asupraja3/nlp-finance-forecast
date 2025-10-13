from __future__ import annotations
import pendulum
from airflow.models.dag import DAG
from airflow.operators.bash import BashOperator
from airflow.sensors.filesystem import FileSensor

# --- DAG Definition ---
with DAG(
    dag_id="stock_sentiment_training_pipeline",
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    schedule="@daily", # Run once a day
    catchup=False,
    tags=["ml", "stock_prediction", "pyspark"],
    doc_md="""
    ## Stock Sentiment Training Pipeline
    This DAG automates the process of fetching stock data, processing it with news sentiment,
    and training a predictive model.
    """,
) as dag:

    # --- Task Definitions ---

    # Task 1: Run the data ingestion script for stock prices.
    # We use BashOperator to execute our existing Python scripts.
    ingest_stock_data = BashOperator(
        task_id="ingest_stock_data",
        bash_command="python /opt/airflow/src/ingest.py",
        doc_md="Fetches the latest daily stock prices for the target ticker.",
    )

    # Task 2: Wait for the news data file to be present.
    # In a real project, this could be a sensor for an API response or a database entry.
    # Here, it checks if the manually placed file exists before proceeding.
    wait_for_news_data = FileSensor(
        task_id="wait_for_news_data",
        filepath="/opt/airflow/data/raw/news_data.csv",
        poke_interval=30,  # Check every 30 seconds
        timeout=600,       # Fail if the file isn't found in 10 minutes
        mode="poke",
    )

    # --- NEW TASK: Stage Raw Files ---
    # This task simulates moving files from a landing zone (raw) to a
    # staging/pre-processing area where they are ready for consumption.
    stage_raw_files = BashOperator(
        task_id="stage_raw_files",
        # 1. Ensure the target directory exists.
        # 2. Copy the CSV files from /raw to /pre-processed.
        bash_command="""
                mkdir -p /opt/airflow/data/pre-processed && \
                cp /opt/airflow/data/raw/*.csv /opt/airflow/data/pre-processed/
            """,
        doc_md="Copies raw data from the landing zone to the pre-processed staging area.",
    )

    # Task 3: Run the PySpark processing and feature engineering script.
    # This task depends on the first two tasks completing successfully.
    process_data = BashOperator(
        task_id="process_and_feature_engineer",
        bash_command="python /opt/airflow/src/process.py",
        doc_md="Combines stock and news data, applies sentiment analysis, and engineers features using PySpark.",
    )

    # Task 4: Run the model training script.
    # This task uses the processed data to train the model and log it with MLflow.
    train_model = BashOperator(
        task_id="train_prediction_model",
        bash_command="python /opt/airflow/src/train.py",
        doc_md="Trains a classification model using MLlib and logs the experiment with MLflow.",
    )


    # --- Task Dependencies ---
    # Define the order in which the tasks should run.
    # The data ingestion and file sensor can run in parallel.
    # Both must succeed before data processing can begin.

    [ingest_stock_data, wait_for_news_data] >> process_data >> train_model