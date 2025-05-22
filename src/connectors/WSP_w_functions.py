import re
import os
import sys
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pdfplumber
import numpy as np
from src.utils.logger_config import setup_logger

main_script_path = sys.path[0]
logger = setup_logger("winstonsalem_execution", main_script_path)

# :::::::::::::::::::::::::::::::::: set path ::::::::::::::::::::::::::::::::::

#CAMINHO_BASE = r"D:\GitHub Rel8ed\WebScraping\SynapselQ\WSP website"

# :::::::::::::::::::::::::::::::::: extract driver names ::::::::::::::::::::::::::::::::::

def extrair_nomes_motoristas(texto):
    """Extrai nomes de motoristas de um texto."""
    padrao = r"20VEHICLE\n([A-Z\s'-]+(?:\s[A-Z'-]+){0,3})\nDriver Driver"
    resultado = re.findall(padrao, texto, re.MULTILINE)
    resultado = [res.replace('UNKNOWN UNKNOWN', 'UNKNOWN') for res in resultado]
    nomes_extraidos = []
    for grupo in resultado:
        nomes_extraidos.extend(re.split(r'\s{2,}|\n', grupo.strip()))
    return [nome.strip() for nome in nomes_extraidos if nome.strip()]

def separar_motoristas_por_sobrenome(nomes, sobrenomes):
    """Separa os nomes dos motoristas de acordo com os sobrenomes fornecidos."""
    motoristas = []
    nome_completo = ' '.join(nomes)
    for sobrenome in sobrenomes:
        sobrenome_split = sobrenome.split(';')
        sobrenome_split = [sobr.strip() for sobr in sobrenome_split]
        if all(sobr[0:16] in nome_completo for sobr in sobrenome_split):
            for sobr in sobrenome_split:
                motoristas.append((nome_completo.split(sobr[0:16])[0].strip() + ' ' + sobr).strip())
                nome_completo = sobr.join(nome_completo.split(sobr[0:16])[1:])
    return motoristas

# :::::::::::::::::::::::::::::::::: extract VIN & insurance ::::::::::::::::::::::::::::::::::

def validar_vin(vin):
    """Verifica se um VIN (Vehicle Identification Number) é válido."""
    if len(vin) != 17:
        return False
    invalid_chars = {'I', 'O', 'Q'}
    return all(char.isalnum() and char not in invalid_chars for char in vin)

def corrigir_cidade_estado(city_state, insurances):
    """Corrige a lista de cidades e estados com base na lista de seguros."""
    if len(city_state) > len(insurances):
        return city_state
    content_out = []
    idx_ref = 0
    for insurance in insurances:
        if insurance == '':
            content_out.append('')
        else:
            if idx_ref + 1 <= len(city_state):
                content_out.append(city_state[idx_ref])
                idx_ref += 1
    return content_out

# :::::::::::::::::::::::::::::::::: get data from page ::::::::::::::::::::::::::::::::::

def obter_dados_pagina(url, headers, data=None):
    """Realiza uma requisição POST ou GET e retorna o conteúdo da página."""
    if data:
        response = requests.post(url, headers=headers, data=data)
    else:
        response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.content

def parse_tabela_pagina(html_content):
    """Faz o parsing do HTML e extrai os dados da tabela da página."""
    soup = BeautifulSoup(html_content, 'html.parser')
    trs_table = soup.find("table", class_="ob_gBody").find("tbody").find_all("tr")
    dados = []
    for tr in trs_table:
        tds = tr.find_all("td")
        report = tds[1].find("a").text
        date = tds[2].find("div").find_all("div")[1].text
        driver = tds[3].text
        street = tds[4].text
        url = tds[1].find("a").get("href")
        dados.append([report, date, driver, street, url])
    return dados, soup

def atualizar_viewstate_eventvalidation(soup):
    """Atualiza os valores de __VIEWSTATE e __EVENTVALIDATION."""
    viewstate = soup.find("input", id="__VIEWSTATE").get_attribute_list("value")[0].replace('+', '%2B').replace('/', '%2F').replace('=', '%3D').replace('&', '%26').replace(' ', '%20')
    eventvalidation = soup.find("input", id="__EVENTVALIDATION").get_attribute_list("value")[0].replace('+', '%2B').replace('/', '%2F').replace('=', '%3D').replace('&', '%26').replace(' ', '%20')
    try:
        viewstate_container = soup.find("input", id="ASPxRoundPanel2_grid1_ob_grid1ViewstateContainer").get_attribute_list("value")[0].replace('+', '%2B').replace('/', '%2F').replace('=', '%3D').replace('&', '%26').replace(' ', '%20')
    except AttributeError:
        viewstate_container = None
    return viewstate, eventvalidation, viewstate_container

def obter_total_paginas(soup):
    """Obtém o número total de páginas de resultados."""
    try:
        pages_text = soup.text.split('10 of ')[-1][0:2].replace('\\', '')
        pages = int(pages_text) // 10 + (int(pages_text) % 10 > 0) - 1
    except (IndexError, ValueError):
        pages = 0
    return pages

# :::::::::::::::::::::::::::::::::: download PDF ::::::::::::::::::::::::::::::::::

def baixar_pdf(url_pdf, nome_arquivo, outdata_folder):
    """Baixa um arquivo PDF de uma URL e salva com o nome especificado."""
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9,pt;q=0.8',
        'Connection': 'keep-alive',
        'DNT': '1',
        'If-Modified-Since': 'Tue, 01 Feb 2020 11:48:19 GMT',
        'If-None-Match': '"365065d87a7cdb1:0"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0',
        'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Microsoft Edge";v="132"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    }
    response = requests.get(url_pdf, headers=headers, stream=True)
    caminho_pasta = outdata_folder
    caminho_completo = os.path.join(caminho_pasta, nome_arquivo)
    
    response.raise_for_status()
    with open(caminho_completo, "wb") as pdf_file:
        for chunk in response.iter_content(chunk_size=4096):
            if chunk:
                pdf_file.write(chunk)
    
    print(f"PDF saved as {caminho_completo}!")

# :::::::::::::::::::::::::::::::::: get PDF URL ::::::::::::::::::::::::::::::::::
def obter_url_pdf(url_relatorio):
    """Obtém a URL do arquivo PDF a partir da página do relatório."""
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9,pt;q=0.8',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://winston-salem.ecrash.interplat.com',
        'Referer': url_relatorio,
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    }
    params = {
        'id': url_relatorio.split("id=")[-1],
    }
    data = {
        '__EVENTTARGET': '',
        '__EVENTARGUMENT': '',
        '__VIEWSTATE': '/wEPDwULLTEzNDEwMTk5MDZkZKhdvVrQ8umwjIp00WHWvW0x71Cz3mV+jz8cFgPHLYVY',
        '__VIEWSTATEGENERATOR': '0E95757D',
        'DXScript': '1_42,1_75,1_40,1_57',
        '__CALLBACKID': 'ASPxCallback1',
        '__CALLBACKPARAM': 'c0:',
        '__EVENTVALIDATION': '/wEdAALwSOy1zNsBlN7c9Srenp3RWHVOJnwVPmH5+9jYfGZMnyOnYOWzG6WjtP7ORJz7EE3Dpd3InCEvvC72WY3wjWRA',
    }
    response = requests.post(
        'https://winston-salem.ecrash.interplat.com/ShowReport.aspx',
        params=params,
        headers=headers,
        data=data,
    )
    response.raise_for_status()
    conteudo = str(response.content).split("'data':'")[-1].split("'")[0]
    return "https://winston-salem.ecrash.interplat.com" + conteudo


# :::::::::::::::::::::::::::::::::: extract data from PDF ::::::::::::::::::::::::::::::::::

