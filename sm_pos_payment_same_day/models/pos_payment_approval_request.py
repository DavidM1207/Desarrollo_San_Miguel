# -*- coding: utf-8 -*-

from odoo import models, _
import logging

_logger = logging.getLogger(__name__)


class PosPaymentApprovalRequest(models.Model):
    _inherit = 'pos.payment.approval.request'
    
    def action_approve_request(self):
        """
        Sobrescribir para eliminar pagos antiguos SOLO cuando se apruebe
        """
        for record in self:
            # ANTES de aprobar, eliminar los pagos antiguos
            if record.edit_detail and 'OLD_PAYMENTS:' in record.edit_detail:
                try:
                    # Parsear los IDs de pagos antiguos
                    detail_parts = record.edit_detail.split('|')
                    old_payments_part = [p for p in detail_parts if 'OLD_PAYMENTS:' in p][0]
                    old_payment_ids_str = old_payments_part.replace('OLD_PAYMENTS:', '')
                    
                    if old_payment_ids_str:
                        old_payment_ids = [int(x) for x in old_payment_ids_str.split(',') if x]
                        old_payments = self.env['pos.payment'].browse(old_payment_ids)
                        
                        _logger.info("Aprobando solicitud: eliminando pagos antiguos %s", old_payment_ids)
                        old_payments.sudo().unlink()
                        _logger.info("✓ Pagos antiguos eliminados")
                except Exception as e:
                    _logger.error("Error al eliminar pagos antiguos: %s", e)
            
            # Extraer la razón del cambio
            reason = ""
            if record.edit_detail and 'REASON:' in record.edit_detail:
                try:
                    detail_parts = record.edit_detail.split('|')
                    reason_part = [p for p in detail_parts if 'REASON:' in p][0]
                    reason = reason_part.replace('REASON:', '')
                except:
                    pass
        
        # Llamar al método original para aprobar
        result = super().action_approve_request()
        
        # Agregar nota de aprobación a la orden
        for record in self:
            from datetime import datetime
            approver_name = self.env.user.name
            
            approval_note = _(
                "\n═══════════════════════════════════════\n"
                "SOLICITUD APROBADA\n"
                "═══════════════════════════════════════\n"
                "Fecha de aprobación: %(date)s\n"
                "Aprobador: %(approver)s\n"
                "Solicitud: %(request)s\n"
                "Método de pago aplicado: %(method)s\n"
                "Monto: %(amount)s\n"
                "═══════════════════════════════════════"
            ) % {
                'date': datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
                'approver': approver_name,
                'request': record.name,
                'method': record.payment_method_id.name,
                'amount': record.amount_requested,
            }
            
            current_note = record.pos_order_id.note or ""
            record.pos_order_id.sudo().write({
                'note': f"{current_note}\n{approval_note}"
            })
        
        return result
    
    def action_reject_request(self, reason):
        """
        Sobrescribir para agregar nota de rechazo
        Los pagos antiguos NO se tocan (se quedan como estaban)
        """
        _logger.info("Rechazando solicitud - Los pagos antiguos permanecen intactos")
        
        # Llamar al método original para rechazar
        result = super().action_reject_request(reason)
        
        # Agregar nota de rechazo a la orden
        for record in self:
            from datetime import datetime
            rejecter_name = self.env.user.name
            
            rejection_note = _(
                "\n═══════════════════════════════════════\n"
                "SOLICITUD RECHAZADA\n"
                "═══════════════════════════════════════\n"
                "Fecha de rechazo: %(date)s\n"
                "Rechazado por: %(rejecter)s\n"
                "Solicitud: %(request)s\n"
                "Método solicitado: %(method)s\n"
                "Monto solicitado: %(amount)s\n"
                "Motivo del rechazo: %(reason)s\n"
                "Los pagos originales permanecen sin cambios.\n"
                "═══════════════════════════════════════"
            ) % {
                'date': datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
                'rejecter': rejecter_name,
                'request': record.name,
                'method': record.payment_method_id.name,
                'amount': record.amount_requested,
                'reason': reason,
            }
            
            current_note = record.pos_order_id.note or ""
            record.pos_order_id.sudo().write({
                'note': f"{current_note}\n{rejection_note}"
            })
        
        return result