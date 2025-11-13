# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError
import logging

_logger = logging.getLogger(__name__)


class PosPaymentApprovalCreateWizard(models.TransientModel):
    _name = 'pos.payment.approval.create.wizard'
    _description = 'Solicitud de Aprobación de Pago'
    
    # Deshabilitar verificación de acceso para este modelo
    def _check_access_rights(self, *args, **kwargs):
        """Sobrescribir para permitir acceso sin permisos explícitos"""
        return True
    
    def check_access_rights(self, *args, **kwargs):
        """Sobrescribir para permitir acceso sin permisos explícitos"""
        return True
    
    def check_access_rule(self, *args, **kwargs):
        """Sobrescribir para permitir acceso sin permisos explícitos"""
        return True
    
    pos_order_id = fields.Many2one(
        'pos.order',
        string='Orden POS',
        required=True,
        readonly=True
    )
    
    document_identifier = fields.Char(
        string='Número de Documento',
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
        attachment=True
    )
    
    attachment_filename = fields.Char(
        string='Nombre del Archivo'
    )
    
    @api.model
    def create(self, vals):
        """Override create para usar siempre sudo"""
        return super(PosPaymentApprovalCreateWizard, self.sudo()).create(vals)
    
    def write(self, vals):
        """Override write para usar siempre sudo"""
        return super(PosPaymentApprovalCreateWizard, self.sudo()).write(vals)
    
    def read(self, fields=None, load='_classic_read'):
        """Override read para usar siempre sudo"""
        return super(PosPaymentApprovalCreateWizard, self.sudo()).read(fields, load)
    
    def action_search_document(self):
        """Busca el documento en la BD"""
        # Usar sudo para toda la operación
        self = self.sudo()
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
        # Usar sudo para toda la operación
        self = self.sudo()
        self.ensure_one()
        
        _logger.info("=" * 80)
        _logger.info("SUBMIT REQUEST")
        
        # VALIDACIONES
        if not self.document_identifier:
            raise UserError(_('Debe ingresar un número de documento.'))
        
        if not self.payment_method_id:
            raise UserError(_('Debe seleccionar un método de pago.'))
        
        if not self.voucher_amount or self.voucher_amount <= 0:
            raise UserError(_('Debe ingresar una cantidad de comprobante válida.'))
        
        if not self.amount_requested or self.amount_requested <= 0:
            raise UserError(_('Debe ingresar una cantidad a utilizar válida.'))
        
        if self.amount_requested > self.voucher_amount:
            raise UserError(_('La cantidad a utilizar no puede ser mayor que la cantidad del comprobante.'))
        
        if not self.attachment:
            raise UserError(_('Debe adjuntar un documento.'))
        
        _logger.info("Documento: %s", self.document_identifier)
        _logger.info("Método: %s", self.payment_method_id.name)
        _logger.info("Voucher: %s", self.voucher_amount)
        _logger.info("Monto: %s", self.amount_requested)
        
        document_id = self.payment_document_id.id
        
        # Si el documento no existe, crearlo
        if not self.document_exists:
            _logger.info("Creando nuevo documento de pago")
            document_id = self.env['pos.payment.document'].create({
                'name': self.document_identifier,
                'total_amount': self.voucher_amount,
                'remaining_amount': self.voucher_amount,
                'payment_method_id': self.payment_method_id.id,
                'verified': False,
            }).id
        
        # Crear solicitud de aprobación
        _logger.info("Creando solicitud de aprobación")
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
        
        _logger.info("✓ Solicitud creada: %s", request.name)
        
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
        
        _logger.info("=" * 80)
        
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