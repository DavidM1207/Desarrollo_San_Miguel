# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PosPaymentApprovalCreateWizard(models.TransientModel):
    _name = 'pos.payment.approval.create.wizard'
    _description = 'Solicitud de Aprobación de Pago'
    
    pos_order_id = fields.Many2one(
        'pos.order',
        string='Orden POS',
        required=True,
        readonly=True
    )
    
    document_identifier = fields.Char(
        string='Número de Documento',
        required=True,
        help='Ingrese el número del documento de pago'
    )
    
    payment_method_id = fields.Many2one(
        'pos.payment.method',
        string='Método de Pago',
        required=True,
        domain="[('is_valid_for_payment_approval_request', '=', True)]"
    )
    
    payment_document_id = fields.Many2one(
        'pos.payment.document',
        string='Documento Encontrado',
        readonly=True,
        help='Se llena automáticamente al buscar el documento'
    )
    
    document_exists = fields.Boolean(
        string='Documento Existe',
        default=False,
        readonly=True
    )
    
    voucher_amount = fields.Float(
        string='Cantidad del Comprobante',
        required=True,
        help='Monto total del comprobante'
    )
    
    remaining_balance = fields.Float(
        string='Saldo Restante',
        readonly=True,
        help='Saldo disponible del documento (si existe)'
    )
    
    amount_requested = fields.Float(
        string='Cantidad a Utilizar',
        required=True,
        help='Monto que se utilizará de este documento'
    )
    
    attachment = fields.Binary(
        string='Adjuntar Documento',
        required=True,
        attachment=True
    )
    
    attachment_filename = fields.Char(
        string='Nombre del Archivo'
    )
    
    def action_search_document(self):
        """Busca el documento en la BD"""
        self.ensure_one()
        
        if not self.document_identifier:
            raise UserError(_('Debe ingresar un número de documento antes de buscar.'))
        
        if not self.payment_method_id:
            raise UserError(_('Debe seleccionar un método de pago antes de buscar.'))
        
        PaymentDocument = self.env['pos.payment.document']
        result = PaymentDocument.search_document(
            self.document_identifier,
            self.payment_method_id.id
        )
        
        if not result['exists']:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Información'),
                    'message': _('El documento no existe. Ingrese el monto manualmente.'),
                    'type': 'warning',
                }
            }
        
        if not result['verified']:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Advertencia'),
                    'message': _('Este documento no ha sido verificado. Se creará uno nuevo al enviar la solicitud.'),
                    'type': 'warning',
                }
            }
        
        self.write({
            'payment_document_id': result['id'],
            'document_exists': True,
            'voucher_amount': result['total_amount'],
            'remaining_balance': result['remaining_amount'],
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Éxito'),
                'message': _('Documento encontrado y verificado. Saldo disponible: %s') % result['remaining_amount'],
                'type': 'success',
            }
        }
    
    def action_submit_request(self):
        """Crea la solicitud de aprobación"""
        self.ensure_one()
        
        if not self.document_identifier or not self.voucher_amount:
            raise UserError(_('Debe ingresar el identificador y monto del documento.'))
        
        if not self.payment_method_id or not self.amount_requested or not self.attachment:
            raise UserError(_('Todos los campos son obligatorios.'))
        
        if self.amount_requested > self.voucher_amount:
            raise UserError(_('La cantidad a utilizar no puede ser mayor que la cantidad del comprobante.'))
        
        document_id = self.payment_document_id.id
        
        if not self.document_exists:
            document_id = self.env['pos.payment.document'].create({
                'name': self.document_identifier,
                'total_amount': self.voucher_amount,
                'remaining_amount': self.voucher_amount,
                'payment_method_id': self.payment_method_id.id,
                'verified': False,
            }).id
        
        request = self.env['pos.payment.approval.request'].create({
            'payment_document_id': document_id,
            'payment_method_id': self.payment_method_id.id,
            'voucher_amount': self.voucher_amount,
            'amount_requested': self.amount_requested,
            'attachment': self.attachment,
            'attachment_filename': self.attachment_filename,
            'pos_order_id': self.pos_order_id.id,
            'state': 'pending',
        })
        
        message = _(
            "Solicitud de aprobación creada exitosamente.\n\n"
            "Número de solicitud: %(name)s\n"
            "Método de pago: %(method)s\n"
            "Monto solicitado: %(amount)s\n\n"
            "La solicitud está pendiente de aprobación."
        ) % {
            'name': request.name,
            'method': self.payment_method_id.name,
            'amount': self.amount_requested,
        }
        
        self.pos_order_id.message_post(
            body=message,
            subject=_("Solicitud de aprobación creada"),
            message_type='notification'
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Solicitud Creada'),
                'message': message,
                'type': 'success',
                'sticky': True,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }