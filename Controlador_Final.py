import socket
import struct
import _thread
import time
import datetime as date
from datetime import datetime
from threading import Timer
import configparser as cfg

config = cfg.ConfigParser()
config.read ('cl_cfg.ini')

structsize = 8 
max_pack_size = 252

#Sensor
HOST_SENSOR = config.get ('controlador_ipcfg', 'ip_sensor')            # Endereco IP do Servidor
PORT_SENSOR = config.getint ('controlador_ipcfg', 'sensor_port')            # Porta que o Servidor esta

#Servidor		
HOST_SERVIDOR = config.get ('controlador_ipcfg', 'ip_servidor')			# Endereco IP do Servidor
PORT_SERVIDOR = config.getint ('controlador_ipcfg', 'servidor_port')          # Porta que o Servidor esta

#Variaveis do controlador
id_controlador = config.getint ('controlador_cfg', 'control_id') 
tipo_local_controlador = config.getint ('controlador_cfg', 'control_tipo') 
# Dicionarios do programa
dicionario_sensor = {}
lista_servidor = [None] #Posição 0 - prametro de liga ou desliga  
# Variaveis do programa
msg_send = "None"

mensagem_interval_servidor = config.getint ('controlador_cfg', 'mensagem_interval_servidor') # Intervalo de tempo em segundos para verificar mensagens recebidas
parametro_defeito = config.getint ('controlador_cfg', 'parametro_defeito') # Parametro para o contador de falhas antes de dar kill no sensor
desliga_interval = config.getint ('controlador_cfg', 'desliga_interval') # Tempo em segundos para desligar equipamentos caso nao tenha ninguem em sala
mensagem_interval = config.getint ('controlador_cfg', 'mensagem_interval') # Intervalo de tempo em segundos para verificar mensagens recebidas
tempo_maximo = config.getint ('controlador_cfg', 'tempo_maximo') # Em segundos para incrementar o contador

# Verificar e tratar sensor defeituoso
def controle_de_defeito(dicionario_sensor, id, tipo): #Alerta de defeito com numero 2
    id_func = dicionario_sensor[id, tipo][0]
    if (dicionario_sensor[id, tipo][1] == 1):
        print ('Alerta! Sensor de presença com defeito! ID do sensor:', id_func)
    elif (dicionario_sensor[id, tipo][1] == 2):
        print ('Alerta! Sensor de luminosidade com defeito! ID do sensor:', id_func)
    elif (dicionario_sensor[id, tipo][1] == 3):
        print ('Alerta! Sensor de temperatura com defeito! ID do sensor:', id_func)

def verifica_intervalo(dicionario_sensor, tempo_maximo, parametro_defeito):
    for i in dicionario_sensor.keys():
        if ((date.datetime.now() - dicionario_sensor[i][3]) > (date.timedelta(seconds = tempo_maximo))):
            dicionario_sensor[i][4] += 1
            print ("Incrementando!", dicionario_sensor[i][4])
            #print (dicionario_sensor[i])
            if (dicionario_sensor[i][4] >= parametro_defeito):
                #controle_de_defeito(dicionario_sensor, dicionario_sensor[i][0], dicionario_sensor[i][1])
                msg = mensagem_send(dicionario_sensor[i][0], dicionario_sensor[i][1])
                my_send_servidor (tcp_servidor, id_controlador, tipo_local_controlador, msg )
                del dicionario_sensor[i]
                break
        else:
            dicionario_sensor[i][4] = 0
# Liga equipamentos ao detectar mudanca no sensor de presenca
def liga_equipamento(dicionario_sensor, lista_servidor):
	for i in dicionario_sensor.keys():
		if (dicionario_sensor[i][1] == 2 and dicionario_sensor[i][5] == 0 and lista_servidor[0] and dicionario_sensor[i][2] < 2000):
			dicionario_sensor[i][5] = 1
			dicionario_sensor[i][6] = date.datetime.now()
			print ('Ligando luzes. Sensor ID:', dicionario_sensor[i][0])
			print (" ")
		if (dicionario_sensor[i][1] == 3 and dicionario_sensor[i][5] == 0 and lista_servidor[0] and dicionario_sensor[i][2] >= 23):
			dicionario_sensor[i][5] = 1
			dicionario_sensor[i][6] = date.datetime.now()
			print ('Ligando ar condicionado. Sensor ID:', dicionario_sensor[i][0])
			print (" ")
