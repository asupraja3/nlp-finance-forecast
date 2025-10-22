from __future__ import annotations
import pendulum
from airflow.decorators import task
from airflow.models.dag import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.sensors.filesystem import FileSensor
from airflow.utils.trigger_rule import TriggerRule

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
    5.  **Branch**: Checks if model training is requested via DAG run configuration.
    6.A. **Train**: (If requested) Trains a new PySpark MLlib model and logs results.
    6.B. **Skip**: (If not requested) Skips the training step.
    7.  **Complete**: Final step to signify a successful run.
    
    ### How to Trigger a Training Run:
    
    To run the model training (Step 6.A.), you must manually trigger the DAG
    using the "Trigger DAG w/ config" button and provide the following JSON:
    
    ```json
    {"train_model": true}
    ```
    
    If run on its daily schedule or triggered manually without this config,
    the pipeline will default to skipping the training step.
    """,
) as dag:

    # --- Task 1: Ingest Stock Data ---
    ingest_stock_data = BashOperator(
        task_id="ingest_stock_data",
        bash_command="python /opt/airflow/src/ingest.py",
        doc_md="Fetches the latest daily stock prices into the /raw landing zone.",
    )

    # --- Task 2: Wait for News Data ---
    wait_for_news_data = FileSensor(
        task_id="wait_for_news_data",
        filepath="/opt/airflow/data/raw/news_data.csv",
        poke_interval=30,
        timeout=600,
        mode="poke",
        doc_md="Waits for the daily 'news_data.csv' file to land in the /raw directory."
    )

    # --- Task 3: Stage Raw Files ---
    stage_raw_files = BashOperator(
        task_id="stage_raw_files",
        bash_command="""
            mkdir -p /opt/airflow/data/pre-processed && \
            cp /opt/airflow/data/raw/*.csv /opt/airflow/data/pre-processed/
        """,
        doc_md="Copies raw data from the landing zone (/raw) to the staging area (/pre-processed).",
    )

    # --- Task 4: Process and Feature Engineer ---
    process_data = BashOperator(
        task_id="process_and_feature_engineer",
        bash_command="python /opt/airflow/src/process.py",
        doc_md="Consumes staged data, runs PySpark sentiment/feature job, and saves to /processed.",
    )

    # --- Task 5: Branching Logic ---
    # This task uses the @task.branch decorator to create a conditional branch.
    # It checks the DAG's run configuration for a key named 'train_model'.
    @task.branch(task_id="decide_training_path")
    def decide_training_path(dag_run=None):
        """
        Checks the DAG run configuration to decide which path to take.
        If `{"train_model": true}` is passed in the config, it runs training.
        Otherwise, it skips.
        """
        run_conf = dag_run.conf if dag_run else {}
        train_flag = run_conf.get('train_model', False) # Default to False

        if train_flag:
            return "train_prediction_model" # Task ID of the "Yes" branch
        else:
            return "skip_model_training" # Task ID of the "No" branch

    # Call the branching task function
    branch_op = decide_training_path()

    # --- Task 6.A: Train Model (The "Yes" path) ---
    train_model = BashOperator(
        task_id="train_prediction_model",
        bash_command="python /opt/airflow/src/train.py",
        doc_md="Trains a model using the final processed data and logs it with MLflow.",
    )

    # --- Task 6.B: Skip Training (The "No" path) ---
    # This is an EmptyOperator, which does nothing. It's a placeholder
    # to make the DAG's "No" path explicit and clear.
    skip_training = EmptyOperator(
        task_id="skip_model_training"
    )

    # --- Task 7: Pipeline Complete ---
    # This final task will run after *either* the 'train_model' or
    # 'skip_model_training' task finishes.
    # The `trigger_rule` is crucial: it ensures this task runs as long
    # as one of the upstream branches (train or skip) completes successfully.
    pipeline_complete = EmptyOperator(
        task_id="pipeline_complete",
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS
    )


    # --- Task Dependencies ---
    # 1. Ingest and wait for files in parallel.
    # 2. When both are done, stage the files.
    # 3. When staging is done, process the data.
    # 4. When processing is done, run the branching logic.
    # 5. The branching logic will trigger *either* train_model *or* skip_training.
    # 6. When the selected branch is complete, mark the pipeline as complete.

    [ingest_stock_data, wait_for_news_data] >> stage_raw_files >> process_data

    process_data >> branch_op >> [train_model, skip_training]

    train_model >> pipeline_complete
    skip_training >> pipeline_complete