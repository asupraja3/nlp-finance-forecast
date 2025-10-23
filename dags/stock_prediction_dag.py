from __future__ import annotations
import pendulum
from airflow.models.dag import DAG
from airflow.operators.bash import BashOperator
from airflow.sensors.filesystem import FileSensor

# --- DAG Definition ---
# This is the main definition of your workflow.
# Airflow will read this file, parse this DAG object, and use it to schedule tasks.
with DAG(
        dag_id="stock_sentiment_training_pipeline",
        start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
        # schedule="@daily": This tells Airflow to run the entire pipeline once per day
        # at midnight UTC. This is perfect for a model that needs to be retrained
        # on the previous day's market data.
        schedule="@daily",
        # catchup=False: If the DAG hasn't run for a few days (e.g., Airflow was
        # turned off), this prevents it from trying to run all the missed
        # daily schedules at once.
        catchup=False,
        tags=["ml", "stock_prediction", "pyspark", "finance"],
        doc_md="""
    ## Stock Sentiment Training Pipeline

    This DAG orchestrates the end-to-end process for the stock price prediction model.
    It performs the following steps:

    1.  **Ingest**: Fetches the latest stock prices from yfinance.
    2.  **Sense**: Waits for the daily financial news file to be manually dropped.
    3.  **Stage**: Copies data from the raw landing zone to a staging area.
    4.  **Process**: Runs a PySpark job to combine data, apply FinBERT sentiment
        analysis, and engineer features.
    5.  **Train**: Trains a PySpark MLlib model and logs results with MLflow.

    This pipeline simulates a real-world batch training process in a financial
    institution, where data from various sources is gathered, processed, and
    used to update predictive models.
    """,
) as dag:
    # --- Task 1: Ingest Stock Data ---
    # This task runs our Python script to download the latest stock prices.
    # In a real-world scenario (like at Citadel), this might be a task that
    # connects to an internal market data warehouse (like Snowflake or a custom DB)
    # and pulls the official end-of-day prices.
    ingest_stock_data = BashOperator(
        task_id="ingest_stock_data",
        # We assume the Airflow instance is running from the root of our project.
        # The paths inside the docker-compose.yml will map our project
        # directory to /opt/airflow, which is why we use this path.
        bash_command="python /opt/airflow/src/ingest.py",
        doc_md="Fetches the latest daily stock prices into the /raw landing zone.",
    )

    # --- Task 2: Wait for News Data ---
    # This task is a "Sensor". It will pause the pipeline and keep checking
    # until the 'news_data.csv' file appears in the /raw directory.
    # This simulates a dependency on an external team or process (e.g., a
    # quantitative research team) that provides a daily news sentiment file.
    wait_for_news_data = FileSensor(
        task_id="wait_for_news_data",
        filepath="/opt/airflow/data/raw/news_data.csv",
        poke_interval=30,  # Check for the file every 30 seconds
        timeout=600,  # Fail the task if the file doesn't appear in 10 minutes
        mode="poke",
        doc_md="Waits for the daily 'news_data.csv' file to land in the /raw directory."
    )

    # --- Task 3: Stage Raw Files ---
    # This task replicates a common ETL pattern: moving data from a
    # "landing zone" (where raw, unmodified files are dropped) to a
    # "staging area" (where the data is ready to be consumed by processing jobs).
    # This decouples ingestion from processing.
    stage_raw_files = BashOperator(
        task_id="stage_raw_files",
        # 1. `mkdir -p`: Creates the staging directory, ignoring errors if it exists.
        # 2. `cp ...`: Copies all CSV files from /raw to /pre-processed.
        #    We use 'cp' (copy) instead of 'mv' (move) so the raw files
        #    are preserved, allowing for easier pipeline reruns on failure.
        bash_command="""
            mkdir -p /opt/airflow/data/pre-processed && \
            cp /opt/airflow/data/raw/*.csv /opt/airflow/data/pre-processed/
        """,
        doc_md="Copies raw data from the landing zone (/raw) to the staging area (/pre-processed).",
    )

    # --- Task 4: Process and Feature Engineer ---
    # This is the main data processing step. It runs our PySpark script.
    # The script `src/process.py` *must* be written to read from
    # '/opt/airflow/data/pre-processed/'
    process_data = BashOperator(
        task_id="process_and_feature_engineer",
        bash_command="python /opt/airflow/src/process.py",
        doc_md="Consumes staged data, runs PySpark sentiment/feature job, and saves to /processed.",
    )

    # --- Task 5: Train Model ---
    # This final task runs the training script. This script reads the
    # feature-engineered data from '/opt/airflow/data/processed/'
    # and logs the resulting model and metrics using MLflow.
    train_model = BashOperator(
        task_id="train_prediction_model",
        bash_command="python /opt/airflow/src/train.py",
        doc_md="Trains a model using the final processed data and logs it with MLflow.",
    )

    # --- Task Dependencies ---
    # This defines the execution order and dependencies for the entire pipeline.
    # Read as: "Run 'ingest_stock_data' and 'wait_for_news_data' in parallel."
    # "Once *both* are complete, run 'stage_raw_files'."
    # "Once 'stage_raw_files' is complete, run 'process_data'."
    # "Once 'process_data' is complete, run 'train_model'."

    [ingest_stock_data, wait_for_news_data] >> stage_raw_files >> process_data >> train_model