def extrair_dados_do_pdf(nome_arquivo, sobrenomes_motoristas, outdata_folder):
    """Extrai dados relevantes de um arquivo PDF."""
    caminho_pasta = outdata_folder
    caminho_completo = os.path.join(caminho_pasta, nome_arquivo)

    texto = ''
    nomes_extraidos = []
    try:
        with pdfplumber.open(caminho_completo) as pdf:
            for pagina in pdf.pages:
                pagina_partial = pagina.extract_text()
                texto += pagina_partial
                nomes_extraidos.extend(extrair_nomes_motoristas(pagina_partial))
    except pdfplumber.exceptions.PDFException as e:
        print(f"Erro ao abrir o PDF {nome_arquivo}: {e}")
        return {}, texto  # Retorna dicionário vazio e o texto parcial

    owners = separar_motoristas_por_sobrenome(nomes_extraidos, sobrenomes_motoristas)

    insurance = []
    partes = texto.split("Insurance ")[1:]
    for parte in partes:
        parte = parte.strip()
        if parte:
            insurance_info = parte.split("Company")[0].strip()
            insurance.append(insurance_info if insurance_info else '')
        else:
            insurance.append('')

    cities = []
    states = []
    match = re.search(r"Driver Driver.*?City State Zip", texto, re.DOTALL)
    if match:
        trecho_motoristas = match.group()
        padrao = r"([A-Z\s]+) ([A-Z]{2}) \d{5}(-\d{4})?"
        resultados = re.findall(padrao, trecho_motoristas)
        if not resultados:
            cities.append("")
            states.append("")
        else:
            for cidade, estado, _ in resultados:
                cities.append(cidade.strip())
                states.append(estado)
    cities = corrigir_cidade_estado(cities, insurance)
    states = corrigir_cidade_estado(states, insurance)

    addresses = []
    match_found = re.findall(r'First Middle Last.*?City State Zip', texto, re.DOTALL)
    for partial_content in match_found:
        partial_content = partial_content.split('First Middle Last')[-1].split('City State Zip')[0].strip().split('Address')[1:]
        addresses.extend([content.split('\n')[0].strip() for content in partial_content])

    dob = []
    match_found = re.findall(r'\n.*DOB.*DOB.*\n', texto)
    for partial_content in match_found:
        partial_content = partial_content.split('DOB ')[1:]
        dob.extend([content.strip().split(' ')[0].strip().split('/')[-1].strip() for content in partial_content])

    #get narrative:
    narrative=[]
    match = re.search(r'include pertinent unusual aspects which are not listed elsewhere on the form.*',texto,re.DOTALL)
    if match:
        narrative=[match[0].replace('include pertinent unusual aspects which are not listed elsewhere on the form','').strip().strip(')').split('ADDITIONAL PROPERTY DAMAGE')[0].strip()]

    vins = []
    vin_parts = texto.split("VIN ")
    for part in vin_parts[1:]:
        part = part.strip()
        if part:
            vin = part.split()[0].strip()
            if vin and validar_vin(vin):
                vins.append(vin)

    policies = []
    if "Policy #" in texto:
        policy_parts = texto.split("Policy #")
        for part in policy_parts[1:]:
            part = part.strip()
            if part:
                policy = part.partition("Policy #")[2].strip()
                policy = part.partition("20 COMMERCIAL")[0].strip()
                if policy != "20":
                    policies.append(policy)
                else:
                    policies.append('N/A')
            else:
                policies.append('N/A')

    cost = []
    if "eated $" in texto:
        cost_parts = texto.split("eated $")
        for part in cost_parts[1:]:
            part = part.strip()
            if part:
                costs = part.partition("eated $")[2].strip()
                costs = part.partition("Insurance")[0].strip()
                if costs:
                    cost.append(costs)
                else:
                    cost.append('')
            else:
                cost.append('')

    return {
        "owners": owners,
        "insurance": insurance,
        "vins": vins,
        "policies": policies,
        "cities": cities,
        "states": states,
        "addresses": addresses,
        "dob": dob,
        "costs": cost,
        "narrative": narrative,
    }, texto

# :::::::::::::::::::::::::::::::::: create dataframe & manage colected info ::::::::::::::::::::::::::::::::::

