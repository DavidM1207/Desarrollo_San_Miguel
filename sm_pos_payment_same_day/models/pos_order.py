# -*- coding: utf-8 -*-
from datetime import date
from odoo import models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'
    
    def action_pos_order_change_payment_same_day(self):
        """
        Acción para cambiar pagos SOLO si la orden es del mismo día.
        """
        self.ensure_one()
        
        _logger.info("=" * 80)
        _logger.info("ACTION POS ORDER CHANGE PAYMENT SAME DAY")
        _logger.info("Orden: %s", self.name)
        _logger.info("=" * 80)
        
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
        
        _logger.info("✓ Validación de fecha correcta")
        _logger.info("Abriendo wizard con contexto from_same_day_button=True")
        
        # Abrir el wizard con el flag
        return {
            'name': _('Cambiar Método de Pago'),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.payment.change.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,
                'default_from_same_day_button': True,  # ← Usar default_ para el campo
                'active_id': self.id,
                'active_ids': self.ids,
                'from_same_day_button': True,  # ← También en el contexto
            }
        }