import socket
import struct
import _thread
import time
#from datatime import date
#from datetime import datetime
#from datetime import timedelta
import datetime as date
from threading import Timer
import configparser as cfg

config = cfg.ConfigParser()
config.read ('Servidor.ini')

structsize = 8 
max_pack_size = 252

#Endereço do CL
HOST_SERVIDOR = config.get ('servidor_ipcfg', 'ip_host') 			# Endereco IP do Servidor
PORT_SERVIDOR = config.getint ('servidor_ipcfg', 'cl_port')           # Porta que o Servidor esta

#Criando dicionario de CL
dicionario_controlador = {}

#Variáveis do sistema
msg_send = "None"

dia_util = config.getint ('servidor_cfg', 'dia_util')
parametro_defeito = config.getint ('servidor_cfg', 'parametro_defeito') # Parametro para o contador de falhas antes de dar kill no sensor
mensagem_interval = config.getint ('servidor_cfg', 'mensagem_interval') # Intervalo de tempo em segundos para verificar mensagens recebidas
tempo_maximo = config.getint ('servidor_cfg', 'tempo_maximo') # Em segundos para incrementar o contador

def date_time():
	datahora = date.datetime.now()
	return date.datetime.timestamp(datahora)

# Insere novo sensor no dicionario de controladores
def insere_dicionario (dicionario_controlador, id_controlador, tipo_local_controlador, connect):
	lista = [id_controlador, tipo_local_controlador, date.datetime.now(), connect, 0, None] #O primeiro 0 é para o contador de falhas e o None serve para identificação de retorno do CL 
	dicionario_controlador[id_controlador] = lista
#Verifica existencia do controlador 
def verifica_controlador(dicionario_controlador, id_controlador):
	for i in dicionario_controlador.keys():
		if (dicionario_controlador[i][0] == id_controlador):
			return True
#Função para pegar id e tipo do sensor
def id_tipo_sensor(mensagem):
	msg = mensagem[0]
	msg_2 = mensagem[1]
	msg_3 = msg.split(":")
	msg_4 = msg_2.split(":")
	return int(msg_3[1]), int(msg_4[1])
#Função que trata mensagens recebidas do controlador 
def trata_controlador_servidor(connect, id_controlador, tipo_local_controlador, mensagem):
	msg = mensagem.decode()
	mensagem = msg.split("|")
	if  "alerta:1" in mensagem:
		dicionario_controlador[id_controlador][2] = date.datetime.now()
		msg = id_tipo_sensor(mensagem)
		print ("Alerta de incendio.")
		print ("Acionando bombeiros para:")
		print ("Tipo Local do Controlador:", int(tipo_local_controlador), "ID do Controlador:", id_controlador)
		print ("ID do sersor:", msg[0])
		my_send(dicionario_controlador[id_controlador][3], dia_util,  "Ta pegando fogo, bicho!|comando:0")
	if "alerta:2" in mensagem:
		dicionario_controlador[id_controlador][2] = date.datetime.now()
		msg = id_tipo_sensor(mensagem)
		print ("Sensor defeituoso.Chamando assintência técnica!")
		print ("ID Controlador:", id_controlador, " | " , "ID Sensor:", msg[0])
		print ("Tipo Local Controlador:", int(tipo_local_controlador), " | " , "Tipo Sensor:", msg[1])
	if "alerta:None" in mensagem:
		print ("Enviando comando.")
		dicionario_controlador[id_controlador][2] = date.datetime.now()
		my_send(dicionario_controlador[id_controlador][3], dia_util,  "comando:1")
	if "controle:1" in mensagem:
		print ("Mensagem de controle recebida!")
		print ("ID Controlador:", id_controlador, " | ","Tipo Local Controlador:", int(tipo_local_controlador))
		dicionario_controlador[id_controlador][2] = date.datetime.now()
		my_send(dicionario_controlador[id_controlador][3], dia_util,  "controle:None")
