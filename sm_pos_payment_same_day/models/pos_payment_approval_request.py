# -*- coding: utf-8 -*-

from odoo import models, _
import logging

_logger = logging.getLogger(__name__)


class PosPaymentApprovalRequest(models.Model):
    _inherit = 'pos.payment.approval.request'
    
    def action_approve_request(self):
       
        for record in self:
            _logger.info("=" * 80)
            _logger.info("APROBANDO SOLICITUD: %s", record.name)
            
            # PASO 1: Eliminar pagos antiguos ANTES de aprobar
            if record.edit_detail and 'OLD_PAYMENTS:' in record.edit_detail:
                try:
                    # Parsear los IDs de pagos antiguos
                    detail_parts = record.edit_detail.split('|')
                    old_payments_part = [p for p in detail_parts if 'OLD_PAYMENTS:' in p][0]
                    old_payment_ids_str = old_payments_part.replace('OLD_PAYMENTS:', '')
                    
                    if old_payment_ids_str:
                        old_payment_ids = [int(x) for x in old_payment_ids_str.split(',') if x]
                        old_payments = self.env['pos.payment'].browse(old_payment_ids)
                        
                        _logger.info("Eliminando pagos antiguos: %s", old_payment_ids)
                        
                        # Verificar que existan antes de eliminar
                        existing_old_payments = old_payments.exists()
                        if existing_old_payments:
                            _logger.info("Pagos encontrados: %s", existing_old_payments.ids)
                            existing_old_payments.sudo().unlink()
                            _logger.info("✓ Pagos antiguos eliminados correctamente")
                        else:
                            _logger.warning("Los pagos antiguos ya no existen")
                            
                except Exception as e:
                    _logger.error("Error al eliminar pagos antiguos: %s", e)
        
        
        _logger.info("Llamando a super().action_approve_request()")
        result = super().action_approve_request()
        
         
        for record in self:
            if record.state == 'approved' and not record.payment_id:
                _logger.warning("Solicitud aprobada pero sin payment_id. Creando manualmente...")
                try:
                    payment_vals = {
                        'payment_date': self.env['ir.fields'].Datetime.now(),
                        'amount': record.amount_requested,
                        'payment_method_id': record.payment_document_id.payment_method_id.id,
                        'pos_order_id': record.pos_order_id.id,
                        'approval_request_id': record.id,
                    }
                    payment = self.env['pos.payment'].create(payment_vals)
                    record.payment_id = payment.id
                    record.pos_order_id.write({'payment_ids': [(4, payment.id)]})
                    _logger.info("Pago creado manualmente: %s", payment.id)
                except Exception as e:
                    _logger.error("Error al crear payment manualmente: %s", e)
            
            # PASO 4: Verificar que NO haya pagos duplicados
            # Si hay más de un pago con el mismo método, eliminar duplicados
            order_payments = record.pos_order_id.payment_ids
            _logger.info("Pagos en la orden después de aprobar: %s", order_payments.ids)
            
            # Agrupar por método de pago
            payment_methods = {}
            for payment in order_payments:
                method_id = payment.payment_method_id.id
                if method_id not in payment_methods:
                    payment_methods[method_id] = []
                payment_methods[method_id].append(payment)
            
            # Si hay duplicados del mismo método, mantener solo el más reciente
            for method_id, payments in payment_methods.items():
                if len(payments) > 1:
                    _logger.warning("Duplicados encontrados para método %s! Total: %s", method_id, len(payments))
                    # Ordenar por ID (el más reciente tiene ID mayor)
                    payments_sorted = sorted(payments, key=lambda p: p.id, reverse=True)
                    # Mantener el primero (más reciente), eliminar el resto
                    payments_to_delete = payments_sorted[1:]
                    _logger.info("Eliminando pagos duplicados: %s", [p.id for p in payments_to_delete])
                    for p in payments_to_delete:
                        p.sudo().unlink()
                    _logger.info("Duplicados eliminados")
        
        # PASO 5: Agregar nota de aprobación a la orden
        for record in self:
            from datetime import datetime
            approver_name = self.env.user.name
            
            # Extraer la razón del cambio si existe
            reason = ""
            if record.edit_detail and 'REASON:' in record.edit_detail:
                try:
                    detail_parts = record.edit_detail.split('|')
                    reason_part = [p for p in detail_parts if 'REASON:' in p][0]
                    reason = reason_part.replace('REASON:', '')
                except:
                    pass
            
            approval_note = _(
                
                "SOLICITUD APROBADA, Fecha de aprobación: %(date)s ,Aprobador: %(approver)s, Solicitud: %(request)s, Método de pago aplicado: %(method)s, Monto: %(amount)s"
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
            
            _logger.info("✓ Nota de aprobación agregada")
            _logger.info("=" * 80)
        
        return result
    
    def action_reject_request(self, reason):
       
        _logger.info("=" * 80)
        _logger.info("RECHAZANDO SOLICITUD")
        _logger.info("Los pagos antiguos permanecen intactos")
        
        # Llamar al método original para rechazar
        result = super().action_reject_request(reason)
        
        # Agregar nota de rechazo a la orden
        for record in self:
            from datetime import datetime
            rejecter_name = self.env.user.name
            
            rejection_note = _(
                "SOLICITUD RECHAZADA" "Fecha de rechazo: %(date)s, Rechazado por: %(rejecter)s, Solicitud: %(request)s, Método solicitado: %(method)s, Monto solicitado: %(amount)s, Motivo del rechazo: %(reason)s"
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
            
            _logger.info("Nota de rechazo agregada")
            _logger.info("=" * 80)
        
        return result
    
    def action_generate_payment_manual(self):
        _logger.info("=" * 80)
        _logger.info("GENERANDO PAGO MANUAL - Este botón no debería aparecer")
        
        result = super().action_generate_payment_manual()
        
        # Eliminar duplicados si los hay
        for record in self:
            order_payments = record.pos_order_id.payment_ids
            payment_methods = {}
            for payment in order_payments:
                method_id = payment.payment_method_id.id
                if method_id not in payment_methods:
                    payment_methods[method_id] = []
                payment_methods[method_id].append(payment)
            
            for method_id, payments in payment_methods.items():
                if len(payments) > 1:
                    payments_sorted = sorted(payments, key=lambda p: p.id, reverse=True)
                    payments_to_delete = payments_sorted[1:]
                    for p in payments_to_delete:
                        p.sudo().unlink()
        
        _logger.info("=" * 80)
        return result