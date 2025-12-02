# -*- coding: utf-8 -*-

from odoo import models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare
import logging

_logger = logging.getLogger(__name__)


class PosPaymentApprovalRequest(models.Model):
    _inherit = 'pos.payment.approval.request'
    
    def action_approve_request(self):
        """
        Lógica inteligente mejorada:
        1. Si total pagos == total orden Y existe pago similar → REEMPLAZAR
        2. Si hay espacio para el nuevo pago → SOLO AGREGAR
        3. Si excede → AGREGAR con advertencia
        """
        for record in self:
            _logger.info("=" * 80)
            _logger.info("APROBANDO SOLICITUD: %s", record.name)
            _logger.info("Orden: %s", record.pos_order_id.name)
            _logger.info("Total orden: %s", record.pos_order_id.amount_total)
            _logger.info("Monto solicitado: %s", record.amount_requested)
            
            # Calcular total de pagos ANTES de agregar el nuevo
            current_payments = record.pos_order_id.payment_ids
            total_current_payments = sum(current_payments.mapped('amount'))
            
            _logger.info("Total pagos actuales: %s", total_current_payments)
            _logger.info("Pagos actuales (%s):", len(current_payments))
            for p in current_payments:
                _logger.info("  - %s: %s (ID: %s)", p.payment_method_id.name, p.amount, p.id)
            
            # Guardar método antiguo (si viene del backend con OLD_PAYMENTS)
            old_payment_method_id = None
            
            if record.edit_detail and 'OLD_PAYMENTS:' in record.edit_detail:
                try:
                    detail_parts = record.edit_detail.split('|')
                    old_payments_part = [p for p in detail_parts if 'OLD_PAYMENTS:' in p][0]
                    old_payment_ids_str = old_payments_part.replace('OLD_PAYMENTS:', '')
                    
                    if old_payment_ids_str:
                        old_payment_ids = [int(x) for x in old_payment_ids_str.split(',') if x]
                        old_payments = self.env['pos.payment'].browse(old_payment_ids)
                        
                        existing_old_payments = old_payments.exists()
                        if existing_old_payments:
                            old_payment_method_id = existing_old_payments[0].payment_method_id.id
                            _logger.info("Método antiguo (backend): %s", existing_old_payments[0].payment_method_id.name)
                        
                except Exception as e:
                    _logger.error("Error al parsear OLD_PAYMENTS: %s", e)
        
        # Llamar a super para crear el nuevo pago
        _logger.info("Creando nuevo pago...")
        result = super().action_approve_request()
        
        # Verificar que se creó el payment_id
        for record in self:
            if record.state == 'approved' and not record.payment_id:
                _logger.warning("Solicitud sin payment_id - creando manualmente")
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
                    _logger.info("✓ Payment creado manualmente")
                except Exception as e:
                    _logger.error("Error al crear payment: %s", e)
            
            # LÓGICA INTELIGENTE
            order_total = record.pos_order_id.amount_total
            precision = record.pos_order_id.currency_id.rounding
            
            # Recalcular sin incluir el nuevo pago
            payments_before_new = [p for p in record.pos_order_id.payment_ids if p.id != record.payment_id.id]
            total_before_new = sum(p.amount for p in payments_before_new)
            
            _logger.info("\n🤔 ANÁLISIS DE DECISIÓN:")
            _logger.info("Total orden: %s", order_total)
            _logger.info("Total pagos antes del nuevo: %s", total_before_new)
            _logger.info("Monto del nuevo pago: %s", record.amount_requested)
            
            # Calcular espacio disponible
            remaining_space = order_total - total_before_new
            _logger.info("Espacio disponible: %s", remaining_space)
            
            # Decisión: ¿Reemplazar o Agregar?
            should_replace = False
            
            # CONDICIÓN 1: Pagos completos Y existe pago similar
            payments_complete = float_compare(total_before_new, order_total, precision_rounding=precision) >= 0
            
            if payments_complete:
                _logger.info("✓ Los pagos ya están completos")
                
                # Buscar si existe un pago con el mismo método y monto
                # (excluyendo el que acabamos de crear)
                similar_payments = []
                
                for payment in payments_before_new:
                    # Buscar por método (si lo tenemos) o por monto
                    matches_method = (old_payment_method_id and 
                                    payment.payment_method_id.id == old_payment_method_id)
                    
                    matches_amount = float_compare(
                        payment.amount,
                        record.amount_requested,
                        precision_rounding=precision
                    ) == 0
                    
                    if matches_amount and (matches_method or not old_payment_method_id):
                        similar_payments.append(payment)
                        _logger.info("  Pago similar encontrado: %s - %s (ID: %s)", 
                                   payment.payment_method_id.name,
                                   payment.amount,
                                   payment.id)
                
                if similar_payments:
                    should_replace = True
                    _logger.info("✓ DECISIÓN: REEMPLAZAR (hay %s pagos similares)", len(similar_payments))
                else:
                    _logger.info("✗ No hay pagos similares para reemplazar")
            else:
                _logger.info("✓ Los pagos aún no están completos (espacio: %s)", remaining_space)
            
            # EJECUTAR DECISIÓN
            if should_replace:
                _logger.info("\n🔄 EJECUTANDO REEMPLAZO:")
                
                # Eliminar UNO de los pagos similares (el más reciente)
                payment_to_remove = max(similar_payments, key=lambda p: p.id)
                
                _logger.info("Eliminando: %s - %s (ID: %s)", 
                           payment_to_remove.payment_method_id.name,
                           payment_to_remove.amount,
                           payment_to_remove.id)
                
                if len(similar_payments) > 1:
                    _logger.info("⚠️ Había %s pagos similares, eliminando el más reciente", 
                               len(similar_payments))
                
                payment_to_remove.sudo().unlink()
                _logger.info("✓ Pago reemplazado exitosamente")
            else:
                _logger.info("\n➕ SOLO AGREGAR (sin reemplazar)")
            
            # VALIDACIÓN FINAL
            final_payments = record.pos_order_id.payment_ids
            final_total = sum(final_payments.mapped('amount'))
            
            _logger.info("\n📊 ESTADO FINAL:")
            _logger.info("Total orden: %s", order_total)
            _logger.info("Total pagos: %s", final_total)
            _logger.info("Diferencia: %s", final_total - order_total)
            _logger.info("Pagos finales (%s):", len(final_payments))
            for p in final_payments:
                _logger.info("  - %s: %s (ID: %s)", p.payment_method_id.name, p.amount, p.id)
            
            # Advertencia si excede
            if float_compare(final_total, order_total, precision_rounding=precision) > 0:
                excess = final_total - order_total
                _logger.warning("⚠️ ADVERTENCIA: Total de pagos excede por %s", excess)
                
                warning_msg = _(
                    "\n⚠️ ADVERTENCIA: Pagos exceden el total de la orden\n"
                    "Total orden: %(order_total)s\n"
                    "Total pagos: %(payment_total)s\n"
                    "Exceso: %(excess)s\n"
                    "Revisa y elimina pagos manualmente si es necesario."
                ) % {
                    'order_total': order_total,
                    'payment_total': final_total,
                    'excess': excess,
                }
                
                current_note = record.pos_order_id.note or ""
                record.pos_order_id.sudo().write({
                    'note': f"{current_note}\n{warning_msg}"
                })
        
        # Agregar nota de aprobación
        for record in self:
            from datetime import datetime
            approver_name = self.env.user.name
            
            approval_note = _(
                "\n═══════════════════════════════════════\n"
                "SOLICITUD APROBADA\n"
                "═══════════════════════════════════════\n"
                "Fecha: %(date)s\n"
                "Aprobador: %(approver)s\n"
                "Solicitud: %(request)s\n"
                "Método: %(method)s\n"
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
        
        _logger.info("=" * 80)
        
        return result
    
    def action_reject_request(self, reason):
        """Agregar nota de rechazo"""
        result = super().action_reject_request(reason)
        
        for record in self:
            from datetime import datetime
            rejecter_name = self.env.user.name
            
            rejection_note = _(
                "\n═══════════════════════════════════════\n"
                "SOLICITUD RECHAZADA\n"
                "═══════════════════════════════════════\n"
                "Fecha: %(date)s\n"
                "Rechazado por: %(rejecter)s\n"
                "Solicitud: %(request)s\n"
                "Motivo: %(reason)s\n"
                "═══════════════════════════════════════"
            ) % {
                'date': datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
                'rejecter': rejecter_name,
                'request': record.name,
                'reason': reason,
            }
            
            current_note = record.pos_order_id.note or ""
            record.pos_order_id.sudo().write({
                'note': f"{current_note}\n{rejection_note}"
            })
        
        return result