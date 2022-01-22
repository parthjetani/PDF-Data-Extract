import datetime
import os
import pdfplumber
import mysql.connector
from dotenv import load_dotenv, find_dotenv
import glob

load_dotenv(find_dotenv())

def parse_pdf_extrato(path):
    filename = path.split("/")[-1]

    all_text = ""

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            all_text += '\n' + text

    # Extract all informations from PDF and create list
    all_lines = list(filter(bool, all_text.split('\n')))

    first_section1 = first_section2 = 0
    second_section1 = second_section2 = 0
    third_section1 = third_section2 = 0
    forth_section1 = forth_section2 = 0
    fifth_section1 = fifth_section2 = 0

    # first section

    for index, val in enumerate(all_lines):
        if 'EXTRATO DE DÉBITOS' in val.strip():
            first_section1 = index
        if 'Mês de Ref:' in val.strip():
            first_section2 = index

    first_data = all_lines[first_section1+1:first_section2+1]
    name = first_data[1]

    for val in first_data:
        if 'Nº:' in val:
            n_extrato = int(val.split(" ")[-1])
        if 'Fornecimento:' in val:
            n_fornecimento = int(val.split(" ")[-1])
        if 'Cód. Cliente:' in val:
            cod_cliente = int(val.split(" ")[-1])
        if 'CNPJ/CPF:' in val:
            cpf = val.split(" ")[-1]
        if 'Mês de Ref:' in val:
            ref_month = val.split(" ")[-1].split("/")[0]
            ref_year = val.split(" ")[-1].split("/")[-1]

    # second section

    for index, val in enumerate(all_lines):
        if 'Autenticação mecânica do agente autorizado' in val.strip():
            second_section1 = index
        elif 'PAGUE ESTE EXTRATO SOMENTE NOS AGENTES AUTORIZADOS' in val.strip():
            second_section2 = index
            break

    second_data = all_lines[second_section1+1:second_section2]
    
    barcode_line1 = second_data[0].replace(" ", "")
    barcode_line2 = second_data[-1]

    # third section

    for index, val in enumerate(all_lines):
        if 'Banco: não receber após' in val.strip():
            third_section1 = index
        elif 'INFORMAÇÕES DA UNIDADE USUÁRIA' in val.strip():
            third_section2 = index
            break

    third_data = all_lines[third_section1+1:third_section2]

    for index, val in enumerate(third_data):
        if 'Mês de Referência' in val:
            tdata1 = third_data[index+1].split(" ")

    due_date = datetime.datetime.strptime(
        tdata1[1], "%d/%m/%Y").strftime('%Y/%m/%d')

    total_amount = tdata1[-1]
    dot_pos = total_amount.rfind('.')
    comma_pos = total_amount.rfind(',')
    
    if comma_pos > dot_pos:
        total_amount = total_amount.replace(".", "")
        total_amount = total_amount.replace(",", ".")
    else:
        total_amount = total_amount.replace(",", "")

    # fourth section

    for index, val in enumerate(all_lines):
        if 'INFORMAÇÕES DA UNIDADE USUÁRIA' in val.strip():
            forth_section1 = index
        elif 'Primeira Vistoria' in val.strip():
            forth_section2 = index
            break

    fourth_data = all_lines[forth_section1+1:forth_section2]
    address_cep = [fourth_data[-1].strip().split(" ")[-1].strip()]
    
    for index, val in enumerate(fourth_data):
        if 'Fornecimento Codificação Sabesp Hidrômetro TL At. Com. Data de Emissão' in val:
            fourth_data1 = fourth_data[index+1].split(" ")

    code = fourth_data1[1].split(".")

    sabesp_code = fourth_data1[1]
    cod_agrupamento = int(code[0])
    cod_setor = int(code[1])
    cod_rota = int(code[2])
    cod_quadra = int(code[3])
    cod_local = int(code[4])
    cod_sublocal = int(code[5] + code[6])
    hidrometer = fourth_data1[2]
    tl = fourth_data1[3]
    at_com = fourth_data1[4]
    emission_date = (datetime.datetime.strptime(fourth_data1[-1], "%d/%m/%Y")).strftime('%Y/%m/%d')

    # fifth section

    for index, val in enumerate(all_lines):
        if 'Sr(a). ' in val.strip():
            fifth_section1 = index
        if 'INFORMAÇÕES DA UNIDADE USUÁRIA' in val.strip():
            fifth_section2 = index

    fifth_data = all_lines[fifth_section1:fifth_section2]
    if len(fifth_data) < 5:
        if len(fifth_data) == 4:
            if 'CEP:' in fifth_data[-1]:
                address_cep = [(fifth_data[-1]).split(":")[-1].strip()]
                fifth_data.remove(fifth_data[-1])
                
                if len(fifth_data) == 3:
                    if fifth_data[1] in name:
                        full_name = fifth_data[0] + fifth_data[1]
                        address_full = fifth_data[2]
                    else:
                        full_name = fifth_data[0]
                        address_full = fifth_data[1] + fifth_data[2]
                else:
                    full_name = fifth_data[0]
                    address_full = fifth_data[1]
            
            else:
                if fifth_data[1] in name:
                    full_name = fifth_data[0] + fifth_data[1]
                    address_full = fifth_data[2] + fifth_data[3]
                    
        elif len(fifth_data) == 3:
            if 'CEP:' in fifth_data[-1]:
                address_cep = [(fifth_data[-1]).split(":")[-1].strip()]
                full_name = fifth_data[0]
                address_full = fifth_data[1]
            else:
                if fifth_data[1] in name:
                    full_name = fifth_data[0] + fifth_data[1]
                    address_full = fifth_data[2]
                else:
                    full_name = fifth_data[0]
                    address_full = fifth_data[1] + fifth_data[2]
        
        else:
            full_name = fifth_data[0]
            address_full = fifth_data[1]
            
                
    address_number = [None if address_full.strip().split("-")[1].strip() == '' else address_full.strip().split("-")[1].strip()]
    address_complement = [None if address_full.strip().split("-")[2].strip() == '' else address_full.strip().split("-")[2].strip()]
    address_end = ' '.join(address_full.strip().split("-")[0].split(" ")[1:])

    return (datetime.datetime.now(), datetime.datetime.now(), full_name, cpf, n_extrato, n_fornecimento, cod_cliente, ref_month, ref_year,
            barcode_line1, barcode_line2, due_date, total_amount, emission_date, hidrometer, sabesp_code, tl, at_com, address_end,
            address_number[0], address_complement[0], address_cep[0], address_full, cod_agrupamento,
            cod_setor, cod_rota, cod_quadra, cod_local, cod_sublocal, filename)


def insert_into_db(data: tuple):
    print('[PDF INSERT] BEGIN')
    mydb = mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USERNAME'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_DATABASE')
    )

    cursor = mydb.cursor()

    # Here is your database query for storing extracted data
    query = ""

    try:
        print('INSERTING IN DATABASE')
        cursor.execute(query, data)
    except mysql.connector.errors.IntegrityError as e:
        print(e)
    mydb.commit()
    mydb.close()


if __name__ == "__main__":

    # Here is your PDF folder pah
    BASE_DIR = os.getenv('BASE_DIR')
    try:
        # Open PDF one by one
        for filename in glob.glob(os.path.join(BASE_DIR, '*.pdf')):
            if filename.endswith('.pdf'):
                fullpath = os.path.join(BASE_DIR, filename)
                insert_into_db(parse_pdf_extrato(fullpath))
                print("Data inserted into DB")
    except FileNotFoundError as f:
        print(f)
    except Exception as e:
        print(e)