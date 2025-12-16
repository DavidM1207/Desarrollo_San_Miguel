# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import Command, models, fields, api, _


class PtNitVerificationMassiveNitUpdate(models.TransientModel):
    _name = 'pt_nit_verification.massive_nit_update'
    _description = 'Actualización de información de  nit'
    
    res_partner_ids = fields.Many2many('res.partner','massive_nit_update_partner_rel', string="Contactos")
    
    def update_contacts(self):
        
        for contact in self.res_partner_ids:
            contact.action_massive_nit_validate()
        
        return True
    