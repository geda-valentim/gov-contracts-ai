FROM ghcr.io/mlflow/mlflow:v2.10.0

# Install PostgreSQL client library
RUN pip install psycopg2-binary

# Expose MLflow port
EXPOSE 5000

# Default command (will be overridden by docker-compose)
CMD ["mlflow", "server", "--host", "0.0.0.0", "--port", "5000"]
