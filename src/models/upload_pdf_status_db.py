from sqlalchemy import (
    create_engine, 
    Column, 
    Integer, 
    String,
    DateTime, 
    Enum, 
    func
)

from sqlalchemy.orm import sessionmaker, declarative_base

# Configuración de conexión a PostgreSQL
DATABASE_URL = "postgresql+psycopg2://synapseiq:SynapseIQ$2025@localhost:5432/crash_records_001"

# Base declarativa
Base = declarative_base()

# Modelo de tabla
class ReportFile(Base):
    __tablename__ = "upload_pdf_status"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_name = Column(String(255), nullable=True)
    agency = Column(String(255), nullable=True)
    report_number = Column(String(100), nullable=True)
    website = Column(String(255), nullable=True)
    state = Column(String(50), nullable=True)
    city = Column(String(100), nullable=True)
    number_passagers = Column(Integer, nullable=True)

    # Auditoría
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(100), nullable=True)
    updated_by = Column(String(100), nullable=True)

    # Estado del procesamiento (sin constraint)
    status = Column(String(20), nullable=True, default="pending")

# Crear engine y sesión
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# Crear la tabla si no existe
def create_tables():
    Base.metadata.create_all(bind=engine)
    print("Tabla update_pdf_status creada exitosamente.")

# Entry point
if __name__ == "__main__":
    create_tables()
