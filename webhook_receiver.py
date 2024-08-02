from flask import Flask, request, jsonify
import requests
import gspread
import time
from datetime import datetime
import json
from dotenv import load_dotenv
import os
load_dotenv()
api_monday = os.getenv("API_MONDAY")
api_many = os.getenv("API_MANY")
google_private_key = os.getenv("GOOGLE_API_PRIVATE_KEY")

# inicio de autenticacion
#----------------------- monday
apiUrl = "https://api.monday.com/v2"
headers_monday = {"Authorization" : api_monday}

#------------------------ manychat
headers_many = {
    'Authorization': f'Bearer {api_many}',
    'Content-Type': 'application/json'
}
#--------------------------google

api_google={
  "type": "service_account",
  "project_id": "graphite-sphere-374923",
  "private_key_id": "924459f8a55c9f96222a99d51ce07da6627e6fd5",
  "private_key": google_private_key,
  "client_email": "shert-590@graphite-sphere-374923.iam.gserviceaccount.com",
  "client_id": "112825666518300225436",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/shert-590%40graphite-sphere-374923.iam.gserviceaccount.com"
}

gc = gspread.service_account_from_dict(api_google)
# Fin de autenticacion

app = Flask(__name__)


@app.route('/webhook', methods=['POST'])

def webhook():
    if request.method == 'POST':
        start = time.time()
        data = request.json
        estado = data['event']['value']['label']['text']

        if estado == 'Confirmada':
            
            id_pulso = data['event']['pulseId']
            client = get_column_client(id_pulso)
            status_many = update_client_many(headers_many,client)            
            
            if status_many[0]['status'] == 'success':  
                status_monday = update_monday(status_many[1],id_pulso)
                print(status_monday.status_code)
                if status_monday.status_code == 200:
                    over = time.time() 
                    ejecucion_automa(start,over,f'Ejecucion completada:{client["Celular 1"]}')
                else:
                    over = time.time() 
                    ejecucion_automa(start,over,f'error_monday{"Celular 1"}')
            else:
                err = str(status_many[0])+f'n{str(status_many[0])}'
                over = time.time() 
                ejecucion_automa(start,over,err)

        return jsonify(''),200


#####################Funciones secundarias
#----------------------------------
def update_client_many(aut_many,cliente):
    check_phone = check_user_sistem_field(aut_many,cliente)
    check_whatp = check_user_custom_field(aut_many,cliente)

    if len(cliente['Id many 1']) == 0:
    

        if check_whatp['status'] == 'success' and check_phone['status']== 'success':
            if len(check_whatp['data']) == 0:
                if len(check_phone['data']) == 0:
                    print('opcion1')
                    #aqui entran los que no estan ni con wp ni con phone
                    create_status = create_many(aut_many,cliente)
                    if create_status['status'] == 'success':
                        id_many = create_status['data']['id']
                        update_status = actualizar_campo(aut_many,cliente,id_many)
                        return update_status , id_many
                    else:
                        return create_status , 0
                else:
                    #aqui entran los que no tienen wp pero si tienen phone
                    print('opcion2')
                    id_many = check_phone['data']['id']
                    update_status = actualizar_campo(aut_many,cliente,check_phone['data']['id'])
                    return update_status, id_many
    

            else:
                
                if len(check_phone['data']) == 0:
                    #aqui entran los que tienen wp pero no tienen phone
                    print('opcion3')
                    id_many = check_whatp['data'][0]['id']                
                    create_status = update_phone(headers_many,cliente,id_many)
                    if create_status['status'] == 'success':
                        update_status = actualizar_campo(aut_many,cliente,id_many)
                        return update_status , id_many
                    else:
                        return create_status , 0
    
                else:
                    #aqui entran los que tienen wp y tienen phone
                    print("opcion4")
                    id_many = check_phone['data']['id']
                    update_status = actualizar_campo(aut_many,cliente,id_many)
                    return update_status , id_many

        else:
            print('opcion5')
            return {'status': 'error', 'message': 'update error', 'details': 'error chequeando whatsapp o phone'}
            #concateneme los dos estatus para enviarlos como error al archivo de ejecucion de automatizaciones

    else:
        #aqui entra si ya tiene el id de manychat y pues revisamos que tenga phone porque es el nos interesa para el mensaje
        print('opcion6')
        check_phone = check_user_sistem_field(aut_many,cliente)
        if check_phone['status']== 'success':
            if len(check_phone['data']) == 0:
                print('entro')
                id_many = cliente['Id many 1']            
                create_status = update_phone(headers_many,cliente,id_many)
                if create_status['status'] == 'success':
                    update_status = actualizar_campo(aut_many,cliente,id_many)
                    return update_status , id_many
                else:
                    return create_status , 0
            else:
                id_many = cliente['Id many 1'] 
                update_status = actualizar_campo(aut_many,cliente,id_many)
                return update_status , id_many
                
#------------------------------------------
def create_many(encabezado,contacto):
    url = f'https://api.manychat.com/fb/subscriber/createSubscriber'
    payload = {
        "first_name": contacto['name'],
        "last_name": "",
        "phone": '+'+contacto['Celular 1'],
        "whatsapp_phone": contacto['Celular 1'],
        "gender": "",
        "has_opt_in_sms": "true",
        "has_opt_in_email": "true",
        "consent_phrase": "string"
        }

    response = requests.post(url, headers=encabezado, json=payload)
    return response.json()
