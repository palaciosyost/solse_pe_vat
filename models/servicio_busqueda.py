# -*- encoding: utf-8 -*-
import requests
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)

STATE = [('ACTIVO', 'ACTIVO'),
		 ('BAJA DE OFICIO', 'BAJA DE OFICIO'),
		 ('BAJA DEFINITIVA', 'BAJA DEFINITIVA'),
		 ('BAJA PROVISIONAL', 'BAJA PROVISIONAL'),
		 ('SUSPENSION TEMPORAL', 'BAJA PROVISIONAL'),
		 ('INHABILITADO-VENT.UN', 'INHABILITADO-VENT.UN'),
		 ('BAJA MULT.INSCR. Y O', 'BAJA MULT.INSCR. Y O'),
		 ('PENDIENTE DE INI. DE', 'PENDIENTE DE INI. DE'),
		 ('OTROS OBLIGADOS', 'OTROS OBLIGADOS'),
		 ('NUM. INTERNO IDENTIF', 'NUM. INTERNO IDENTIF'),
		 ('ANUL.PROVI.-ACTO ILI', 'ANUL.PROVI.-ACTO ILI'),
		 ('ANULACION - ACTO ILI', 'ANULACION - ACTO ILI'),
		 ('BAJA PROV. POR OFICI', 'BAJA PROV. POR OFICI'),
		 ('ANULACION - ERROR SU', 'ANULACION - ERROR SU')]

CONDITION = [('HABIDO', 'HABIDO'),
			 ('NO HABIDO', 'NO HABIDO'),
			 ('NO HALLADO', 'NO HALLADO'),
			 ('PENDIENTE', 'PENDIENTE'),
			 ('NO HALLADO SE MUDO D', 'NO HALLADO SE MUDO D'),
			 ('NO HALLADO NO EXISTE', 'NO HALLADO NO EXISTE'),
			 ('NO HALLADO FALLECIO', 'NO HALLADO FALLECIO'),
			 ('-', 'NO HABIDO'),
			 ('NO HALLADO OTROS MOT', 'NO HALLADO OTROS MOT'),
			 ('NO APLICABLE', 'NO APLICABLE'),
			 ('NO HALLADO NRO.PUERT', 'NO HALLADO NRO.PUERT'),
			 ('NO HALLADO CERRADO', 'NO HALLADO CERRADO'),
			 ('POR VERIFICAR', 'POR VERIFICAR'),
			 ('NO HALLADO DESTINATA', 'NO HALLADO DESTINATA'),
			 ('NO HALLADO RECHAZADO', 'NO HALLADO RECHAZADO')]

# ::::::::::::::::: Usando API de APIPERU.dev

def get_dni_apiperu(token, dni):
	endpoint = "https://apiperu.dev/api/dni/%s" % dni
	headers = {
		"Authorization": "Bearer %s" % token,
		"Content-Type": "application/json",
	}
	try:
		datos_dni = requests.get(endpoint, data={}, headers=headers)
		if datos_dni.status_code == 200:
			datos = datos_dni.json()
			return datos['data']['nombre_completo']
		else:
			return ""
	except Exception as e:
		_logger.info('algo salio mal en la busqueda dni con el apiperu')
		_logger.info(e)
		raise UserError('Algo salio mal en la busqueda dni con el apiperu')
		return ""

def get_ruc_apiperu(token, ruc):
	try:
		endpoint = "https://apiperu.dev/api/ruc/%s" % ruc
		headers = {
			"Authorization": "Bearer %s" % token,
			"Content-Type": "application/json",
		}
		datos_ruc = requests.get(endpoint, data={}, headers=headers)
		if datos_ruc.status_code == 200:
			datos_ruc = datos_ruc.json()
			ubigeo = datos_ruc['data']['ubigeo'][2]
			direccion = datos_ruc['data']['direccion_completa'] if 'direccion_completa' in datos_ruc['data'] else ''
			if not direccion:
				direccion = ''
			if not ubigeo:
				ubigeo = '-'
			datos = {
				'error': False, 
				'message': 'ok',
				'condicion': datos_ruc['data']['condicion'],
				'estado': datos_ruc['data']['estado'],
				'ubigeo': ubigeo if ubigeo != "-" else "150101",
				'direccion': direccion.split(',')[0],
				'razonSocial': datos_ruc['data']['nombre_o_razon_social'],
				'ruc': datos_ruc['data']['ruc'],
			}
			return datos
		else:
			return {'error': True, 'message': 'Error al intentar obtener datos'}
	except Exception as e:
		return {'error': True, 'message': str(e)}

# ::::::::::::::::: Usando API de migo.pe
def get_dni_apimigo(token, dni):
	endpoint = "https://api.migo.pe/api/v1/dni/"
	datos_consultar = {
		'dni': dni,
		'token': token
	}
	try:
		datos_dni = requests.post(url=endpoint, data=datos_consultar)
		if datos_dni.status_code == 200:
			datos = datos_dni.json()
			return datos['nombre']
		else:
			return ""
		print("------------------------DATOS--------------------------------")
		print(datos_dni)

	except Exception as e:
		_logger.info('algo salio mal en la busqueda dni')
		_logger.info(e)
		return ""