def criar_dataframe(data):
    """Cria um DataFrame pandas com os dados fornecidos."""
    df = pd.DataFrame(data)
    cols_to_explode = ["DRIVERS", "Insurances", "VINs", "Policies", "Cities", "States", "STREET", "DOB", "Costs", "Narrative"]
    max_len = df[cols_to_explode].applymap(len).max(axis=1)
    for col in cols_to_explode:
        df[col] = df.apply(lambda row: row[col] + [None] * (max_len[row.name] - len(row[col])), axis=1)

    df_expanded = df.explode(cols_to_explode, ignore_index=True)
    df_expanded.rename(columns={"DRIVERS": "Driver", "Insurances": "Insurance", "VINs": "VIN", "Policies": "Policy",
                                "Cities": "City", "States": "State", "DOB": "Date of Birth", "STREET": "Address", "Costs": "Costs", "Narrative": "Narrative"}, inplace=True)
    df_expanded.fillna("", inplace=True)

    # Remove o sufixo 'Insurance' dos nomes de seguradora, se necessário
    df_expanded['Insurance'] = df_expanded['Insurance'].apply(lambda x: x[:-9].strip() if x.strip().endswith('Insurance') else x)

    # Remove o prefixo 'UNKNOWN' (seguido ou não de espaço) do início do nome do driver
    df_expanded['Driver'] = df_expanded['Driver'].astype(str).str.strip()
    df_expanded['Driver'] = df_expanded['Driver'].str.replace(r'^UNKNOWN\s*', '', case=False, regex=True).str.strip()

    # Remove linhas com Driver vazio ou só com espaços
    df_expanded = df_expanded[df_expanded['Driver'].str.strip() != ""]


    # Remove registros totalmente vazios nas colunas críticas
    df_expanded.replace("", np.nan, inplace=True)
    df_expanded = df_expanded.dropna(subset=['Driver', 'Insurance', 'VIN', 'City', 'State'], how='all')
    df_expanded.fillna("", inplace=True)

    # Ordena e remove duplicatas
    df_expanded.sort_values(by=["REPORT", "Driver"], inplace=True)
    df_expanded.drop_duplicates(subset=["REPORT", "Driver"], keep='first', inplace=True)

    # Trata data de nascimento e idade
    df_expanded['Date of Birth'] = df_expanded['Date of Birth'].apply(lambda x: '' if len(x) < 4 else x)
    df_expanded['Age'] = df_expanded['Date of Birth'].apply(lambda x: datetime.now().year - int(x) if x.isdigit() and len(x) == 4 else '')

    # Trata custos
    df_expanded['Costs'] = df_expanded['Costs'].str.split(' 43 ').str[0].str.replace(",", "").str.replace(".00", "").str.strip()
    df_expanded['Costs'] = pd.to_numeric(df_expanded['Costs'], errors='coerce').fillna(0).astype(int)

    def classify_severity(cost):
        if pd.isna(cost):
            return "Low"
        elif cost < 1500:
            return "Low"
        elif 1500 <= cost < 5000:
            return "High"
        elif 5000 <= cost < 10000:
            return "Severe"
        else:
            return "Critical"

    df_expanded['Severity'] = df_expanded['Costs'].apply(classify_severity)
    df_expanded['Costs'] = df_expanded['Costs'].fillna(0).astype(int)

    return mover_para_ultima_coluna(df_expanded, "Costs")


def mover_para_ultima_coluna(df, coluna):
    """Move uma coluna especificada para a última posição do DataFrame."""
    if coluna in df.columns:
        colunas = [c for c in df.columns if c != coluna] + [coluna]
        return df[colunas]
    else:
        return df

# :::::::::::::::::::::::::::::::::: save dataframe to CSV ::::::::::::::::::::::::::::::::::

def salvar_dataframe_csv(df, nome_arquivo, outdata_folder):
    """Salva o DataFrame em um arquivo CSV no diretório especificado."""
    caminho_pasta = outdata_folder
    caminho_completo = os.path.join(caminho_pasta, nome_arquivo)
    df.to_csv(caminho_completo, index=False)

    with open(outdata_folder + "/last_csv_path.txt", "w") as f:
        f.write(caminho_completo + "\n")

    print(f"Arquivo salvo como {caminho_completo}!")


# :::::::::::::::::::::::::::::::::: main function ::::::::::::::::::::::::::::::::::

