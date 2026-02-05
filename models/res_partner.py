# -*- encoding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import requests
import logging
import time
import unicodedata
from . import servicio_busqueda

_logger = logging.getLogger(__name__)


def getDatosDNI(ditrict_obj, dni, tipo_busqueda, token):
    try:
        nombre = ''
        if tipo_busqueda == 'apiperu':
            nombre = servicio_busqueda.get_dni_apiperu(token, dni)
        elif tipo_busqueda == 'apimigo':
            nombre = servicio_busqueda.get_dni_apimigo(token, dni)
        elif tipo_busqueda == 'apinet':
            nombre = servicio_busqueda.get_dni_apinet(token, dni)
        print("-----------------------------------resultado----------------------------------------------------")
        print(nombre)

        dist_id = ditrict_obj.search(
            [('name_simple', '=ilike', 'LIMA'), ('city_id', '!=', False)], limit=1)
        if not dist_id:
            dist_id = ditrict_obj.search(
                [('name', '=', 'Lima'), ('city_id', '!=', False)], limit=1)

        rpt = {
            'names': nombre,
            'district_code': dist_id.code,
            'province_code': dist_id.city_id.l10n_pe_code,
            'department_code': dist_id.city_id.state_id.code,
            'district_id': dist_id.id,
            'province_id': dist_id.city_id.id,
            'department_id': dist_id.city_id.state_id.id,
            'direccion': '-',
            'distrito': dist_id.name,
            'provincia': dist_id.city_id.state_id.name,
        }
        return rpt
    except Exception as e:
        return ""


def get_data_doc_number(ditrict_obj, tipo_doc, numero_doc, tipo_busqueda, token, format='json'):
    print("DATOS DE INGRESO------------------------------------------------------")
    print(tipo_doc)
    print(numero_doc)
    print(tipo_busqueda)
    print(token)
    if tipo_doc == "dni" or tipo_doc == "01" or tipo_doc == "1":
        res = {'error': False, 'message': 'OK', 'data': {'success': True,
                                                         'data': getDatosDNI(ditrict_obj, numero_doc, tipo_busqueda, token)}}
        return res

    d = {}
    if tipo_busqueda == 'apiperu':
        d = servicio_busqueda.get_ruc_apiperu(token, numero_doc)
    elif tipo_busqueda == 'apimigo':
        d = servicio_busqueda.get_ruc_apimigo(token, numero_doc)
    elif tipo_busqueda == 'apinet':
        d = servicio_busqueda.get_ruc_apinet(token, numero_doc)
    print("---------------------DATA DE LA BUSQUEDA--------------------------")
    print(d)
    if d['error'] == True:
        return {'error': True, 'message': 'No se pudo completar la operacion', 'data': {}}

    dist_id = False
    if 'ubigeo' in d:
        ubigeo = d['ubigeo']
        dist_id = ditrict_obj.search([('code', '=', ubigeo)], limit=1)
    else:
        distrito = unicodedata.normalize('NFKD', d['distrito']).encode(
            'ASCII', 'ignore').strip().upper().decode()
        provincia = unicodedata.normalize('NFKD', d['provincia']).encode(
            'ASCII', 'ignore').strip().upper().decode()
        dist_id = ditrict_obj.search(
            [('name_simple', '=ilike', distrito), ('city_id', '!=', False)])
        if len(dist_id) < 1:
            return {'error': True, 'message': 'No se pudo ubicar el codigo de distrito', 'data': {}}
        elif len(dist_id) > 1:
            dist_id = ditrict_obj.search(
                [('name_simple', '=ilike', distrito), ('city_id.name_simple', '=ilike', provincia)])
        if len(dist_id) > 1:
            return {'error': True, 'message': 'No se pudo establecer el codigo de distrito, mas de una opcion encontrada', 'data': {}}
        elif len(dist_id) < 1:
            return {'error': True, 'message': 'No se pudo ubicar el codigo de distrito, se perdio en la validacion '+d['distrito']+' '+d['provincia']+' '+d['departamento'], 'data': {}}

    res = {'error': True,
           'message': 'Error al construir mensaje de retorno', 'data': {}}

    if dist_id:
        data_json = {
            'success': True,
            'data': {
                'razonSocial': d['razonSocial'],
                'district_code': dist_id.code,
                'province_code': dist_id.city_id.l10n_pe_code,
                'department_code': dist_id.city_id.state_id.code,
                'district_id': dist_id.id,
                'province_id': dist_id.city_id.id,
                'department_id': dist_id.city_id.state_id.id,
                'direccion': d['direccion'],
                'distrito': dist_id.name,
                'provincia': dist_id.city_id.name,
                'condicion': d['condicion'],
                'estado': d['estado']
            }
        }
        if 'buen_contribuyente' in d and d['buen_contribuyente']:
            data_json['data']['buen_contribuyente'] = d['buen_contribuyente']
            data_json['data']['a_partir_del'] = d['a_partir_del']
            data_json['data']['resolucion'] = d['resolucion']

        res = {'error': False, 'message': None, 'data': data_json}
    return res


class Partner(models.Model):
    _inherit = 'res.partner'

    l10n_latam_identification_type_id = fields.Many2one(
        # lambda self: self.env.ref('l10n_pe.it_RUC')
        'l10n_latam.identification.type', default=False)
    doc_type = fields.Char(
        related="l10n_latam_identification_type_id.l10n_pe_vat_code")
    doc_number = fields.Char("Numero de documento", related="vat", store=True)
    commercial_name = fields.Char("Nombre commercial", default="-")
    legal_name = fields.Char("Nombre legal", default="-")
    state_partner = fields.Selection(
        servicio_busqueda.STATE, string='Estado', default="ACTIVO")
    state_sunat = fields.Selection(
        servicio_busqueda.STATE, string='Estado', default="ACTIVO")
    condition = fields.Selection(
        servicio_busqueda.CONDITION, string='Condicion', default='HABIDO')
    is_validate = fields.Boolean("Está validado")
    last_update = fields.Datetime("Última actualización")
    buen_contribuyente = fields.Boolean('Buen contribuyente')
    a_partir_del = fields.Date('A partir del')
    resolucion = fields.Char('Resolución')
    zip = fields.Char(store=True, readonly=False)

    busqueda_automatica = fields.Boolean("Busqueda automatica", default=True,
                                         help="Si esta marcado cuando ingrese o cambie el numero ruc o dni se buscaran sus datos en la pagina de SUNAT")

    def consulta_datos_simple(self, tipo_documento, nro_documento):
        # res = {'error': True, 'message': None, 'data': {}}

        res_partner = self.search([('vat', '=', nro_documento)]).exists()
        if res_partner:
            if tipo_documento == "dni" or tipo_documento == "01" or tipo_documento == "1":
                data_json = {
                    'success': True,
                    'data': {
                        'names': res_partner.display_name,
                    }
                }
            else:
                data_json = {
                    'success': True,
                    'data': {
                        'razonSocial': res_partner.display_name,
                    }
                }
            datos = {'error': False, 'message': None, 'data': data_json}
        else:
            datos = self.consulta_datos(tipo_documento, nro_documento, 'json')
        return datos

    # Para usar la funcion de busqueda desde llamadas javascript
    @api.model
    def consulta_datos(self, tipo_documento, nro_documento, format='json', id_reg=False):
        res = {'error': True, 'message': None, 'data': {}}
        res_partner = self.search([('vat', '=', nro_documento)]).exists()
        # Si el nro. de doc. ya existe
        if res_partner and res_partner.id != id_reg:
            res['message'] = 'Nro. doc. ya existe'
            return res

        token = ''
        tipo_busqueda = 'apiperu'
        if self.company_id:
            token = self.company_id.token_api
            tipo_busqueda = self.company_id.busqueda_ruc_dni
        else:
            token = self.env.company.token_api
            tipo_busqueda = self.env.company.busqueda_ruc_dni

        try:
            ditrict_obj = self.env['l10n_pe.res.city.district']
            res = get_data_doc_number(ditrict_obj, tipo_documento, str(
                nro_documento), tipo_busqueda, token, format='json')
        except Exception as e:
            res['message'] = 'Error en la conexion: '+str(self.company_id)
            return res

        return res

    # Funcion 2 Para usar la funcion de busqueda desde llamadas javascript
    @api.model
    def consulta_datos_completo(self, tipo_documento, nro_documento, format='json'):
        res = {'error': True, 'message': None, 'data': {}, 'registro': False}
        res_partner = self.search([('vat', '=', nro_documento)], limit=1)
        # Si el nro. de doc. ya existe
        if res_partner:
            res['message'] = 'Nro. doc. ya existe'
            res['error'] = False
            res['registro'] = res_partner
            return res

        token = ''
        tipo_busqueda = 'apiperu'
        if self.company_id:
            token = self.company_id.token_api
            tipo_busqueda = self.company_id.busqueda_ruc_dni
        else:
            token = self.env.company.token_api
            tipo_busqueda = self.env.company.busqueda_ruc_dni
        try:
            ditrict_obj = self.env['l10n_pe.res.city.district']
            res = get_data_doc_number(ditrict_obj, tipo_documento, str(
                nro_documento), tipo_busqueda, token, format='json')
        except Exception as e:
            res['message'] = 'Error en la conexion: '+str(self.company_id)
            return res

        return res

    @api.constrains("vat")
    def check_vat(self):
        if not self.parent_id:
            for partner in self:
                doc_type = partner.l10n_latam_identification_type_id.l10n_pe_vat_code
                if not doc_type and not partner.vat:
                    continue
                elif doc_type == "0":
                    continue
                elif doc_type and not partner.vat:
                    raise ValidationError(
                        "Ingrese el número de documento %s" % doc_type)
                vat = partner.vat
                if doc_type == '6':
                    check = self.validate_ruc(vat)
                    if not check:
                        raise ValidationError('El RUC ingresado es incorrecto')
                if self.search_count([('company_id', '=', partner.company_id.id), ('l10n_latam_identification_type_id.l10n_pe_vat_code', '=', doc_type), ('vat', '=', partner.vat)]) > 1:
                    raise ValidationError(
                        'El número de documento ya existe y viola la restricción de campo único')

    @api.onchange('l10n_latam_identification_type_id')
    def onchange_company_type(self):
        doc_type = self.l10n_latam_identification_type_id.l10n_pe_vat_code
        if doc_type == "6":
            self.company_type = 'company'
        else:
            self.company_type = 'person'
        super(Partner, self).onchange_company_type()

    @staticmethod
    def validate_ruc(vat):
        return True
        factor = '5432765432'
        sum = 0
        dig_check = False
        if len(vat) != 11:
            return False
        try:
            int(vat)
        except ValueError:
            return False
        for f in range(0, 10):
            sum += int(factor[f]) * int(vat[f])
        subtraction = 11 - (sum % 11)
        if subtraction == 10:
            dig_check = 0
        elif subtraction == 11:
            dig_check = 1
        else:
            dig_check = subtraction
        if not int(vat[10]) == dig_check:
            return False
        return True

    @api.onchange("vat", "l10n_latam_identification_type_id")
    @api.depends("l10n_latam_identification_type_id", "vat", "zip")
    def _doc_number_change(self):
        for record in self:
            _logger.info(
                "🔎 [ONCHANGE] Ejecutando _doc_number_change para partner %s", record.id)
            _logger.info("➡️ vat=%s, tipo_doc=%s, zip=%s, busqueda_automatica=%s",
                         record.vat, record.l10n_latam_identification_type_id, record.zip, record.busqueda_automatica)

            if record.l10n_pe_district:
                record.zip = str(record.l10n_pe_district.code)
                _logger.info("🏷️ Asignado ZIP desde distrito: %s", record.zip)

            rpt = record._validar_tipo_doc()
            _logger.info("📋 Resultado _validar_tipo_doc(): %s", rpt)

            vat = record.vat
            if record.busqueda_automatica is False:
                _logger.info(
                    "⏩ Busqueda automática desactivada, solo sincronizando ZIP si falta...")
                if record.l10n_pe_district and not record.zip:
                    record.write({"zip": record.l10n_pe_district.code})
                    record.zip = record.l10n_pe_district.code
                    _logger.info(
                        "✅ ZIP actualizado manualmente: %s", record.zip)
                return

            if not vat:
                _logger.warning("⚠️ No hay VAT, se termina aquí")
                return

            # Obtener token y método de búsqueda
            token = ""
            tipo_busqueda_ruc_dni = "apiperu"
            if record.company_id:
                token = record.company_id.token_api
                tipo_busqueda_ruc_dni = record.company_id.busqueda_ruc_dni
            else:
                token = record.env.company.token_api
                tipo_busqueda_ruc_dni = record.env.company.busqueda_ruc_dni

            _logger.info("🔑 Token: %s, Tipo busqueda: %s",
                         token, tipo_busqueda_ruc_dni)

            if vat and record.l10n_latam_identification_type_id:
                vat_type = record.l10n_latam_identification_type_id.l10n_pe_vat_code
                _logger.info("📌 VAT Type: %s", vat_type)

                # === DNI ===
                if vat_type == "1":
                    _logger.info("🪪 Procesando DNI: %s", vat)
                    if len(vat) != 8:
                        _logger.error("❌ DNI inválido (no tiene 8 dígitos)")
                        raise UserError("El DNI ingresado es incorrecto")

                    response = False
                    try:
                        if tipo_busqueda_ruc_dni == "apiperu":
                            response = servicio_busqueda.get_dni_apiperu(
                                token, vat.strip())
                        elif tipo_busqueda_ruc_dni == "apimigo":
                            response = servicio_busqueda.get_dni_apimigo(
                                token, vat.strip())
                        elif tipo_busqueda_ruc_dni == "apinet":
                            response = servicio_busqueda.get_dni_apinet(
                                token, vat.strip())
                            _logger.info(
                                "🌐 Respuesta API.NET DNI: %s", response)
                        _logger.info("✅ Respuesta servicio DNI: %s", response)
                    except Exception as e:
                        _logger.exception("❌ Excepción buscando DNI: %s", e)
                        response = False

                    if response:
                        record.name = response
                        record.company_type = "person"
                        record.is_validate = True
                        _logger.info(
                            "🎉 Nombre asignado desde servicio: %s", response)

                    # Forzar persona natural en Perú
                    record.company_type = "person"
                    record.country_id = 173
                    _logger.info("🇵🇪 País forzado a Perú")

                    # Default: Lima
                    district = record.env["l10n_pe.res.city.district"].search([
                        ("name", "ilike", "Lima"),
                        ("city_id.name", "ilike", "Lima")
                    ])
                    _logger.info("🔍 Búsqueda de distrito Lima: %s", district)

                    if len(district) == 1:
                        record.l10n_pe_district = district.id
                        record.city_id = district.city_id.id
                        record.state_id = district.city_id.state_id.id
                        _logger.info("📍 Distrito Lima asignado")
                    elif len(district) == 0:
                        province = record.env["res.city"].search(
                            [("name", "ilike", "Lima")])
                        if len(province) == 1:
                            record.city_id = province.id
                            record.state_id = province.state_id.id
                            _logger.info("📍 Provincia Lima asignada")
                    else:
                        province = record.env["res.city"].search(
                            [("name", "ilike", "Lima")])
                        if len(province) == 1:
                            record.city_id = province.id
                            district = record.env["l10n_pe.res.city.district"].search([
                                ("name", "=ilike", "Lima"),
                                ("city_id.name", "ilike", record.city_id.name)
                            ])
                            if len(district) == 1:
                                record.l10n_pe_district = district.id
                                _logger.info("📍 Distrito exacto Lima asignado")

                # === RUC ===
                elif vat_type == "6":
                    _logger.info("🏢 Procesando RUC: %s", vat)
                    if not record.validate_ruc(vat):
                        raise UserError("El RUC ingresado es incorrecto")

                    vals = {}
                    for x in range(3):
                        _logger.info("🔄 Intento #%s para buscar RUC", x + 1)
                        if tipo_busqueda_ruc_dni == "apiperu":
                            vals = servicio_busqueda.get_ruc_apiperu(
                                token, vat)
                        elif tipo_busqueda_ruc_dni == "apimigo":
                            vals = servicio_busqueda.get_ruc_apimigo(
                                token, vat)
                        elif tipo_busqueda_ruc_dni == "apinet":
                            vals = servicio_busqueda.get_ruc_apinet(token, vat)
                        _logger.info("📥 Respuesta servicio RUC: %s", vals)

                        if vals.get("error") is False:
                            break
                        elif x == 2:
                            raise UserError(vals.get("message"))

                    if vals.get("error") is True:
                        raise UserError(vals.get("message"))

                    if vals:
                        record.commercial_name = vals.get("razonSocial")
                        record.legal_name = vals.get("razonSocial")
                        record.name = vals.get("razonSocial")
                        record.street = vals.get("direccion", False)
                        record.company_type = "company"
                        record.state_sunat = vals.get("estado", False)
                        record.condition = vals.get("condicion", False)
                        record.is_retenedor = bool(vals.get("retencion"))
                        record.is_validate = True
                        _logger.info(
                            "🎉 Datos de RUC aplicados: %s", vals.get("razonSocial"))

                        if vals.get("buen_contribuyente", False):
                            record.buen_contribuyente = vals.get(
                                "buen_contribuyente")
                            record.a_partir_del = vals.get("a_partir_del")
                            record.resolucion = vals.get("resolucion")
                            _logger.info("🏅 Buen contribuyente detectado")

                        ditrict_obj = record.env["l10n_pe.res.city.district"]
                        district = False
                        if vals.get("ubigeo"):
                            ubigeo = vals.get("ubigeo")
                            district = ditrict_obj.search(
                                [("code", "=", ubigeo)], limit=1)
                            _logger.info(
                                "📍 Distrito por ubigeo %s: %s", ubigeo, district)
                        elif vals.get("distrito") and vals.get("provincia"):
                            distrito = unicodedata.normalize("NFKD", vals.get("distrito")).encode(
                                "ASCII", "ignore"
                            ).strip().upper().decode()
                            district = ditrict_obj.search([
                                ("name_simple", "=ilike", distrito),
                                ("city_id", "!=", False)
                            ])
                            _logger.info(
                                "📍 Distrito por nombre %s: %s", distrito, district)

                            if len(district) < 1:
                                raise Warning(
                                    "No se pudo ubicar el codigo de distrito " + distrito)
                            elif len(district) > 1:
                                district = ditrict_obj.search([
                                    ("name_simple", "=ilike", distrito),
                                    ("city_id.name_simple",
                                     "=ilike", vals.get("provincia"))
                                ])
                            if len(district) > 1:
                                raise Warning(
                                    "Más de un distrito encontrado para " + distrito)
                            elif len(district) < 1:
                                raise Warning(
                                    "No se pudo ubicar distrito " + distrito)

                        if district:
                            record.country_id = district.city_id.state_id.country_id.id
                            record.state_id = district.city_id.state_id.id
                            record.city_id = district.city_id.id
                            record.l10n_pe_district = district.id
                            record.zip = str(district.code)
                            _logger.info(
                                "✅ Ubicación asignada desde distrito: %s", district)

            # Sincronizar ZIP si falta
            if record.l10n_pe_district and not record.zip:
                record.write({"zip": record.l10n_pe_district.code})
                record.zip = record.l10n_pe_district.code
                _logger.info(
                    "📮 ZIP actualizado desde distrito: %s", record.zip)

    def _validar_tipo_doc(self):
        if self.vat:
            vat = len(self.vat) >= 1 and self.vat or ""
            doc_type = self.l10n_latam_identification_type_id.l10n_pe_vat_code or False

            if vat:
                if doc_type == "0":
                    self.doc_type = "0"
                elif doc_type == "1":
                    if len(vat) != 8:
                        raise UserError('El DNI ingresado es incorrecto')
                    self.doc_type = "1"
                elif doc_type == "4":
                    self.doc_type = "4"
                elif doc_type == "6":
                    if not self.validate_ruc(vat):
                        raise UserError('El RUC ingresado es incorrecto')
                    self.doc_type = "6"
                elif doc_type == "A":
                    self.doc_type = "A"

            else:
                self.doc_type = "7"

    @api.onchange('l10n_pe_district')
    def _onchange_l10n_pe_district(self):
        if self.l10n_pe_district:
            self.city_id = self.l10n_pe_district.city_id
            self.zip = str(self.l10n_pe_district.code)

    @api.model
    def change_commercial_name(self):
        partner_ids = self.search(
            [('commercial_name', '!=', '-'), ('doc_type', '=', '6')])
        for partner_id in partner_ids:
            partner_id.update_document()

    def update_document(self):
        self._doc_number_change()
        self._onchange_l10n_pe_district()

    @api.onchange('city_id')
    def _onchange_l10n_pe_city_id(self):
        if self.l10n_pe_district and not self.zip:
            self.zip = self.l10n_pe_district.code
        if self.city_id and self.l10n_pe_district.city_id and self.l10n_pe_district.city_id != self.city_id:
            self.l10n_pe_district = False


class ResUsers(models.Model):
    _inherit = 'res.users'

    l10n_latam_identification_type_id = fields.Many2one(
        'l10n_latam.identification.type', default=False)

    @api.constrains("doc_number")
    def check_doc_number(self):
        return

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.update({'l10n_latam_identification_type_id': False})

        return super(ResUsers, self).create(vals_list)
