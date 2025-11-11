# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.exceptions import UserError
from datetime import date

class PosOrder(models.Model):
    _inherit = 'pos.order'
    
    def action_pos_order_change_payment_same_day(self):
        """
        Acción para cambiar pagos solo si la orden es del mismo día
        """
        self.ensure_one()
        
        # Validar que la orden sea del mismo día
        today = date.today()
        order_date = self.date_order.date() if self.date_order else False
        
        if order_date != today:
            raise UserError(
                f'No se puede cambiar el método de pago. '
                f'Esta acción solo está permitida para órdenes del mismo día.\n\n'
                f'Fecha de la orden: {order_date.strftime("%d/%m/%Y")}\n'
                f'Fecha actual: {today.strftime("%d/%m/%Y")}'
            )
        
        # Si la validación pasa, abrir el wizard
        return {
            'name': 'Cambiar Método de Pago',
            'type': 'ir.actions.act_window',
            'res_model': 'pos.payment.change.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,
                'active_id': self.id,
                'active_ids': self.ids,
            }
        }