def pipeline_winstonsalem(outdata_folder):
    """
    Execute a pipeline to scrape data from the Winston-Salem website.

    Args:
        outdata_folder (str): The folder where the output files (pdfs) will be saved.
    
    Returns:
        None 
    """

    os.makedirs(outdata_folder, exist_ok=True)

    days = 1
    desired_date = datetime.now() - timedelta(days)
    format1 = desired_date.strftime('%Y.%m.%d')
    format2 = desired_date.strftime('%m/%d/%Y')
    first_day_of_month = datetime.now().replace(day=1).strftime('%Y.%m.%d')
    caminho_base = outdata_folder

    viewstate='/wEPDwUJNTkyNDI3NTY2D2QWAgIDD2QWAgIDD2QWCGYPZBYCZg9kFgJmDw8WAh4EVGV4dAVGV2VsY29tZSB0byBXaW5zdG9uLVNhbGVtIFBvbGljZSBEZXBhcnRtZW50J3M8YnIvPkNyYXNoIFJlcG9ydCBEYXRhYmFzZWRkAgEPDxYCHgdWaXNpYmxlaGRkAgIPZBYCZg9kFgJmD2QWAmYPZBYCZg9kFgJmD2QWAmYPZBYCZg9kFgICAg9kFgICAQ9kFgJmD2QWAgIBD2QWBmYPZBYEAgEPZBYCZg8PFgIfAGVkZAIDD2QWBGYPDxYCHwBlZGQCAw8WBh4MU2VsZWN0ZWREYXRlZB4KRGF0ZUZvcm1hdAUKTU0vZGQveXl5eR4NQ2FsZW5kYXJJdGVtcwUMPGNhbGVuZGFyIC8+ZAIBD2QWBAIBD2QWAmYPDxYCHwBlZGQCAw9kFgJmDw8WAh8AZWRkAgMPDxYCHwFnZBYCZg9kFgJmDw8WBB8ABYwBVG8gcmVjZWl2ZSBhbiBlbGVjdHJvbmljIGNvcHkgb2YgYSBXaW5zdG9uLVNhbGVtIFBvbGljZSBEZXBhcnRtZW50IENyYXNoIFJlcG9ydCw8YnIvPnBsZWFzZSBzZWFyY2ggdXNpbmcgYXQgbGVhc3Qgb25lIG9mIHRoZSBhYm92ZSBjcml0ZXJpYS4fAWdkZAIDD2QWAmYPZBYCZg9kFgJmD2QWAmYPZBYCZg9kFgJmD2QWAmYPZBYCAgIPZBYCAgEPZBYCZg9kFgICAQ9kFgJmDzwrAAoBAA8WAh4LRm9sZGVyU3R5bGUFHC9TdHlsZXMvZ3JhbmRfZ3JheS9PYm91dEdyaWRkZBgBBR5fX0NvbnRyb2xzUmVxdWlyZVBvc3RCYWNrS2V5X18WAwUVQVNQeFJvdW5kUGFuZWwyJGdyaWQxBRhBU1B4Um91bmRQYW5lbDEkaW1nQ2xlYXIFGUFTUHhSb3VuZFBhbmVsMSRDYWxlbmRhcjHpftIgY0nTcB2cZR0DZcCDlzBjZx/42/kW4Vu/EuQh9g=='
    eventvalidation = '/wEdAATRou6MHqSWkBDZQ7SCXAv3PIMmlrdlpXESQnOS4mHW+QFkT5n3l3TDiP1aCzZXk2iTHpfAQzQZ2fZHXAwYa9/JLgIfiyr04Ed69IzuiKamOI6O3qXOtz9TSjVvT+VoL08='
    viewstateContainer = ''

    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://winston-salem.ecrash.interplat.com',
        'Referer': 'https://winston-salem.ecrash.interplat.com/SearchReports.aspx',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    }
    data = {
        'h_ASPxRoundPanel1_Calendar1': '' + format1 + ';' + first_day_of_month + '',
        'sd_ASPxRoundPanel1_Calendar1': '',
        '__EVENTTARGET': '',
        '__EVENTARGUMENT': '',
        '__VIEWSTATE': viewstate,
        '__VIEWSTATEGENERATOR': '0C6A3359',
        '__EVENTVALIDATION': eventvalidation,
        'ASPxRoundPanel1$txtLocalUse': '',
        'ASPxRoundPanel1$txtDate': '' + format2 + '',
        'ASPxRoundPanel1$txtLastName': '',
        'ASPxRoundPanel1$txtRoadName': '',
        'ASPxRoundPanel1$btnSearch': 'Search',
        'DXScript': '1_42',
    }
    response = requests.post(
        'https://winston-salem.ecrash.interplat.com/SearchReports.aspx',
        headers=headers,
        data=data,
    )

    soup = BeautifulSoup(response.content, 'html.parser')
    viewstate, eventvalidation, viewstateContainer = atualizar_viewstate_eventvalidation(soup)

    list_report = []
    list_date = []
    list_driver = []
    list_street = []
    list_url = []

    dados_pagina, soup_pagina = parse_tabela_pagina(response.content)
    for report, date, driver, street, url in dados_pagina:
        list_report.append(report)
        list_date.append(date)
        list_driver.append(driver)
        list_street.append(street)
        list_url.append(url)

    pages = obter_total_paginas(soup)
    print('pages total:', pages)

    for page in range(pages):
        print('running page', page + 1)
        data_proxima_pagina = (
            f"__EVENTTARGET=&__EVENTARGUMENT=&__VIEWSTATE={viewstate.replace('/', '%2F')}&__VIEWSTATEGENERATOR=0C6A3359&ob_iDdlob_grid1PageSizeSelectorTB=10&ASPxRoundPanel2%24grid1%24ob_grid1FooterContainer%24ob_grid1PageSizeSelector=10&ob_iDdlob_grid1PageSizeSelectorSIS=1&ASPxRoundPanel2%24grid1%24ob_grid1EditControl1=&ASPxRoundPanel2%24grid1%24ob_grid1EditControl2=&ASPxRoundPanel2%24grid1%24ob_grid1EditControl3=&ASPxRoundPanel2%24grid1%24ob_grid1EditControl4=&ASPxRoundPanel2%24grid1%24ob_grid1ViewstateContainer={viewstateContainer}&ASPxRoundPanel2%24grid1%24ob_grid1EMRC=&ASPxRoundPanel2%24grid1%24ob_grid1PageSelector={1 + page}&ASPxRoundPanel2%24grid1%24ob_grid1TotalRecords=32&ASPxRoundPanel2%24grid1%24ob_grid1CellDivsWidthContainer=&ASPxRoundPanel2%24grid1%24ob_grid1ColumnsWidthContainer=0%2C110%2C90%2C50%25%2C50%25&ASPxRoundPanel2%24grid1%24ob_grid1VSC=&ASPxRoundPanel2%24grid1%24ob_grid1FBConfC=1&ASPxRoundPanel2%24grid1%24ob_grid1CFEC=&ASPxRoundPanel2%24grid1%24ob_grid1SerializedCols=key_crash*_o_osep_*None*_o_osep_*0*_o_osep_*false*_o_osep_*0*_o_osep_*false*_o_osep_*0*_o_osep_*key_crash*_o_asep_*LocalUse*_o_osep_*Desc*_o_osep_*0*_o_osep_*false*_o_osep_*0*_o_osep_*true*_o_osep_*1*_o_osep_*LocalUse*_o_asep_*DateOfCrash*_o_osep_*None*_o_osep_*0*_o_osep_*false*_o_osep_*0*_o_osep_*true*_o_osep_*2*_o_osep_*DateOfCrash*_o_asep_*LastName*_o_osep_*None*_o_osep_*0*_o_osep_*false*_o_osep_*0*_o_osep_*true*_o_osep_*3*_o_osep_*LastName*_o_asep_*RoadOn*_o_osep_*None*_o_osep_*0*_o_osep_*false*_o_osep_*0*_o_osep_*true*_o_osep_*4*_o_osep_*RoadOn&ASPxRoundPanel2%24grid1%24ob_grid1SortExpression=&ASPxRoundPanel2%24grid1%24ob_grid1SortOrder=&&__ob_gridgrid1IsCallback=1&__CALLBACKID=ASPxRoundPanel2%24grid1&__CALLBACKPARAM=&__EVENTVALIDATION={eventvalidation.replace('/', '%2F')}"
        )
        response_proxima_pagina = requests.post(
            'https://winston-salem.ecrash.interplat.com/SearchReports.aspx',
            headers=headers,
            data=data_proxima_pagina,
        )
        dados_pagina_extra, _ = parse_tabela_pagina(response_proxima_pagina.content)
        for report, date, driver, street, url in dados_pagina_extra:
            list_report.append(report)
            list_date.append(date)
            list_driver.append(driver)
            list_street.append(street)
            list_url.append(url)

    list_url_final = [f"""https://winston-salem.ecrash.interplat.com/ShowReport.aspx?id={url.split('id=')[1].split("'")[0]}""" for url in list_url]

    list_insurance = []
    list_vin = []
    list_policy = []
    owner_list = []
    list_cities = []
    list_States = []
    list_Addresses = []
    list_DOB = []
    list_costs = []
    list_narratives=[]

    for k in range(len(list_url_final)):
        attempts = 0
        while attempts < 5:
            try:
                pdf_url = obter_url_pdf(list_url_final[k])
                nome_arquivo_temp = "temp_file.pdf"
                baixar_pdf(pdf_url, nome_arquivo_temp, outdata_folder)

                dados_pdf, texto_pdf = extrair_dados_do_pdf(nome_arquivo_temp, list_driver, outdata_folder)

                owner_list.append(dados_pdf.get("owners", []))
                list_insurance.append(dados_pdf.get("insurance", []))
                list_vin.append(dados_pdf.get("vins", []))
                list_policy.append(dados_pdf.get("policies", []))
                list_cities.append(dados_pdf.get("cities", []))
                list_States.append(dados_pdf.get("states", []))
                list_Addresses.append(dados_pdf.get("addresses", []))
                list_DOB.append(dados_pdf.get("dob", []))
                list_costs.append(dados_pdf.get("costs", []))
                # list_narratives.append([dados_pdf.get("narrative", "")] * len(dados_pdf.get("policies", [])))

                narrativa = dados_pdf.get("narrative", "")
                if isinstance(narrativa, list):
                    narrativa = "\n".join(narrativa)  # ou narrativa[0] se quiser só o primeiro item
                list_narratives.append([narrativa] * len(dados_pdf.get("policies", [])))

                nome_arquivo_final_nome = f"WSP-{datetime.now().year}-{list_report[k]}.pdf"
                nome_arquivo_temp = os.path.join(caminho_base, "temp_file.pdf")
                nome_arquivo_final = os.path.join(caminho_base, nome_arquivo_final_nome)
                # Verificar se o arquivo já existe antes de renomear
                if os.path.exists(nome_arquivo_final):
                    print(f"Arquivo já existe: {nome_arquivo_final}. Pulando renomeação.")
                    os.remove(nome_arquivo_temp)  # Limpar o arquivo temporário
                else:
                    os.rename(nome_arquivo_temp, nome_arquivo_final)
                break
            except requests.exceptions.RequestException as e:
                print(f"Erro de requisição ao baixar PDF ({attempts + 1}/5): {e}")
                attempts += 1
            except pdfplumber.PDFException as e:
                print(f"Erro ao processar PDF ({attempts + 1}/5): {e}")
                attempts += 1
            except Exception as e:
                print(f"Erro inesperado ({attempts + 1}/5): {e}")
                attempts += 1
            finally:
                if os.path.exists(nome_arquivo_temp):
                    os.remove(nome_arquivo_temp)

        if attempts == 3:
            print(f"Falha ao processar PDF para o relatório: {list_report[k]}")
            owner_list.append([])
            list_insurance.append([])
            list_vin.append([])
            list_policy.append([])
            list_cities.append([])
            list_States.append([])
            list_Addresses.append([])
            list_DOB.append([])
            list_costs.append([])
            list_narratives.append([])

    data_frame = {
        "REPORT": list_report,
        "DATE": list_date,
        "DRIVERS": owner_list,
        "STREET": list_Addresses,
        "URL": list_url_final,
        "Insurances": list_insurance,
        "VINs": list_vin,
        "Policies": list_policy,
        "Cities": list_cities,
        "States": list_States,
        "DOB": list_DOB,
        "Costs": list_costs,
        "Narrative": list_narratives,
    }

    df_expanded = criar_dataframe(data_frame)
    file_name = f"Data_Crashes_WSP_Daily_{format1}.csv"
    salvar_dataframe_csv(df_expanded, file_name, outdata_folder)
