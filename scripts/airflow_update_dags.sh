#!/bin/bash
# Reserialize Airflow DAGs after code changes
docker exec govcontracts-airflow-scheduler airflow dags reserialize
