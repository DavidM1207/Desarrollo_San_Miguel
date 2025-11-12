# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


class PosPaymentChangeWizard(models.TransientModel):
    _inherit = "pos.payment.change.wizard"
    
    def button_change_payment(self):
        """
        Extensión del método original para detectar si algún método de pago
        requiere aprobación. Si es así, crea solicitudes de aprobación en lugar
        de ejecutar el cambio directamente.
        """
        self.ensure_one()
        order = self.order_id
        
        # Validación de total (mismo código del original)
        total = sum(self.mapped("new_line_ids.amount"))
        if (
            float_compare(
                total,
                self.amount_total,
                precision_rounding=order.currency_id.rounding,
            )
            != 0
        ):
            raise UserError(
                _(
                    "Differences between the two values for the POS"
                    " Order '%(name)s':\n\n"
                    " * Total of all the new payments %(total)s;\n"
                    " * Total of the POS Order %(amount_total)s;\n\n"
                    "Please change the payments.",
                    name=order.name,
                    total=total,
                    amount_total=order.amount_total,
                )
            )
        
        # Verificar si algún método requiere aprobación
        methods_requiring_approval = self.new_line_ids.filtered(
            lambda l: l.new_payment_method_id.is_valid_for_payment_approval_request
        )
        
        if methods_requiring_approval:
            # Si hay métodos que requieren aprobación, crear solicitudes
            return self._create_approval_requests()
        else:
            # Si no hay métodos que requieran aprobación, flujo normal
            return super().button_change_payment()
    
    def _create_approval_requests(self):
        """
        Crea solicitudes de aprobación para los métodos de pago seleccionados.
        Reutiliza el sistema de aprobación existente.
        """
        self.ensure_one()
        order = self.order_id
        
        # Crear una solicitud por cada línea de pago
        approval_requests = []
        for line in self.new_line_ids:
            request_vals = {
                'payment_method_id': line.new_payment_method_id.id,
                'amount_requested': line.amount,
                'voucher_amount': line.amount,
                'pos_order_id': order.id,
                'state': 'pending',
            }
            
            request = self.env['pos.payment.approval.request'].create(request_vals)
            approval_requests.append(request)
        
        # Preparar mensaje para el usuario
        methods_names = ', '.join(
            self.new_line_ids.mapped('new_payment_method_id.name')
        )
        
        message = _(
            "Se han creado %(count)s solicitudes de aprobación para el pedido %(order)s.\n\n"
            "Métodos de pago: %(methods)s\n\n"
            "Las solicitudes están pendientes de aprobación. "
            "El aprobador debe asignar los documentos de pago correspondientes y aprobar."
        ) % {
            'count': len(approval_requests),
            'order': order.name,
            'methods': methods_names,
        }
        
        # Registrar en el chatter de la orden
        order.message_post(
            body=message,
            subject=_("Solicitudes de aprobación creadas"),
            message_type='notification'
        )
        
        # Retornar notificación al usuario
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Solicitudes de Aprobación Creadas'),
                'message': message,
                'type': 'success',
                'sticky': True,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }