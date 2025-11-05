# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PosOrder(models.Model):
    _inherit = 'pos.order'

    to_ship = fields.Boolean(
        string='Enviar Después',
        default=False,
        help='Si está marcado, la orden se enviará en una fecha posterior'
    )
    
    shipping_date = fields.Date(
        string='Fecha de Envío',
        help='Fecha programada para el envío'
    )

    @api.model
    def _order_fields(self, ui_order):
        order_fields = super()._order_fields(ui_order)
        order_fields['to_ship'] = True
        order_fields['shipping_date'] = fields.Date.context_today(self)
        return order_fields
