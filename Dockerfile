# Utiliza una imagen oficial de Python como base
FROM python:3.9-slim

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia los archivos del proyecto al contenedor
COPY . /app

# Instala las dependencias
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Expone el puerto si tu aplicación es web (descomenta si es necesario)
# EXPOSE 8080

# Comando por defecto (puedes cambiarlo o sobrescribirlo en Code Engine)
CMD ["python", "src/pipelines/chicago/people/1_chg_people_scraping.py"] 