# -*- coding: utf-8 -*-

from odoo import models, _
import logging

_logger = logging.getLogger(__name__)


class PosPaymentApprovalRequest(models.Model):
    _inherit = 'pos.payment.approval.request'
    
    def action_approve_request(self):
        """
        Al aprobar:
        1. Eliminar pagos antiguos
        2. Crear nuevo pago
        3. Enviar notificación al POS para actualizar
        """
        for record in self:
            _logger.info("=" * 80)
            _logger.info("APROBANDO SOLICITUD: %s", record.name)
            _logger.info("Orden: %s", record.pos_order_id.name)
            
            # Guardar datos ANTES de eliminar para la notificación
            old_payment_method_id = None
            
            # PASO 1: Si viene del backend, eliminar pagos antiguos
            if record.edit_detail and 'OLD_PAYMENTS:' in record.edit_detail:
                try:
                    detail_parts = record.edit_detail.split('|')
                    old_payments_part = [p for p in detail_parts if 'OLD_PAYMENTS:' in p][0]
                    old_payment_ids_str = old_payments_part.replace('OLD_PAYMENTS:', '')
                    
                    if old_payment_ids_str:
                        old_payment_ids = [int(x) for x in old_payment_ids_str.split(',') if x]
                        old_payments = self.env['pos.payment'].browse(old_payment_ids)
                        
                        _logger.info("Eliminando pagos antiguos: %s", old_payment_ids)
                        
                        existing_old_payments = old_payments.exists()
                        if existing_old_payments:
                            # Guardar el método del primer pago antiguo
                            old_payment_method_id = existing_old_payments[0].payment_method_id.id
                            existing_old_payments.sudo().unlink()
                            _logger.info("✓ Pagos antiguos eliminados")
                        
                except Exception as e:
                    _logger.error("Error al eliminar pagos antiguos: %s", e)
            
            # PASO 2: Si NO viene del backend (viene del POS), eliminar pagos del mismo método
            else:
                _logger.info("Solicitud desde POS - eliminando pagos del mismo método")
                try:
                    # Buscar pagos existentes con el MISMO método de pago
                    same_method_payments = record.pos_order_id.payment_ids.filtered(
                        lambda p: p.payment_method_id.id == record.payment_method_id.id
                    )
                    
                    if same_method_payments:
                        _logger.info("Encontrados pagos del mismo método: %s", same_method_payments.ids)
                        # Guardar el método antes de eliminar
                        old_payment_method_id = same_method_payments[0].payment_method_id.id
                        same_method_payments.sudo().unlink()
                        _logger.info("✓ Pagos del mismo método eliminados")
                    
                except Exception as e:
                    _logger.error("Error al eliminar pagos del mismo método: %s", e)
        
        # PASO 3: Llamar a super para crear el nuevo pago
        _logger.info("Creando nuevo pago (super)")
        result = super().action_approve_request()
        
        # PASO 4: Verificar que se creó el payment_id (evita botón manual)
        for record in self:
            if record.state == 'approved' and not record.payment_id:
                _logger.warning("Solicitud aprobada sin payment_id - creando manualmente")
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
                    _logger.info("✓ Payment creado manualmente: %s", payment.id)
                except Exception as e:
                    _logger.error("Error al crear payment: %s", e)
            
            # PASO 5: Eliminar duplicados por si acaso
            order_payments = record.pos_order_id.payment_ids
            _logger.info("Pagos finales en la orden: %s", order_payments.ids)
            
            payment_methods = {}
            for payment in order_payments:
                method_id = payment.payment_method_id.id
                if method_id not in payment_methods:
                    payment_methods[method_id] = []
                payment_methods[method_id].append(payment)
            
            for method_id, payments in payment_methods.items():
                if len(payments) > 1:
                    _logger.warning("Duplicados encontrados para método %s", method_id)
                    payments_sorted = sorted(payments, key=lambda p: p.id, reverse=True)
                    payments_to_delete = payments_sorted[1:]
                    _logger.info("Eliminando duplicados: %s", [p.id for p in payments_to_delete])
                    for p in payments_to_delete:
                        p.sudo().unlink()
                    _logger.info("✓ Duplicados eliminados")
        
        # PASO 6: Enviar notificación al POS para actualizar la pantalla
        
        for record  in self:
            _logger.info("=" * 80)
            _logger.info("PREPARANDO NOTIFICACIÓN AL POS")
            _logger.info("old_payment_method_id: %s", old_payment_method_id)
            
            # Determinar el método antiguo
            # Si viene del backend, ya lo tenemos en old_payment_method_id
            # Si viene del POS, buscamos pagos con el mismo método
            final_old_method_id = old_payment_method_id

            if not final_old_method_id:
                _logger.info("No hay old_payment_method_id guardado")
                _logger.info("Buscando pagos antiguos en la orden...")

                all_payments = record.pos_order_id.payment_ids
                _logger.info("Pagos totales en la orden: %s", len(all_payments))    

                for payment in all_payments:
                    _logger.info("  - Pago ID %s: Método %s (ID: %s), Monto: %s", 
                        payment.id, 
                        payment.payment_method_id.name,
                        payment.payment_method_id.id,
                        payment.amount)
            
            # Si hay un pago DIFERENTE al que acabamos de crear, ese es el antiguo
                    if payment.id != record.payment_id.id:
                        final_old_method_id = payment.payment_method_id.id
                        _logger.info("✓ Encontrado método antiguo: %s (ID: %s)", 
                           payment.payment_method_id.name,
                           final_old_method_id)
                        break
    
            _logger.info("final_old_method_id: %s", final_old_method_id)
        
            if final_old_method_id:
                _logger.info("✓ Enviando notificación al POS")
                _logger.info("  Usuario: %s (ID: %s)", record.user_id.name, record.user_id.id)
                _logger.info("  Partner: %s (ID: %s)", record.user_id.partner_id.name, record.user_id.partner_id.id)
                _logger.info("  Orden: %s (ID: %s)", record.pos_order_id.name, record.pos_order_id.id)
                _logger.info("  Método antiguo ID: %s", final_old_method_id)
                _logger.info("  Método nuevo: %s (ID: %s)", record.payment_method_id.name, record.payment_method_id.id)
        
        # Preparar payload
                payload = {
                    'pos_order_id': record.pos_order_id.id,
                    'old_payment_method_id': final_old_method_id,
                    'new_payment_method_id': record.payment_method_id.id,
                    'amount': record.amount_requested,
                }
        
                _logger.info("  Payload: %s", payload)
        
                try:
                    # Enviar notificación
                    self.env['bus.bus']._sendone(
                        record.user_id.partner_id,
                        'pos_payment_approved',
                        payload
                    )
            
                    _logger.info("✓✓✓ NOTIFICACIÓN ENVIADA EXITOSAMENTE ✓✓✓")
                except Exception as e:
                    _logger.error("❌ Error al enviar notificación: %s", e)
                    _logger.exception("Stack trace completo:")
            else:
                _logger.warning("✗ No se puede determinar el método antiguo - NO se envía notificación")
    
            _logger.info("=" * 80)


        # PASO 7: Agregar nota de aprobación
        for record in self:
            from datetime import datetime
            approver_name = self.env.user.name
            
            approval_note = _(
               
                "SOLICITUD APROBADA"
               
                "Fecha de aprobación: %(date)s"
                "Aprobador: %(approver)s"
                "Solicitud: %(request)s"
                "Método de pago aplicado: %(method)s"
                "Monto: %(amount)s"
             
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
        """
        Sobrescribir para agregar nota de rechazo
        Los pagos antiguos NO se tocan (se quedan como estaban)
        """
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
                
                "SOLICITUD RECHAZADA"
              
                "Fecha de rechazo: %(date)s"
                "Rechazado por: %(rejecter)s"
                "Solicitud: %(request)s"
                "Método solicitado: %(method)s"
                "Monto solicitado: %(amount)s"
                "Motivo del rechazo: %(reason)s"
                "Los pagos originales permanecen sin cambios."
        
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
            
            _logger.info("✓ Nota de rechazo agregada")
            _logger.info("=" * 80)
        
        return result
    
    def action_generate_payment_manual(self):
        """
        Este método NO debería ser necesario nunca
        Pero por seguridad, también eliminamos duplicados aquí
        """
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