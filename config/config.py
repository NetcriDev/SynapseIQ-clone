import psycopg2
import psycopg2.extras
# DB config
def get_connection():
    return psycopg2.connect(
        dbname="crash_records_001",
        user="synapseiq",
        password="SynapseIQ$2025",
        host="localhost",
        port="5432"
    )