# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PosOrder(models.Model):
    _inherit = 'pos.order'

    # Definir los campos que necesitamos
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
        """
        Interceptar los datos de la orden antes de crearla para 
        forzar que siempre tenga ship_later activado con fecha actual
        """
        order_fields = super()._order_fields(ui_order)
        
        # Forzar ship_later a True y establecer la fecha actual
        order_fields['to_ship'] = True
        order_fields['shipping_date'] = fields.Date.context_today(self)
        
        return order_fields

    def _prepare_picking_vals(self):
        """
        Modificar la preparación de los valores del picking para 
        asegurar que se generen los 2 movimientos
        """
        self.ensure_one()
        vals = super()._prepare_picking_vals()
        
        # Si hay una fecha de envío programada, usarla
        if self.shipping_date:
            vals['scheduled_date'] = fields.Datetime.now()
        
        return vals