#Função que trata mensagem recebida do controlador
def trata_controlador(connect, id_controlador, tipo_local_controlador, mensagem):
	if (not verifica_controlador(dicionario_controlador, id_controlador) and mensagem.decode() == "None"):
		print ("Controlador instalado!")
		print ("ID:", id_controlador)
		insere_dicionario (dicionario_controlador, id_controlador, tipo_local_controlador, connect)
		print ("Enviando primeira mensagem ao controlador!")
		my_send (dicionario_controlador[id_controlador][3], dia_util, "None")
	else:
		if(dicionario_controlador[id_controlador][5] == None):
			trata_controlador_servidor(connect, id_controlador, tipo_local_controlador, mensagem)
		else:
			print ("Controlador reparado.")
			print ("ID Controlador:", id_controlador)
			print (" ")
			trata_controlador_servidor(connect, id_controlador, tipo_local_controlador, mensagem)
			dicionario_controlador[id_controlador][5] = None
			dicionario_controlador[id_controlador][2] = date.datetime.now()
# Faz o primeiro tratamento de mensagem recebida	
def conectado(connect, cliente, dicionario_controlador):
	while True:
		msg = my_recv(connect)
		if (not msg):
			break
		#print (msg)
		if (cliente != None):
			id_controlador, tipo_local_controlador, mensagem = msg
		
			trata_controlador(connect, id_controlador, tipo_local_controlador, mensagem)
		
		print (" ")
	connect.close()
	_thread.exit()
# Funcao  de recepção e desempacotamento da mensagem do controlador
def my_recv(socket):	
	try:	
		msg = socket.recv(max_pack_size)
		pack_size = len(msg) - structsize
		mask_format = '!If' + str(pack_size) + 's'
		return struct.unpack(mask_format, msg)
	except ConnectionResetError:
		print ('Erro! Controlador desconectado!')
		return False
#Funcao transforma a mensagem em string
def mensagem_format (dia_util, data, msg_send):
	mask_format = '!If' + str(len(msg_send.encode())) + 's'
	mensagem = struct.pack(mask_format, dia_util, data, msg_send.encode())
	return mensagem
# Funcao de empacotamento e envio de da mensagem para o controlador
def my_send (socket, dia_util, msg_send):
	try:
		msg = mensagem_format(dia_util, date_time(), msg_send)
		socket.send (msg)
	except ConnectionResetError:
		return False
#Verifica e trata controlador defeituoso
def verifica_intervalo(dicionario_controlador, tempo_maximo, parametro_defeito):
    for i in dicionario_controlador.keys():
        if ((date.datetime.now() - dicionario_controlador[i][2]) > (date.timedelta(seconds = tempo_maximo))):
            dicionario_controlador[i][4] += 1
            print ("Incrementando!", dicionario_controlador[i][4])
            #print (dicionario_sensor[i])
            if (dicionario_controlador[i][4] >= parametro_defeito and dicionario_controlador[i][4] < parametro_defeito + 1 ):
                print("Controlador com defeito!")
                print("Chamando assistência técnica para:")
                print("ID Controlador:", dicionario_controlador[i][0], " | " ,"Tipo Local do Controlador:", dicionario_controlador[i][1])
                print(" ")
                dicionario_controlador[i][5] = 1
                break
        else:
            dicionario_controlador[i][4] = 0
# Timer para verificar recepcao de mensagens
def set_interval_controlador(interval, dicionario_controlador, tempo_maximo, parametro_defeito):
    
    def set_timer(wrapper):
        wrapper.timer = Timer(interval, wrapper)
        wrapper.timer.start()

    def wrapper():
        verifica_intervalo(dicionario_controlador, tempo_maximo, parametro_defeito)
        set_timer(wrapper)

    set_timer(wrapper)
    return wrapper
#Variavel para monitorar recepção de mensagens 
interval_monitor = set_interval_controlador(mensagem_interval, dicionario_controlador, tempo_maximo, parametro_defeito)
# Programa principal Controlador
tcp_controlador = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
origem_controlador = (HOST_SERVIDOR, PORT_SERVIDOR)
tcp_controlador.bind(origem_controlador)
tcp_controlador.listen(1)

print ("Inicializando servidor.")
print ("Aluno: Mateus Schineider")
print ()

while True:
    connect, cliente = tcp_controlador.accept()
    _thread.start_new_thread(conectado, tuple([connect, cliente, dicionario_controlador]))    
tcp_controlador.close()
