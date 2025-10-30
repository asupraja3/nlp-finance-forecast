# MLOps Pipeline for Financial Analysis

An automated, end-to-end data pipeline that uses financial news sentiment to inform a stock price prediction model. This project is orchestrated with Apache Airflow and runs entirely in a containerized Docker environment for consistency and scalability.

### Pipeline Architecture

The pipeline runs on a daily schedule, moving from raw data ingestion to a final trained model in distinct stages.

```mermaid
graph TD
    %% --- Main Workflow ---
    A["1. Ingest Data<br/>(Stocks & News)"] --> B["2. Process Data<br/>(PySpark + NLP)"];
    B --> C{3. Train Model?};
    
    C -- Yes --> D["Train & Log New Model"];
    C -- No --> E["Load Existing Model"];
    
    D --> F["4. Run Inference"];
    E --> F;
    
    F --> G["5. 📊 Update Streamlit App"];

    %% --- Future Work Loop (Dotted Lines) ---
    F -.-> M(Future work: Monitor for Drift);
    M -.-> C;

```

---

### Tech Stack 🛠️

* **Orchestrator:** Apache Airflow (operators: BashOperator, FileSensor, EmptyOperator; uses pendulum)
* **Environment:** Docker & Astro CLI
* **Data Processing:** Apache Spark (`pyspark`)
* **NLP:** Hugging Face Transformers (FinBERT)
* **ML:** `scikit-learn` & `MLflow`
* **Data Sources:** `yfinance`, `parquet`, `CSV`
* **Dashboard:** `Streamlit`
* **Dev & Test:** PyCharm, Jupyter notebooks, pytest (tests/), Git / GitHub

---

### Airflow DAG
<img width="777" height="403" alt="image" src="https://github.com/user-attachments/assets/d92eaa9b-d286-43ea-bb6c-be93e073089d" />


---

### Streamlit App
**Link:** https://nlp-finance-forecast-jcvsw7mecpiz2u46w4jq7z.streamlit.app/

<img width="1919" height="994" alt="Screenshot 2025-10-30 121341" src="https://github.com/user-attachments/assets/29ffc5dd-f141-449f-bea6-4669a428a9f9" />

---

### How to Run This Project

**Prerequisites:** Docker Desktop & Astro CLI must be installed.

1.  **Clone the repo:** `git clone https://github.com/asupraja3/nlp-finance-forecast.git`
2.  **Navigate to the directory:** `cd nlp-finance-forecast`
3.  **Start the environment:** `astro dev start`

Once running, access the Airflow UI at `http://localhost:8080` (login: `admin`/`admin`).

---

### Future Prospects

* Transition to a real-time streaming architecture with Kafka.
* Implement more advanced time-series models (LSTMs, Transformers).
* Deploy the pipeline to a cloud environment (AWS, GCP, Azure).
* Build a CI/CD pipeline for automated testing and deployment.

  <p align="right"> <img src="https://hackatime-badge.hackclub.com/U091WBXJ59C/nlp-finance-forecast"/>
