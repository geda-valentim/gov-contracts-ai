# 📁 Salvar em: dags/exemplo_01_hello_world.py

from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator


# 🎯 PASSO 1: Criar a função que será executada
def dizer_ola():
    print("👋 Olá, Mundo do Airflow!")
    print("🎉 Meu primeiro DAG está funcionando!")
    return "Sucesso!"


# 🎯 PASSO 2: Definir o DAG
with DAG(
    dag_id="exemplo_01_hello_world",  # ID único (como nome do arquivo)
    description="Meu primeiro DAG",  # Descrição
    start_date=datetime(2024, 1, 1),  # Data de início
    schedule=None,  # Execução manual (sem agendamento)
    catchup=False,  # Não rodar datas passadas
    tags=["exemplo", "iniciante"],  # Tags para organizar
) as dag:
    # 🎯 PASSO 3: Criar a tarefa
    tarefa_ola = PythonOperator(
        task_id="dizer_ola",  # ID único da tarefa
        python_callable=dizer_ola,  # Função a ser executada
    )

# Pronto! DAG criado! 🎊
