# -*- coding: utf-8 -*-

from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    nit_fel_certifier = fields.Selection(string='Certificador a utilizar para validación de NIT', related="company_id.nit_fel_certifier", readonly=False)
    nit_fel_certifier_url = fields.Char(string="Url servicio", related="company_id.nit_fel_certifier_url", readonly=False)