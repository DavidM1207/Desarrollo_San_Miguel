# -*- coding: utf-8 -*-
from datetime import date
from odoo import models, _
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
                _('No se puede cambiar el método de pago.\n\n'
                  'Esta acción solo está permitida para órdenes del mismo día.\n\n'
                  'Fecha de la orden: %s\n'
                  'Fecha actual: %s') % (
                    order_date.strftime("%d/%m/%Y") if order_date else 'N/A',
                    today.strftime("%d/%m/%Y")
                )
            )
        
        # Si pasa la validación, abrir el wizard existente
        return {
            'name': _('Cambiar Método de Pago'),
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