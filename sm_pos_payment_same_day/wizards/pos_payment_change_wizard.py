# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_compare
import logging

_logger = logging.getLogger(__name__)


class PosPaymentChangeWizard(models.TransientModel):
    _inherit = "pos.payment.change.wizard"
    
    # Agregar campo para saber si viene del botón "Cambiar pagos día"
    from_same_day_button = fields.Boolean(
        string='Desde Botón Mismo Día',
        default=False
    )
    
    @api.model
    def default_get(self, fields_list):
        """Capturar el contexto en default_get"""
        res = super().default_get(fields_list)
        
        # Capturar el flag del contexto
        if self.env.context.get('from_same_day_button'):
            res['from_same_day_button'] = True
            _logger.info("✓ Flag from_same_day_button capturado en default_get")
        
        return res
    
    def button_change_payment(self):
        """
        Sobrescribir completamente el método para interceptar el flujo
        """
        self.ensure_one()
        order = self.order_id
        
        _logger.info("=" * 80)
        _logger.info("BUTTON CHANGE PAYMENT - INICIO")
        _logger.info("from_same_day_button (campo): %s", self.from_same_day_button)
        _logger.info("Orden: %s", order.name)
        _logger.info("=" * 80)
        
        # Validación de total (código original)
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
        
        # Verificar si viene del botón "Cambiar pagos día"
        if self.from_same_day_button or self.env.context.get('from_same_day_button'):
            _logger.info("✓ Detectado flag from_same_day_button")
            
            # Verificar si hay métodos que requieren aprobación
            methods_requiring_approval = self.new_line_ids.filtered(
                lambda l: l.new_payment_method_id.is_valid_for_payment_approval_request
            )
            
            _logger.info("Métodos de pago seleccionados:")
            for line in self.new_line_ids:
                _logger.info("  - %s: requires_approval=%s, amount=%s", 
                           line.new_payment_method_id.name,
                           line.new_payment_method_id.is_valid_for_payment_approval_request,
                           line.amount)
            
            _logger.info("Total métodos que requieren aprobación: %s", len(methods_requiring_approval))
            
            if methods_requiring_approval:
                _logger.info("✓✓✓ ABRIENDO WIZARD DE APROBACIÓN ✓✓✓")
                # Abrir wizard de aprobación (NO eliminar el actual)
                return self._open_approval_wizard(methods_requiring_approval)
        
        # Si no requiere aprobación, ejecutar flujo original
        _logger.info("Ejecutando flujo normal (super)")
        return super(PosPaymentChangeWizard, self).button_change_payment()
    
    def _open_approval_wizard(self, approval_lines):
        """
        Abre el wizard de solicitud de aprobación
        """
        self.ensure_one()
        
        # Tomar la primera línea que requiere aprobación
        first_line = approval_lines[0]
        
        _logger.info("Creando wizard de aprobación:")
        _logger.info("  Orden: %s (ID: %s)", self.order_id.name, self.order_id.id)
        _logger.info("  Método: %s (ID: %s)", first_line.new_payment_method_id.name, first_line.new_payment_method_id.id)
        _logger.info("  Monto: %s", first_line.amount)
        
        # Crear el wizard de aprobación
        wizard = self.env['pos.payment.approval.create.wizard'].create({
            'pos_order_id': self.order_id.id,
            'payment_method_id': first_line.new_payment_method_id.id,
            'amount_requested': first_line.amount,
            'voucher_amount': first_line.amount,
        })
        
        _logger.info("✓ Wizard creado con ID: %s", wizard.id)
        
        # Retornar acción para abrir el nuevo wizard
        # Odoo cerrará el wizard actual automáticamente
        return {
            'name': _('Solicitud de Aprobación de Pago'),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.payment.approval.create.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }