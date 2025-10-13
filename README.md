# Automated MLOps Pipeline for Financial News Sentiment Analysis

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
        D --> E[PySpark Job];
        subgraph "Feature Engineering"
            F[Hugging Face for Sentiment Analysis] --> E;
        end
    end

    subgraph "4. Model Training"
        E --> G[scikit-learn Model];
        G --> H[Log with MLflow];
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

---

### How to Run This Project

**Prerequisites:** Docker Desktop & Astro CLI must be installed.

1.  **Clone the repo:** `git clone <your-repo-url>`
2.  **Navigate to the directory:** `cd nlp-finance-forecast`
3.  **Start the environment:** `astro dev start`

Once running, access the Airflow UI at `http://localhost:8080` (login: `admin`/`admin`).

---

### Future Prospects

* Transition to a real-time streaming architecture with Kafka.
* Implement more advanced time-series models (LSTMs, Transformers).
* Deploy the pipeline to a cloud environment (AWS, GCP, Azure).
* Build a CI/CD pipeline for automated testing and deployment..
