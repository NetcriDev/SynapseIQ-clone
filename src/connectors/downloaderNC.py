
import pandas as pd
import requests
import os
from urllib.parse import urlparse
import time
from pathlib import Path

def download_pdfs_from_excel(excel_path, download_folder, delay=0.5):
    """
    Descarga todos los PDFs desde un archivo Excel con campo PDFLINK
    
    Args:
        excel_path (str): Ruta al archivo Excel
        download_folder (str): Carpeta donde guardar los PDFs (path completo)
        delay (float): Pausa entre descargas en segundos
    
    Returns:
        dict: Resumen con estadísticas de descarga
    """
    
    print(f"Leyendo archivo: {excel_path}")
    
    # Leer el archivo Excel
    try:
        df = pd.read_excel(excel_path)
        print(f"Archivo cargado exitosamente - {len(df)} filas encontradas")
    except Exception as e:
        print(f"Error leyendo el archivo: {e}")
        return {"error": str(e)}
    
    # Buscar la columna con enlaces PDF
    pdf_column = None
    possible_columns = ['PDFLINK', 'PdfLink', 'PDF_LINK', 'pdf_link', 'PDFLink']
    
    for col in possible_columns:
        if col in df.columns:
            pdf_column = col
            break
    
    # Si no encuentra por nombre exacto, buscar por contenido
    if not pdf_column:
        for col in df.columns:
            if df[col].astype(str).str.contains('http.*\.pdf', na=False).any():
                pdf_column = col
                break
    
    if not pdf_column:
        print("No se encontró la columna con enlaces PDF")
        print(f"Columnas disponibles: {list(df.columns)}")
        return {"error": "No se encontró columna PDFLINK"}
    
    print(f"Usando columna: {pdf_column}")
    
    # Buscar la columna ReportNumber
    report_column = None
    possible_report_columns = ['ReportNumber', 'REPORTNUMBER', 'reportnumber', 'Report_Number']
    
    for col in possible_report_columns:
        if col in df.columns:
            report_column = col
            break
    
    if not report_column:
        print("No se encontró la columna ReportNumber")
        print(f"Columnas disponibles: {list(df.columns)}")
        return {"error": "No se encontró columna ReportNumber"}
    
    print(f"Usando columna de reportes: {report_column}")
    
    # Filtrar filas con enlaces válidos
    valid_links = df[df[pdf_column].notna() & (df[pdf_column] != '')]
    print(f"🔗 Enlaces PDF encontrados: {len(valid_links)}")
    
    # Crear carpeta de descarga
    Path(download_folder).mkdir(parents=True, exist_ok=True)
    print(f"📁 Guardando en: {os.path.abspath(download_folder)}")
    
    # Contadores
    successful = 0
    failed = 0
    skipped = 0
    
    print("\nIniciando descargas...")
    print("-" * 50)
    
    for idx, row in valid_links.iterrows():
        pdf_url = row[pdf_column]
        
        # Crear nombre del archivo usando solo ReportNumber
        report_number = row[report_column]
        
        # Nombre del archivo: solo ReportNumber.pdf
        filename = f"{report_number}.pdf"
        filename = "".join(c for c in filename if c.isalnum() or c in "._-")
        
        filepath = os.path.join(download_folder, filename)
        
        # Verificar si ya existe
        if os.path.exists(filepath):
            print(f"⏭️  {filename} - Ya existe, saltando...")
            skipped += 1
            continue
        
        try:
            print(f"⬇️  Descargando: {filename}")
            
            # Descargar el archivo
            response = requests.get(pdf_url, timeout=30)
            response.raise_for_status()
            
            # Guardar el archivo
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            successful += 1
            print(f"✅ {filename} - Descargado exitosamente")
            
        except requests.exceptions.RequestException as e:
            failed += 1
            print(f"{filename} - Error: {e}")
        
        except Exception as e:
            failed += 1
            print(f"{filename} - Error inesperado: {e}")
        
        # Pausa entre descargas
        if delay > 0:
            time.sleep(delay)
    
    # Resumen final
    print("\n" + "=" * 50)
    print("RESUMEN DE DESCARGA")
    print("=" * 50)
    print(f"Descargas exitosas: {successful}")
    print(f"Archivos saltados: {skipped}")
    print(f"Descargas fallidas: {failed}")
    print(f"Archivos guardados en: {os.path.abspath(download_folder)}")
    print("¡Proceso completado!")
    
    return {
        "successful": successful,
        "failed": failed,
        "skipped": skipped,
        "total_processed": len(valid_links),
        "download_folder": os.path.abspath(download_folder)
    }

# EJEMPLO DE USO:
# 
# resultado = download_pdfs_from_excel(
#     excel_path="C:/datos/reportes.xlsx",
#     download_folder="C:/descargas/pdfs"
# )
# 
# print(f"Descargados: {resultado['successful']}")

# INSTRUCCIONES:
# 1. Instalar dependencias: pip install pandas requests openpyxl
# 2. Usar la función directamente:
#    download_pdfs_from_excel("ruta/archivo.xlsx", "ruta/destino")



# excel_path = "C:/Users/spss/OneDrive - INGELSI CIA LTDA/Documentos/SynapseIQ/data/NC/NC List UPLD/NC List  4-14-25.xlsx"

# download_folder = "C:/Users/spss/OneDrive - INGELSI CIA LTDA/Documentos/SynapseIQ/data/processed/NC"
# download_pdfs_from_excel(excel_path,download_folder)
# df=pd.read_excel(excel_path)
# csv_name=Path(excel_path).stem
# df.to_csv(rf'{download_folder}/{csv_name}.csv',index=False)
# print(df)