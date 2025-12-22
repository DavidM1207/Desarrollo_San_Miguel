# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Almacén',
        help='Almacén asociado a esta tienda para consultar disponibilidad de stock'
    )