# Desliga equipamentos ao detectar mudanca no sensor de presenca
def desliga_equipamento (dicionario_sensor):
	for i in dicionario_sensor.keys():
		if (dicionario_sensor[i][1] == 2 and dicionario_sensor[i][5] == 1):
			dicionario_sensor[i][5] = 0
			dicionario_sensor[i][7] = date.datetime.now()
			print ('Desligando luzes. Sensor ID:', dicionario_sensor[i][0])
			print ('As luzes permaneceram ligadas por:', dicionario_sensor[i][7] - dicionario_sensor[i][6])
			print (" ")
		if (dicionario_sensor[i][1] == 3 and dicionario_sensor[i][5] == 1):
			dicionario_sensor[i][5] = 0
			dicionario_sensor[i][7] = date.datetime.now()
			print ('Desligando ar condicionado. Sensor ID:', dicionario_sensor[i][0])
			print ('O ar condicionado permaneceu ligado por:', dicionario_sensor[i][7] - dicionario_sensor[i][6])
			print (" ")
# Insere novo sensor no dicionario de sensores
def insere_dicionario (dicionario_sensor, id_sensor, tipo_sensor, valor_sensor):
	lista = [id_sensor, tipo_sensor, valor_sensor,  date.datetime.now(), 0, 0, None, None] #Os dois None sao a data que ele lida/desliga
	dicionario_sensor[id_sensor, tipo_sensor] = lista
# Verifica se o sensor mudou seu estado
def mudaca_estado (dicionario_sensor, id_sensor, tipo_sensor, valor_sensor):
	if (dicionario_sensor[id_sensor, tipo_sensor][2] != valor_sensor):
		print ('Valor do sensor', id_sensor ,'alterado! Valor anterior:', dicionario_sensor[id_sensor, tipo_sensor][2], 'Novo valor:', valor_sensor)
		teste = dicionario_sensor[id_sensor, tipo_sensor][2]
		dicionario_sensor[id_sensor, tipo_sensor][2] = valor_sensor
		if (tipo_sensor == 3 and teste >= 50 and valor_sensor <= 50):
			my_send_servidor(tcp_servidor, id_controlador, tipo_local_controlador, "alerta:None")
		return True
	else:
		return False
# Verifica existencia de outros sensores alem do de presença no dicionario
def verifica_sensores (dicionario_sensor):	
	for i in dicionario_sensor.keys():
		if (dicionario_sensor[i][1] == 2 or dicionario_sensor[i][1] == 3):
			return True
# Trata dados relacionados ao sensor de presença
def trata_sensor_presenca(dicionario_sensor, id_sensor, tipo_sensor):
	if (dicionario_sensor[id_sensor, tipo_sensor][2] == 1 and dicionario_sensor[id_sensor, tipo_sensor][5] == 0):
		dicionario_sensor[id_sensor, tipo_sensor][5] = 1
		print ('Pessoa detectada!')
	elif (dicionario_sensor[id_sensor, tipo_sensor][2] == 0 and dicionario_sensor[id_sensor, tipo_sensor][5] == 1):
		dicionario_sensor[id_sensor, tipo_sensor][5] = 0
		print ('Pessoa não detectada!')
# Faz o controle do sensor de presença
def sensor_presenca (interval ,dicionario_sensor, id_sensor, tipo_sensor, valor_sensor, lista_servidor):
	if (id_sensor, tipo_sensor) in dicionario_sensor.keys():
		dicionario_sensor[id_sensor, tipo_sensor][3] = date.datetime.now()
		if (mudaca_estado (dicionario_sensor, id_sensor, tipo_sensor, valor_sensor)):
			trata_sensor_presenca(dicionario_sensor, id_sensor, tipo_sensor)
			if (verifica_sensores(dicionario_sensor) and valor_sensor == 0 and dicionario_sensor[id_sensor, tipo_sensor][5] == 0 and not(verifica_presenca(dicionario_sensor))):
				desliga = set_interval_off(interval, dicionario_sensor)
			elif (valor_sensor == 1 and dicionario_sensor[id_sensor, tipo_sensor][5] == 1):
				liga_equipamento(dicionario_sensor, lista_servidor)
	else:
		print ('Sensor de presença',id_sensor, 'conectado!')
		insere_dicionario (dicionario_sensor, id_sensor, tipo_sensor, valor_sensor)
		trata_sensor_presenca(dicionario_sensor, id_sensor, tipo_sensor)
		if (valor_sensor == 1 and dicionario_sensor[id_sensor, tipo_sensor][5] == 1):
				liga_equipamento(dicionario_sensor, lista_servidor)
# Verifica a existencia de um sesor de presenca ativo
def verifica_presenca (dicionario_sensor):
	for i in dicionario_sensor.keys():
		if (dicionario_sensor[i][1] == 1 and dicionario_sensor[i][5] == 1):
			return True
# Trata dados relacionados ao sensor de luminosidade
def trata_sensor_luminosidade(dicionario_sensor, id_sensor, tipo_sensor, lista_servidor):
	if (verifica_presenca(dicionario_sensor) and dicionario_sensor[id_sensor, tipo_sensor][2] < 2000 and dicionario_sensor[id_sensor, tipo_sensor][5] == 0 and lista_servidor[0]):
		dicionario_sensor[id_sensor, tipo_sensor][5] = 1
		dicionario_sensor[id_sensor, tipo_sensor][6] = date.datetime.now()
		print ('Luzes ligadas!')
	elif (dicionario_sensor[id_sensor, tipo_sensor][2] > 2000 and dicionario_sensor[id_sensor, tipo_sensor][5] == 1):
		dicionario_sensor[id_sensor, tipo_sensor][5] = 0
		dicionario_sensor[id_sensor, tipo_sensor][7] = date.datetime.now()
		print ('Luzes desligadas!')
		print ('As luzes permaneceram ligadas por:', dicionario_sensor[id_sensor, tipo_sensor][7] - dicionario_sensor[id_sensor, tipo_sensor][6])	
# Faz o controle do sensor de luminosidade
def sensor_luminosidade (dicionario_sensor, id_sensor, tipo_sensor, valor_sensor, lista_servidor):
	if (id_sensor, tipo_sensor) in dicionario_sensor.keys():
		dicionario_sensor[id_sensor, tipo_sensor][3] = date.datetime.now()
		if (mudaca_estado (dicionario_sensor, id_sensor, tipo_sensor, valor_sensor)):
			trata_sensor_luminosidade(dicionario_sensor, id_sensor, tipo_sensor, lista_servidor)
	else:
		print ('Sensor de luminosidade',id_sensor, 'conectado!')
		insere_dicionario (dicionario_sensor, id_sensor, tipo_sensor, valor_sensor)
		trata_sensor_luminosidade(dicionario_sensor, id_sensor, tipo_sensor, lista_servidor)
# Trata dados relacionados ao sensor de temperatura
def trata_sensor_temperatura(dicionario_sensor, id_sensor, tipo_sensor, lista_servidor): #Alerta de defeito com numero 2
	if (verifica_presenca(dicionario_sensor) and dicionario_sensor[id_sensor, tipo_sensor][2] >= 23 and dicionario_sensor[id_sensor, tipo_sensor][2] < 50 and dicionario_sensor[id_sensor, tipo_sensor][5] == 0 and lista_servidor[0]):
		dicionario_sensor[id_sensor, tipo_sensor][5] = 1
		print ('Ar condicionado ligado!')
		dicionario_sensor[id_sensor, tipo_sensor][6] = date.datetime.now()
	elif (dicionario_sensor[id_sensor, tipo_sensor][2] < 20 and dicionario_sensor[id_sensor, tipo_sensor][5] == 1):
		dicionario_sensor[id_sensor, tipo_sensor][5] = 0
		dicionario_sensor[id_sensor, tipo_sensor][7] = date.datetime.now()
		print ('Ar condicionado desligado!')
		print ('O ar condicionado permaneceu ligado por:', dicionario_sensor[id_sensor, tipo_sensor][7] - dicionario_sensor[id_sensor, tipo_sensor][6])
	elif (dicionario_sensor[id_sensor, tipo_sensor][2] >= 50):
		print ('ALERTA DE INCENDIO!! ID SENSOR:', dicionario_sensor[id_sensor, tipo_sensor][0]) 
		dicionario_sensor[id_sensor, tipo_sensor][5] = 0
		string = "ID_Sensor" + ":" + str(id_sensor) + "|" + "Tipo_Sensor" + ":" + str(tipo_sensor) + "|" + "alerta:1"
		#print (string)
		my_send_servidor (tcp_servidor, id_controlador, tipo_local_controlador, string )
# Faz o controle do sensor de temperatura
def sensor_temperatura (dicionario_sensor, id_sensor, tipo_sensor, valor_sensor, lista_servidor):
	if (id_sensor, tipo_sensor) in dicionario_sensor.keys():
		dicionario_sensor[id_sensor, tipo_sensor][3] = date.datetime.now()
		if (mudaca_estado (dicionario_sensor, id_sensor, tipo_sensor, valor_sensor)):
			trata_sensor_temperatura(dicionario_sensor, id_sensor, tipo_sensor, lista_servidor)
	else:
		print ('Sensor de temperatura',id_sensor, 'conectado!')
		insere_dicionario (dicionario_sensor, id_sensor, tipo_sensor, valor_sensor)
		trata_sensor_temperatura(dicionario_sensor, id_sensor, tipo_sensor, lista_servidor)
# Faz o primeiro tratamento de mensagem recebida
def conectado(connect, cliente, interval, dicionario_sensor, lista_servidor):
	while True:
		msg = my_recv(connect)
		if (not msg):
			break
		id_sensor, tipo_sensor, valor_sensor = msg 
		if (cliente != None):
			
			print ("Mensagem de sensor recebida!")
			if (tipo_sensor == 1):
				sensor_presenca(interval, dicionario_sensor, id_sensor, tipo_sensor, valor_sensor, lista_servidor)
			elif (tipo_sensor == 2):
				sensor_luminosidade(dicionario_sensor, id_sensor, tipo_sensor, valor_sensor, lista_servidor)
			elif (tipo_sensor == 3):
				sensor_temperatura(dicionario_sensor, id_sensor, tipo_sensor, valor_sensor, lista_servidor)
			else:
				print ("Tipo de sensor não identificado.")
		print (" ")			
	connect.close()
	_thread.exit()
# Desempacotamento da mensagem
def my_recv(socket):	
	try:	
		msg = socket.recv(structsize)
		#print (msg)
		return struct.unpack('!IHe', msg)
	except ConnectionResetError:
		print ('Erro! Sensor desconectado!')
		return False
# Desliga equipamentos em um timer
def set_interval_off(interval, dicionario_sensor):
    print ('Chamando timer para desligar equipamentos.')    
    def set_timer(wrapper):
        wrapper.timer = Timer(interval, wrapper)
        wrapper.timer.start()

    def wrapper():
        desliga_equipamento(dicionario_sensor)
        #set_timer(wrapper) - Tirar o comentario dessa parte se eu quiser uma função recursiva

    set_timer(wrapper)
    return wrapper
# Timer para verificar recepcao de mensagens
def set_interval_sensor(interval, dicionario_sensor, tempo_maximo, parametro_defeito):
    
    def set_timer(wrapper):
        wrapper.timer = Timer(interval, wrapper)
        wrapper.timer.start()

    def wrapper():
        verifica_intervalo(dicionario_sensor, tempo_maximo, parametro_defeito)
        set_timer(wrapper)

    set_timer(wrapper)
    return wrapper
# Variavel que verifica sensor defeituoso
interval_monitor_sensor = set_interval_sensor(mensagem_interval, dicionario_sensor, tempo_maximo, parametro_defeito)
# Programa principal Controlador
tcp_sensor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
origem_sensor = (HOST_SENSOR, PORT_SENSOR)
tcp_sensor.bind(origem_sensor)
tcp_sensor.listen(1)
#------------------------FIM-DO-CONTROLADOR-SENSOR------------------------#
#Função para conferir se há sensores ativos no dicionario
def confere_sensores(dicionario_sensor, parametro):
	for i in dicionario_sensor.keys():
		if (dicionario_sensor[i][5] == parametro and dicionario_sensor[i][1] != 1):
			return True

#Funcao para formatação da mensagem
def mensagem_format (id_controlador, tipo_local_controlador, msg_send):
	mask_format = '!If' + str(len(msg_send.encode())) + 's'
	mensagem = struct.pack(mask_format, id_controlador, tipo_local_controlador, msg_send.encode())
	return mensagem

#Funcao formatação de mensagem send
def mensagem_send (id_sensor, tipo_sensor):
	msg = "ID_Sensor:" + str(id_sensor) + "|" + "Tipo_Sensor:" + str(tipo_sensor) + "|" + "alerta:2"
	return msg

#Funcao que trata mensagens recebidas do servidor
def servidor_msg (dia_util, timestamp_servidor, mensagem, lista_servidor, dicionario_sensor):
	if  (str(mensagem) == "None"):
		print ("Primeira mensagem do servidor recebida!")
		print ("Dia útil:", dia_util)
		print ("Data e Hota:", datetime.fromtimestamp(timestamp_servidor))
		if (int(dia_util) == 1):
			lista_servidor[0] = True
	else:
		msg = mensagem
		mensagem = msg.split("|")
		if "comando:0" in mensagem:
			lista_servidor[0] = False
			#print (mensagem[0])
			if (confere_sensores(dicionario_sensor, 1)):	
				print ("Desligando todos os equipamentos!")
				desliga_equipamento(dicionario_sensor)
		if "comando:1" in mensagem:
			lista_servidor[0] = True
			if (confere_sensores(dicionario_sensor, 0) and verifica_presenca(dicionario_sensor)):	
				print ("Ligando todos os equipamentos!")
				liga_equipamento(dicionario_sensor, lista_servidor)
		if "controle:None" in mensagem:
			print ("Mensagem controle do servidor recebida!")
			print ("Dia útil:", dia_util)
			print ("Data e Hota:", datetime.fromtimestamp(timestamp_servidor))

#Funcao de empacotamento e envio de da mensagem para o servidor
def my_send_servidor (socket, id_controlador, tipo_local_controlador, msg_send):
	try:
		msg = mensagem_format(id_controlador, tipo_local_controlador, msg_send)
		print ("Enviando mensagem.")
		socket.send (msg)
	except ConnectionResetError:
		return False

#Desempacotamento da mensagem do servidor
def my_recv_servidor(socket):	
	try:	
		msg = socket.recv(max_pack_size)
		pack_size = len(msg) - structsize
		mask_format = '!If' + str(pack_size) + 's'
			
		return struct.unpack(mask_format, msg)
	except ConnectionResetError:
		print ('Erro! Servidor desconectado!')
		return False

#Função que trata conexão servidor-controlador
def conectado_servidor(connect, lista_servidor, dicionario_sensor):
	while True:
		msg = my_recv_servidor(connect)
		if (not msg):
			break
		dia_util, timestamp_servidor, mensagem = msg

		servidor_msg (dia_util, timestamp_servidor, mensagem.decode(), lista_servidor, dicionario_sensor)
		
		print (" ")
	connect.close()
	_thread.exit()

def set_interval_servidor(interval, connect, id_controlador, tipo_local_controlador, msg_send):
    
	def set_timer(wrapper):
		wrapper.timer = Timer(interval, wrapper)
		wrapper.timer.start()

	def wrapper():
		print ("Enviando mensagem de controle ao servidor.")
		my_send_servidor (connect, id_controlador, tipo_local_controlador, msg_send)
		set_timer(wrapper)

	set_timer(wrapper)
	return wrapper

#Programa principal Servidor
tcp_servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
dest_servidor = (HOST_SERVIDOR, PORT_SERVIDOR)
tcp_servidor.connect(dest_servidor)
# Variavel que envia mensagem de controle ao servidor
interval_monitor_servidor = set_interval_servidor(mensagem_interval_servidor, tcp_servidor, id_controlador, tipo_local_controlador, "controle:1")
#------------------------FIM-DO-CONTROLADOR-SERVIDOR------------------------#

my_send_servidor (tcp_servidor, id_controlador, tipo_local_controlador, msg_send)

#Mensagens de inicio do programa
print ("Controlador Iniciado.")
print ("Aluno: Mateus Schineider")
print ("ID Controlador:", id_controlador)
print ("Tipo local:", tipo_local_controlador)
print(" ")

#Verifica recepcao de novas mensagens
while True:
	_thread.start_new_thread(conectado_servidor, tuple([tcp_servidor, lista_servidor, dicionario_sensor]))
	connect, cliente = tcp_sensor.accept()	
	_thread.start_new_thread(conectado, tuple([connect, cliente, desliga_interval, dicionario_sensor, lista_servidor]))

tcp_servidor.close()
tcp_sensor.close()