def get_ruc_apimigo(token, ruc):
	endpoint = "https://api.migo.pe/api/v1/ruc/"
	retencion = "https://api.migo.pe/api/v1/ruc/agentes-retencion"
	datos_consultar = {
		'ruc': ruc,
		'token': token
	}
	datos = ""
	try:
		datos_request = requests.post(url=endpoint, data=datos_consultar)
		data_retencion = requests.post(url=retencion, data=datos_consultar)
		_logger.info("------------------------DATOS--------------------------------")
		_logger.info(datos_request.json())
		_logger.info(data_retencion.json())
		if datos_request.status_code == 200 and data_retencion.status_code == 200:
			datos_ruc = datos_request.json()
			datos_retencion = data_retencion.json()
			ubigeo = datos_ruc['ubigeo']
			direccion = datos_ruc['direccion_simple'] or ''
			datos = {
					'error': False, 
					'message': 'ok',
					'condicion': datos_ruc['condicion_de_domicilio'],
					'estado': datos_ruc['estado_del_contribuyente'],
					'ubigeo': ubigeo if ubigeo != "-" else "150101",
					'direccion': direccion,
					'razonSocial': datos_ruc['nombre_o_razon_social'],
					'ruc': datos_ruc['ruc'],
					"retencion": datos_retencion['success']
			}
			datos_buen_contribuyente = es_buen_contribuyente(token, ruc)
			if datos_buen_contribuyente['buen_contribuyente']:
				datos['buen_contribuyente'] = datos_buen_contribuyente['buen_contribuyente']
				datos['a_partir_del'] = datos_buen_contribuyente['a_partir_del']
				datos['resolucion'] = datos_buen_contribuyente['resolucion']
			else:
				datos['buen_contribuyente'] = False
				datos['a_partir_del'] = ""
				datos['resolucion'] = ""
			return datos
		else:
			return {'error': True, 'message': 'No se pudo cargar'}

	except Exception as e:
		_logger.info('algo salio mal en la busqueda ruc')
		_logger.info(e)
		return {'error': True, 'message': 'No se pudo obtener una respuesta valida'}


def get_ruc_apinet(token, ruc):
	print("----------------SELECCIONES--------------------")
	print(token)
	print(ruc)
	endpoint = f'https://api.apis.net.pe/v2/sunat/ruc/full?numero={ruc}&token={token}'
	datos = {
	    'ruc': ruc,
	    'buen_contribuyente': False,
	    'error': None,
	}
	try:
		datos_request = requests.get(url=endpoint, timeout=10)
		if datos_request.status_code == 200:
			datos_ruc = datos_request.json()
			ubigeo = datos_ruc['ubigeo']
			direccion = datos_ruc['direccion'] or ''
			datos = {
				'error': False, 
				'message': 'ok',
				'condicion': datos_ruc['condicion'],
				'estado': datos_ruc['estado'],
				'ubigeo': ubigeo if ubigeo != "-" else "150101",
				'direccion': direccion ,
				'razonSocial': datos_ruc['razonSocial'],
				'ruc': datos_ruc['numeroDocumento'],
			}
			print("------------------------DATOS--------------------------------")
			print(datos_ruc)
			print(datos)
			datos_buen_contribuyente = es_buen_contribuyente(token, ruc)
			if datos_buen_contribuyente['buen_contribuyente']:
				datos['buen_contribuyente'] = datos_buen_contribuyente['buen_contribuyente']
				datos['a_partir_del'] = datos_buen_contribuyente['a_partir_del']
				datos['resolucion'] = datos_buen_contribuyente['resolucion']
			else:
				datos['buen_contribuyente'] = False
				datos['a_partir_del'] = ""
				datos['resolucion'] = ""
			print("------------------------DATOS--------------------------------")
			print(datos)
			return datos
		else:
			return {'error': True, 'message': 'No se pudo cargar'}

	except Exception as e:
		_logger.info('algo salio mal en la busqueda ruc')
		_logger.info(e)
		return {'error': True, 'message': 'No se pudo obtener una respuesta valida'}


def get_dni_apinet(token, dni):
	endpoint = f'https://api.apis.net.pe/v2/reniec/dni?numero={dni}&token={token}'
	try:
		datos_request = requests.get(url=endpoint, timeout=10)
		if datos_request.status_code == 200:
			datos = datos_request.json()
			print("--------------------------------DATOS DE LA CONSULTA--------------------------------")
			print(datos)
			_logger.info(datos)
			nombre = datos["nombreCompleto"] or 'EL NOMNRE NO SE LOGRA EXTRAER'
			return nombre
		else:
			return ""
	except Exception as e:
		_logger.info('algo salio mal en la busqueda dni')
		_logger.info(e)
		return ""


def es_buen_contribuyente(token, ruc):
	endpoint = "https://api.migo.pe/api/v1/ruc/buenos-contribuyentes"
	datos_consultar = {
		'ruc': ruc,
		'token': token
	}
	datos = {
		'buen_contribuyente': False,
	}
	try:
		datos_request = requests.post(url=endpoint, data=datos_consultar)
		if datos_request.status_code == 200:
			datos = datos_request.json()
			datos['buen_contribuyente'] = True
			return datos
	except Exception as e:
		pass
	return datos

"""
import requests
import logging
_logger = logging.getLogger(__name__)
fecha = "2020-12-02"
token = 'YjkJ4rBK1sMIvdkjVootZFbelG0fZccnNerDehCYHlQ5mqdpzApvk2cEXsZm'
datos = get_tipo_cambio_apiperu(token, fecha)
datos


import requests
import json
import logging
endpoint = "https://apiperu.dev/api/tipo_de_cambio"
fecha = "2020-12-02"
token = 'YjkJ4rBK1sMIvdkjVootZFbelG0fZccnNerDehCYHlQ5mqdpzApvk2cEXsZm'
headers_enviar = {
	"Authorization": "Bearer %s" % token,
	"Content-Type": "application/json"
}
datos_enviar = {"fecha": fecha}
datos_dni = requests.post(endpoint, data=datos_enviar, headers=headers_enviar)


if datos_dni.status_code == 200:
	datos = datos_dni.json()
	return datos['data']['nombre_completo']
else:
	return ""
"""

