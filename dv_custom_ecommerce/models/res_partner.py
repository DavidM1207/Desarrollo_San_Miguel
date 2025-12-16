# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"


    # @api.model_create_multi
    # def create(self, vals_list):
    #     # Saltar validación si viene del portal web
    #     if self.env.context.get('from_website') or self.env.context.get('portal_signup'):
    #         return super(ResPartner, self).create(vals_list)
        
    #     # Validar NITs duplicados solo si NO viene del portal
    #     for vals in vals_list:
    #         vat = vals.get('vat')
    #         if vat and vat.upper() not in ['CF', 'C/F']:
    #             existing = self.search([('vat', '=', vat)], limit=1)
    #             if existing:
    #                 raise ValidationError(
    #                     _("Ya existe un contacto con el mismo número de NIT: %s") % existing.name
    #                 )
        
    #     return super(ResPartner, self).create(vals_list)



    @api.model_create_multi
    def create(self,vals):
        if self.env.context.get('from_website') or self.env.context.get('portal_signup'):
            return super(ResPartner, self).create(vals)
        company_type = False
        parent_id = False
        if'company_type' in vals:
            company_type = vals['company_type']
        if'parent_id' in vals:
            parent_id = vals['parent_id']
        if company_type == 'person' and parent_id:
            return super(ResPartner, self).create(vals)
        else:
            for rec in vals:
                if 'vat' in rec:
                    if rec['vat']:
                        vat = rec['vat'].replace('-', '')
                        vat = vat.upper()
                        rec['vat'] = vat
                        name = ""
                        address = ""
                        
                        if vat != 'CF' and vat != 'C/F' and vat != 'cf':   
                            name, address = self.nit_validation(vat)
                            if name != "":
                                rec['name'] = name.title()
                            if address != "":
                                rec['street'] = address.title()
                            
                    else:
                        raise ValidationError("Debe ingresar NIT.")
        return super(ResPartner, self).create(vals)
    
