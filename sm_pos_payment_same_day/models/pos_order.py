# -*- coding: utf-8 -*-
from datetime import date
from odoo import models
from odoo.exceptions import UserError


class PosOrder(models.Model):
    _inherit = 'pos.order'
    
    def action_pos_order_change_payment_same_day(self):
        """
        Acción para cambiar pagos SOLO si la orden es del mismo día.
        Reutiliza el wizard existente del módulo pos_payment_change.
        """
        self.ensure_one()
        
        # Validar que la orden sea del mismo día
        today = date.today()
        order_date = self.date_order.date() if self.date_order else False
        
        if order_date != today:
            raise UserError(
                f'No se puede cambiar el método de pago.\n\n'
                f'Esta acción solo está permitida para órdenes del mismo día.\n\n'
                f'Fecha de la orden: {order_date.strftime("%d/%m/%Y")}\n'
                f'Fecha actual: {today.strftime("%d/%m/%Y")}'
            )
        
        # Si pasa la validación, abrir el wizard existente
        return {
            'name': 'Cambiar Método de Pago',
            'type': 'ir.actions.act_window',
            'res_model': 'pos.payment.change.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,
                'active_id': self.id,
                'active_ids': self.ids,
            }
        }