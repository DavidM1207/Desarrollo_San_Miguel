# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_compare
import logging

_logger = logging.getLogger(__name__)


class PosPaymentChangeWizard(models.TransientModel):
    _inherit = "pos.payment.change.wizard"
    
    from_same_day_button = fields.Boolean(
        string='Desde Botón Mismo Día',
        default=False
    )
    
    @api.model
    def default_get(self, fields_list):
        """Capturar el contexto en default_get"""
        res = super().default_get(fields_list)
        
        if self.env.context.get('from_same_day_button'):
            res['from_same_day_button'] = True
            _logger.info("✓ Flag from_same_day_button capturado")
        
        return res
    
    def button_change_payment(self):
        """Interceptar el flujo para detectar métodos que requieren aprobación"""
        self.ensure_one()
        order = self.order_id
        
        _logger.info("=" * 80)
        _logger.info("BUTTON CHANGE PAYMENT")
        _logger.info("from_same_day_button: %s", self.from_same_day_button)
        _logger.info("Orden: %s", order.name)
        
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
        
        # SOLO interceptar si viene del botón "Cambiar pagos día"
        if self.from_same_day_button or self.env.context.get('from_same_day_button'):
            _logger.info("✓ Detectado flag from_same_day_button")
            
            # Verificar métodos que requieren aprobación
            methods_requiring_approval = self.new_line_ids.filtered(
                lambda l: l.new_payment_method_id.is_valid_for_payment_approval_request
            )
            
            for line in self.new_line_ids:
                _logger.info("  - %s: requires_approval=%s", 
                           line.new_payment_method_id.name,
                           line.new_payment_method_id.is_valid_for_payment_approval_request)
            
            if methods_requiring_approval:
                _logger.info("✓✓✓ Abriendo wizard de aprobación")
                return self._open_approval_wizard(methods_requiring_approval)
            else:
                _logger.info("No hay métodos que requieran aprobación, flujo normal")
        
        # Flujo normal - ASEGURAR QUE RETORNE CORRECTAMENTE
        _logger.info("Ejecutando flujo original (super)")
        
        # Remover el flag del contexto para evitar recursión
        ctx = dict(self.env.context)
        ctx.pop('from_same_day_button', None)
        ctx.pop('default_from_same_day_button', None)
        
        # Llamar al método original SIN nuestro contexto
        result = super(PosPaymentChangeWizard, self.with_context(ctx)).button_change_payment()
        
        _logger.info("Resultado del super: %s", result)
        _logger.info("=" * 80)
        
        # Si no retorna nada, retornar acción de cerrar
        if not result:
            return {'type': 'ir.actions.act_window_close'}
        
        return result
    
    def _open_approval_wizard(self, approval_lines):
        """Abre wizard de aprobación con sudo() completo"""
        self.ensure_one()
        
        first_line = approval_lines[0]
        
        _logger.info("Creando wizard de aprobación:")
        _logger.info("  Orden: %s", self.order_id.name)
        _logger.info("  Método: %s", first_line.new_payment_method_id.name)
        _logger.info("  Monto: %s", first_line.amount)
        
        # Crear wizard con sudo()
        wizard = self.env['pos.payment.approval.create.wizard'].sudo().create({
            'pos_order_id': self.order_id.id,
            'payment_method_id': first_line.new_payment_method_id.id,
            'amount_requested': first_line.amount,
            'voucher_amount': first_line.amount,
        })
        
        _logger.info("✓ Wizard creado con ID: %s", wizard.id)
        
        return {
            'name': _('Solicitud de Aprobación de Pago'),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.payment.approval.create.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }