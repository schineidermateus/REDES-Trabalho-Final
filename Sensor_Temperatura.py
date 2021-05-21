import socket
import struct
import time
from datetime import datetime
from threading import Timer
import configparser as cfg

config = cfg.ConfigParser()
config.read ('temperatura.ini')

HOST = config.get ('sensor_ipcfg', 'ip_dest')    # Endereco IP do CL
PORT = config.getint ('sensor_ipcfg', 'port')            # Porta do CL

def tipo_mensagem (valor):
	return valor != None

# Campos da mensagem
#id_sensor = int(input("ID:"))
id_sensor = config.getint ('sensor_cfg', 'id_sensor')
tipo_sensor = config.getint ('sensor_cfg', 'tipo_sensor')
print ('Sensor de temperatura: ', tipo_mensagem(tipo_sensor))
print ('ID do sensor: ', id_sensor)
valor_sensor = float(input("Entre com o valor do sensor: "))

mensagem_interval = config.getint ('sensor_cfg', 'mensagem_interval') #mensagem de controle

# Funcao de empacotamento e envio de da mensagem
def my_send (socket, id_sensor, tipo_sensor, valor_sensor):
	try:
		msg = struct.pack('!IHe', id_sensor, tipo_sensor, float (valor_sensor))
		#print (msg)
		socket.send (msg)
	except ConnectionResetError:
		return False

def set_interval(function, interval):
    def set_timer(wrapper):
        wrapper.timer = Timer(interval, wrapper)
        wrapper.timer.start()

    def wrapper():
        function()
        set_timer(wrapper)
    

    set_timer(wrapper)
    return wrapper
	
def mensagem_controle():
	my_send (tcp, id_sensor, tipo_sensor, valor_sensor)

def atualiza_valor (valor_sensor):
	valor = input("Valor sensor: ")
	
	if (valor_sensor != valor):
		valor_sensor = valor
	return valor_sensor

	
# Inicio do programa	
# Ativando um alarme para a mensagem_controle

interval_monitor = set_interval(mensagem_controle, mensagem_interval) 

tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
dest = (HOST, PORT)
tcp.connect(dest)

my_send (tcp, id_sensor, tipo_sensor, valor_sensor)

teste_valor = 0

while (True):
	teste_valor = atualiza_valor(valor_sensor)
	if valor_sensor != teste_valor:
		valor_sensor = teste_valor
		my_send (tcp, id_sensor, tipo_sensor, valor_sensor)

	
tcp.close()
