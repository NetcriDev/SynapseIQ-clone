import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime

def trigger_airflow_dag(dag_id: str, conf: dict = None):
    url = f"http://localhost:8083/api/v1/dags/{dag_id}/dagRuns"
    response = requests.post(
        url,
        json={"conf": conf or {}, "dag_run_id": f"triggered_by_api_{datetime.now().isoformat()}"},
        auth=HTTPBasicAuth("synapseiq", "SynapseIQ$2025")  # reemplaza con tus credenciales
    )
    if response.status_code != 200:
        raise RuntimeError(f"Error al lanzar DAG: {response.text}")
    return response.json()


#trigger_response = trigger_airflow_dag("incident_services_common", conf={"source": "FastAPI", "date": str(datetime.now())})
