# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def _order_fields(self, ui_order):
        """
        Interceptar los datos de la orden antes de crearla para 
        forzar que siempre tenga ship_later activado con fecha actual
        """
        order_fields = super()._order_fields(ui_order)
        
        # Forzar ship_later a True y establecer la fecha actual
        order_fields['to_ship'] = True
        order_fields['shipping_date'] = fields.Date.context_today(self)
        
        return order_fields

     
