# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.exceptions import ValidationError

class ResCompany(models.Model):
    _inherit = "res.company"

    nit_fel_certifier = fields.Selection([
        ('infile', 'InFile'),
        ('g4s', 'G4S'),
    ], string='Certificador a utilizar para validación de NIT')
    nit_fel_certifier_url = fields.Char(string="Url servicio")
    
    def write(self, values):
        for company in self:
            
            if values.get('nit_fel_certifier'):
                if values.get('nit_fel_certifier') != company.fel_certifier:
                    raise ValidationError('El certificador de la validación de NIT y facturación deben ser iguales')
        
        return super(ResCompany, self).write(values)