# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


class PosPaymentChangeWizard(models.TransientModel):
    _inherit = "pos.payment.change.wizard"
    
    def button_change_payment(self):
        """
        Extensión del método original para detectar si algún método de pago
        requiere aprobación.
        """
        self.ensure_one()
        order = self.order_id
        
        # Validación de total
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
        
        # SOLO validar si viene del botón "Cambiar pagos día"
        if self.env.context.get('from_same_day_button'):
            methods_requiring_approval = self.new_line_ids.filtered(
                lambda l: l.new_payment_method_id.is_valid_for_payment_approval_request
            )
            
            if methods_requiring_approval:
                # Abrir wizard de solicitud de aprobación
                return self._open_approval_wizard(methods_requiring_approval)
        
        # Flujo normal
        return super().button_change_payment()
    
    def _open_approval_wizard(self, approval_lines):
        """
        Abre el wizard de solicitud de aprobación para el primer método
        que requiere aprobación
        """
        self.ensure_one()
        
        # Por simplicidad, tomamos la primera línea que requiere aprobación
        # Si hay múltiples, el usuario tendrá que crear solicitudes una por una
        first_line = approval_lines[0]
        
        wizard = self.env['pos.payment.approval.create.wizard'].create({
            'pos_order_id': self.order_id.id,
            'payment_method_id': first_line.new_payment_method_id.id,
            'amount_requested': first_line.amount,
        })
        
        return {
            'name': _('Solicitud de Aprobación de Pago'),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.payment.approval.create.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }