# -*- coding: utf-8 -*-
from odoo import models, fields, api
import re
import requests
import xml.etree.ElementTree as ET
from odoo.exceptions import ValidationError
import zeep
from zeep.transports import Transport
import requests
import json

class ResPartner(models.Model):
    _inherit = "res.partner"


    def update_contacts(self):
        return True
    
    # @api.model_create_multi
    # def create(self,vals):
    #     company_type = False
    #     parent_id = False
    #     if'company_type' in vals:
    #         company_type = vals['company_type']
    #     if'parent_id' in vals:
    #         parent_id = vals['parent_id']
    #     if company_type == 'person' and parent_id:
    #         return super(ResPartner, self).create(vals)
    #     else:
    #         for rec in vals:
    #             if 'vat' in rec:
    #                 if rec['vat']:
    #                     vat = rec['vat'].replace('-', '')
    #                     vat = vat.upper()
    #                     rec['vat'] = vat
    #                     name = ""
    #                     address = ""
                        
    #                     if vat != 'CF' and vat != 'C/F' and vat != 'cf':   
    #                         name, address = self.nit_validation(vat)
    #                         if name != "":
    #                             rec['name'] = name.title()
    #                         if address != "":
    #                             rec['street'] = address.title()
                            
    #                 else:
    #                     raise ValidationError("Debe ingresar NIT.")

    #     return super(ResPartner, self).create(vals)

    
    def write(self, vals):
        for rec in self:
            company_type = rec.company_type
            parent_id = rec.parent_id

            if'company_type' in vals:
                company_type = vals['company_type']
            if'parent_id' in vals:
                parent_id = vals['parent_id']           

            if company_type == 'person' and parent_id:
                return super(ResPartner, rec).write(vals)
            else:
                if 'vat' in vals:
                    if vals['vat']:
                        vat = vals['vat'].replace('-', '')
                        vat = vat.upper()
                        vals['vat'] = vat
                        name = ""
                        address = ""
                        if vat != 'CF' and vat != 'C/F' and vat != 'cf':   
                            name, address = rec.nit_validation(vat)
                            if name != "":
                                vals['name'] = name.title()
                            if address != "":
                                vals['street'] = address.title()
                    else:
                        raise ValidationError("Debe ingresar NIT.")

                return super(ResPartner, rec).write(vals)
    
    def nit_validation(self, vat):
        name = ""
        address = ""
        vat = vat.replace("-", "")
        company_id = self.env.company
        
        if not company_id.nit_fel_certifier:
            raise ValidationError('Debe seleccionar el certificador a utilizar para validación de NIT')
        else:
            if not company_id.nit_fel_certifier_url:
                raise ValidationError('Debe ingresar la url del certificador a utilizar para validación de NIT')
            
            if company_id.nit_fel_certifier == 'g4s':
                
                url = company_id.nit_fel_certifier_url
                second_wsdl = url+'?wsdl'
                client = zeep.Client(wsdl=second_wsdl)
                requestor_id = company_id.requestor_id
                company_vat = company_id.vat
                request_data = {
                    'vNIT': vat,
                    'Entity': company_vat,
                    'Requestor': requestor_id,
                }
                service_response = client.service.getNIT(**request_data)
                
                if 'Response' in service_response:
                    if 'Result' in service_response['Response']:
                        print(service_response['Response']['Result'])
                        if not service_response['Response']['Result']:
                            raise ValidationError("El NIT que ingresó no es válido.")
                        else:
                            name = self.clean_name(service_response['Response']['nombre'])
                
                return name, address
            
            if company_id.nit_fel_certifier == 'infile':
                #url = "https://consultareceptores.feel.com.gt/rest/action"
                
                url = company_id.nit_fel_certifier_url
                
                headers = {'Content-Type': 'application/json'}
                
                json_body = {
                    "emisor_codigo": company_id.infile_user,
                    "emisor_clave": company_id.infile_key_certificate,
                    "nit_consulta": vat 
                }
                
                response = requests.post(url, json=json_body, headers=headers)
                
                if response.status_code == 200:
                    response_data = response.json()
                    
                    if 'nombre' in response_data:
                        name = response_data['nombre']
                        if isinstance(name, str):
                            name = self.clean_name(name)
                        else:
                            name = 'Error - %s' % (vat)
                    
                    if 'direccion_completa' in response_data:
                        address = response_data['direccion_completa']
                        if isinstance(address, str):
                            if address.isspace():
                                address = "Ciudad"
                        if not isinstance(address, str):
                            address = ""
                    else:
                        address = "Ciudad"
                    
                    if response_data['mensaje'] == "NIT no válido":
                        raise ValidationError("El NIT que ingresó no es válido.")
                    if response_data['mensaje'] == "Credenciales no registradas":
                        raise ValidationError("No ha registrado credenciales válidas, por favor verifique en su configuración")
    
                return name, address

    def action_nit_validate(self):
        if not self.vat:
            raise ValidationError('Debe ingresar un NIT a verificar')
        name, address = self.nit_validation(self.vat)
        vat = self.vat.replace('-', '')
        vat = vat.upper()
        if address != "":
            vals = {
                'name': name,
                'street': address,
                'vat': vat
            }
        else:
            vals = {
                'name': name,
                'vat': vat
            }
        self.write(vals)

    def clean_name(self, name):
        clean_name = re.compile(',')
        name = re.sub(clean_name, ' ',name)

        return name

    
    def action_massive_nit_validate(self):
        if not self.vat:
            raise ValidationError('Debe ingresar un NIT a verificar')
        name, address = self.massive_nit_validation(self.vat)
        vat = self.vat.replace('-', '')
        vat = vat.upper()
        if address != "":
            vals = {
                'name': name,
                'street': address,
                'vat': vat
            }
        else:
            vals = {
                'name': name,
                'vat': vat
            }
        self.write(vals)

    def clean_name(self, name):
        clean_name = re.compile(',')
        name = re.sub(clean_name, ' ',name)

        return name
    
    def massive_nit_validation(self, vat):
        name = ""
        address = ""
        vat = vat.replace("-", "")
        company_id = self.env.company
        
        if not company_id.nit_fel_certifier:
            raise ValidationError('Debe seleccionar el certificador a utilizar para validación de NIT')
        else:
            if not company_id.nit_fel_certifier_url:
                raise ValidationError('Debe ingresar la url del certificador a utilizar para validación de NIT')
            
            if company_id.nit_fel_certifier == 'g4s':
                
                url = company_id.nit_fel_certifier_url
                second_wsdl = url+'?wsdl'
                client = zeep.Client(wsdl=second_wsdl)
                requestor_id = company_id.requestor_id
                company_vat = company_id.vat
                request_data = {
                    'vNIT': vat,
                    'Entity': company_vat,
                    'Requestor': requestor_id,
                }
                service_response = client.service.getNIT(**request_data)
                
                if 'Response' in service_response:
                    if 'Result' in service_response['Response']:
                        print(service_response['Response']['Result'])
                        if not service_response['Response']['Result']:
                            raise ValidationError("El NIT que ingresó no es válido.")
                        else:
                            name = self.clean_name(service_response['Response']['nombre'])
                
                return name, address
            
            if company_id.nit_fel_certifier == 'infile':
                #url = "https://consultareceptores.feel.com.gt/rest/action"
                
                url = company_id.nit_fel_certifier_url
                
                headers = {'Content-Type': 'application/json'}
                
                json_body = {
                    "emisor_codigo": company_id.infile_user,
                    "emisor_clave": company_id.infile_key_certificate,
                    "nit_consulta": vat 
                }
                
                response = requests.post(url, json=json_body, headers=headers)
                
                if response.status_code == 200:
                    response_data = response.json()
                    
                    if 'nombre' in response_data:
                        name = response_data['nombre']
                        if isinstance(name, str):
                            name = self.clean_name(name)
                        else:
                            name = 'Error - %s' % (vat)
                    
                    if 'direccion_completa' in response_data:
                        address = response_data['direccion_completa']
                        if isinstance(address, str):
                            if address.isspace():
                                address = "Ciudad"
                        if not isinstance(address, str):
                            address = ""
                    else:
                        address = "Ciudad"
                    
                    if response_data['mensaje'] == "NIT no válido":
                        raise ValidationError("El NIT %s del contacto %s que ingresó no es válido." % (vat, self.name))
                    if response_data['mensaje'] == "Credenciales no registradas":
                        raise ValidationError("No ha registrado credenciales válidas, por favor verifique en su configuración")
    
                return name, address

    