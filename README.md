# MLOps Pipeline for Financial Analysis

An automated, end-to-end data pipeline that uses financial news sentiment to inform a stock price prediction model. This project is orchestrated with Apache Airflow and runs entirely in a containerized Docker environment for consistency and scalability.

### Pipeline Architecture

The pipeline runs on a daily schedule, moving from raw data ingestion to a final trained model in distinct stages.

```mermaid
graph TD
    %% Define Styles for the Future Work loop
    style M fill:#fff,stroke:#f00,stroke-width:2px,stroke-dasharray: 5 5
    linkStyle 7 stroke-width:2px,fill:none,stroke:red,stroke-dasharray: 3 3
    linkStyle 8 stroke-width:2px,fill:none,stroke:red,stroke-dasharray: 3 3
    
    %% --- Main Workflow ---
    A[1. Ingest Data<br/>(Stocks & News)] --> B[2. Process Data<br/>(PySpark + NLP)];
    B --> C{3. Retrain Model?};
    
    C -- Yes --> D[Train & Log New Model];
    C -- No --> E[Load Existing Model];
    
    D --> F[4. Run Inference];
    E --> F;
    
    F --> G[5. 📊 Update Streamlit App];

    %% --- Future Work Loop (Dotted Lines) ---
    F -.-> M(Monitor for Drift);
    M -.-> C;
```

---

### Tech Stack 🛠️

* **Orchestrator:** Apache Airflow
* **Environment:** Docker & Astro CLI
* **Data Processing:** Apache Spark (`pyspark`)
* **NLP:** Hugging Face Transformers
* **ML:** `scikit-learn` & `MLflow`
* **Data Sources:** `yfinance`
* **Dashboard:** `Streamlit`

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
* Build a CI/CD pipeline for automated testing and deployment..
