FROM quay.io/astronomer/astro-runtime:10.8.0

USER root
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"
USER astro


ENV TRANSFORMERS_CACHE=/usr/local/airflow/.cache/huggingface

# Dockerfile
ENV AIRFLOW__WEBSERVER__WEB_SERVER_WORKER_TIMEOUT=600

# .env (or set in Dockerfile)
#AIRFLOW__SECRETS__BACKEND=airflow.providers.amazon.aws.secrets.secrets_manager.SecretsManagerBackend
#AIRFLOW__SECRETS__BACKEND_KWARGS={"connections_prefix": "airflow/connections", "variables_prefix": "airflow/variables", "region_name": "us-east-1"}
## Remove a DAG from metadata/UI (does not touch your code)
