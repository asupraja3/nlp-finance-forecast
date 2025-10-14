# MLOps Pipeline for Financial Analysis

An automated, end-to-end data pipeline that uses financial news sentiment to inform a stock price prediction model. This project is orchestrated with Apache Airflow and runs entirely in a containerized Docker environment for consistency and scalability.

### Pipeline Architecture

The pipeline runs on a daily schedule, moving from raw data ingestion to a final trained model in four distinct stages.

```mermaid
graph TD
    subgraph "1. Ingestion"
        A[yfinance Stock Data] --> C{Staging};
        B[FileSensor for News Data] --> C;
    end

    subgraph "2. Staging"
        C --> D[Copy to Pre-processed];
    end

    subgraph "3. Processing"
        D --> E[PySpark Job with Sentiment Analysis];
    end

    %% --- The Decision Point ---
    E --> I{Train Model?};

    subgraph "4a. Training Path"
        I -- Yes --> G[Train scikit-learn Model];
        G --> H[Log New Model to MLflow];
    end

    subgraph "4b. Inference-Only Path"
        I -- No --> J[Load Existing Model from MLflow];
    end

    subgraph "5. Inference & Presentation"
        %% Both paths lead to the inference task, which then updates the dashboard
        H --> K[Run Inference on New Data];
        J --> K;
        K --> L[📊 Update Streamlit App];
        K --> M[Monitor Predictions & Data];
        M --> N{Drift Detected?};
        N -- Yes --> O[Trigger Alert & Flag for Retraining];
        N -- No --> P[End Cycle];
    end
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
