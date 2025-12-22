# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    tracker_active = fields.Boolean(
        string='Activo en Tracker',
        default=True,
        help='Si está marcado, este producto/servicio creará proyectos en el Tracker'
    )