##----------------------------

def update_phone(encabezado,contacto,idMany):
    url = f'https://api.manychat.com/fb/subscriber/updateSubscriber'
    payload2 = {
        "subscriber_id": idMany,
        "first_name": contacto['name'],        
        "phone": '+'+contacto['Celular 1'],
        "has_opt_in_sms": "true",
        "has_opt_in_email": "true",
        "consent_phrase": "string"
    }
    response = requests.post(url, headers=encabezado, json=payload2)
    return response.json()

#---------------------------------
#---------------------------------  

def actualizar_campo(encabezado,contacto,idMany):
    
    if len(contacto['Fecha Prueba Menu/Firma Otrosi'])!=0 and len(contacto['Sede Prueba Menu'])!=0:
        url = f'https://api.manychat.com/fb/subscriber/setCustomFields'
        payload = {
        "subscriber_id": idMany,
        "fields": [
            {
            "field_id": 11517154,
            "field_name": "Nombre pareja",
            "field_value": contacto['name']                
            },
            {
            "field_id": 11498558,
            "field_name": "Fecha_prueba_menu",
            "field_value": contacto['Fecha Prueba Menu/Firma Otrosi']
            },
            {
            "field_id": 11498566,
            "field_name": "Loca_prueba_menu",
            "field_value": contacto['Sede Prueba Menu']
            }
        ]
        }
        response = requests.post(url, headers=encabezado, json=payload)
        return response.json()
    else:
        return {'status': 'error', 'message': 'update error', 'details': 'error en la actualizacion de campos de fecha y loca'}

#------------------------------
def check_user_custom_field(encabezado,contacto):
    url = f'https://api.manychat.com/fb/subscriber/findByCustomField'
    params = {
        'field_id': 11495176,
        'field_value': contacto['Celular 1']
     }
    response = requests.get(url,headers=encabezado,params=params)
    return response.json()

#-----------------------------
def check_user_sistem_field(encabezado,contacto):
    url = f'https://api.manychat.com/fb/subscriber/findBySystemField'
    params = {
    "phone":'+'+contacto['Celular 1']
     }
    response = requests.get(url,headers=encabezado,params=params)
    return response.json()
#-----------------------------
def get_column_client(id):
    dic = {}
    query = '''
    query {
    items (ids: [%d]) {
        name
        column_values(ids: ["tel_fono","celular_1","email_1","texto79","email_23","fecha3","estado93"]) {
        column {
            title
        }
        value
        text
        }
    }
    }
    ''' % id
    data = {'query': query}

    response = requests.post(url=apiUrl, json=data, headers=headers_monday)

    if response.status_code == 200:
        item_data = response.json()['data']['items'][0]
        name = format_name(item_data)
        dic['name'] = name
        for col in item_data['column_values']:
            dic[col['column']['title']] = col['text']
        return dic
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
#-------------------------------
def update_monday(idMany,idMonday):
    vals = {'texto79': idMany }
    Mut2 = ' mutation  ( $id: ID!,  $columnVals: JSON!)  { change_multiple_column_values (board_id:207361215, item_id: $id, column_values: $columnVals) { id } }'
    vars = {'id' : idMonday,
              'columnVals' : json.dumps(vals)}
    dataUP = {'query' : Mut2, 'variables' : vars}
    req = requests.post(url=apiUrl, json=dataUP, headers=headers_monday)
    return req
#-----------------------------------
def ejecucion_automa(_start,_over,estado):
    hora = str(datetime.today().time())[:-7]
    tiempo_ejecucion = (_over-_start)/60
    fecha_ejecucion = datetime.today().strftime("%d/%m/%Y")
    url='https://docs.google.com/spreadsheets/d/17De9XoKdl0sith1I03eMlURr3MayMx5GeugsE-QjZmk/edit?gid=0#gid=0'
    archivo_ejecucion = gc.open_by_url(url)
    hoja_ejecucion = archivo_ejecucion.worksheet('Registro de ejecucion')
    fila_ejecucion = len(hoja_ejecucion.get_all_values())

    hoja_ejecucion.update_cell(fila_ejecucion+1,1,fecha_ejecucion)
    hoja_ejecucion.update_cell(fila_ejecucion+1,2,'Prueba de menu')
    hoja_ejecucion.update_cell(fila_ejecucion+1,3,hora)
    hoja_ejecucion.update_cell(fila_ejecucion+1,4,(tiempo_ejecucion))
    hoja_ejecucion.update_cell(fila_ejecucion+1,5,'VERDADERO')
    hoja_ejecucion.update_cell(fila_ejecucion+1,6,estado)

#----------------------------
def format_name(item_name):
    index1 = item_name['name'].find("-")
    index2 = item_name['name'].find("/")
    index3 = item_name['name'].find("2")
    inicio = index3+7 
    if index1 < 0 :
        solo_name = item_name['name'][inicio:index2]
    if index2 < 0 :
        solo_name = item_name['name'][inicio:index1]    
    if index1 > 0 and index2 > 0 :
        if index1 < index2 :
            solo_name = item_name['name'][inicio:index1]
        else:
            solo_name = item_name['name'][inicio:index2]    
    if index1 <0 and index2 < 0 :
        solo_name = item_name['name']

    solo_name_final =solo_name.rstrip()
    return solo_name_final

################# Fin Funciones secundarias 


if __name__ == '__main__':
    app.run(host='0.0.0.0',port = 5000)

