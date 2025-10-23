from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo import _


class PosOrder(models.Model):
    _inherit = 'pos.order'

    is_credit_note = fields.Boolean(
        string='Es Nota de Crédito',
        compute='_compute_is_credit_note',
        store=True,
        help='Indica si esta orden es una nota de crédito'
    )
    
    credit_note_amount = fields.Monetary(
        string='Monto NC',
        compute='_compute_credit_note_amount',
        store=True,
        currency_field='currency_id',
        help='Monto de la nota de crédito'
    )
    
    origin_order_id = fields.Many2one(
        'pos.order',
        string='Orden Original',
        compute='_compute_origin_order',
        store=True,
        help='Orden que originó esta nota de crédito'
    )
    
    origin_invoice_id = fields.Many2one(
        'account.move',
        string='Factura Origen',
        related='origin_order_id.account_move',
        store=True,
        help='Factura que originó esta nota de crédito'
    )
    
    origin_invoice_name = fields.Char(
        string='Número Factura Origen',
        related='origin_invoice_id.name',
        store=True
    )
    
    credit_note_move_line_id = fields.Many2one(
        'account.move.line',
        string='Apunte Contable NC',
        compute='_compute_credit_note_move_line',
        store=True,
        help='Apunte contable de la nota de crédito'
    )
    
    reconciled = fields.Boolean(
        string='Conciliado',
        related='credit_note_move_line_id.reconciled',
        store=True
    )
    
    balance = fields.Monetary(
        string='Saldo',
        compute='_compute_balance',
        store=True,
        currency_field='currency_id'
    )
    
    # Nuevo campo para el método de pago
    payment_method_name = fields.Char(
        string='Método de Pago',
        compute='_compute_payment_method',
        store=True,
        help='Método de pago utilizado en la nota de crédito'
    )
    
    has_nc_account = fields.Boolean(
        string='Tiene Cuenta NC',
        compute='_compute_has_nc_account',
        store=True,
        help='Indica si tiene apunte en cuenta 211040020000'
    )
    
    @api.depends('amount_total')
    def _compute_is_credit_note(self):
        for order in self:
            order.is_credit_note = order.amount_total < 0
    
    @api.depends('amount_total', 'is_credit_note')
    def _compute_credit_note_amount(self):
        for order in self:
            if order.is_credit_note:
                order.credit_note_amount = abs(order.amount_total)
            else:
                order.credit_note_amount = 0.0
    
    @api.depends('pos_reference', 'name')
    def _compute_origin_order(self):
        for order in self:
            origin = False
            if order.is_credit_note and order.pos_reference:
                # Extraer referencia original del refund
                original_ref = order.pos_reference.upper()
                if 'REFUND' in original_ref:
                    # Remover REFUND y limpiar
                    original_ref = original_ref.replace('REFUND', '').strip()
                    original_ref = original_ref.replace('-', '').strip()
                    
                    # Buscar orden original
                    origin = self.env['pos.order'].search([
                        ('pos_reference', 'ilike', original_ref),
                        ('amount_total', '>', 0),
                        ('id', '!=', order.id)
                    ], limit=1)
            
            order.origin_order_id = origin.id if origin else False
    
    @api.depends('account_move', 'account_move.line_ids', 'is_credit_note')
    def _compute_credit_note_move_line(self):
        for order in self:
            move_line = False
            if order.is_credit_note and order.account_move:
                # Buscar el apunte contable con la cuenta de NC 211040020000
                move_line = order.account_move.line_ids.filtered(
                    lambda l: l.account_id.code == '211040020000' and l.credit > 0
                )
                if move_line:
                    move_line = move_line[0]
            
            order.credit_note_move_line_id = move_line.id if move_line else False
    
    @api.depends('credit_note_move_line_id')
    def _compute_has_nc_account(self):
        for order in self:
            order.has_nc_account = bool(order.credit_note_move_line_id)
    
    @api.depends('credit_note_move_line_id', 'credit_note_move_line_id.amount_residual')
    def _compute_balance(self):
        for order in self:
            if order.credit_note_move_line_id:
                order.balance = abs(order.credit_note_move_line_id.amount_residual)
            else:
                order.balance = 0.0
    
    @api.depends('payment_ids', 'payment_ids.payment_method_id')
    def _compute_payment_method(self):
        for order in self:
            payment_method = ''
            if order.payment_ids:
                # Obtener todos los métodos de pago únicos
                methods = order.payment_ids.mapped('payment_method_id.name')
                payment_method = ', '.join(methods) if methods else 'Sin método'
            else:
                payment_method = 'Sin método'
            
            order.payment_method_name = payment_method
    
    def action_view_origin_invoice(self):
        """Abre la factura origen que generó esta nota de crédito"""
        self.ensure_one()
        if not self.origin_invoice_id:
            raise UserError(_('No hay factura origen asociada a esta nota de crédito.'))
        
        return {
            'name': _('Factura Origen'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.origin_invoice_id.id,
            'target': 'current',
        }
    
    def action_reconcile_credit_note(self):
        """Abre el asistente de conciliación para esta nota de crédito"""
        self.ensure_one()
        
        if not self.credit_note_move_line_id:
            raise UserError(_('Esta nota de crédito no tiene un apunte contable en la cuenta 211040020000.'))
        
        if self.reconciled:
            raise UserError(_('Esta nota de crédito ya está conciliada.'))
        
        # Abrir vista de conciliación manual
        return {
            'name': _('Conciliar Nota de Crédito'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'tree',
            'views': [(False, 'list')],
            'domain': [
                ('account_id', '=', self.credit_note_move_line_id.account_id.id),
                ('reconciled', '=', False),
                ('parent_state', '=', 'posted'),
                '|',
                ('id', '=', self.credit_note_move_line_id.id),
                '&',
                ('partner_id', '=', self.partner_id.id if self.partner_id else False),
                ('amount_residual', '!=', 0)
            ],
            'context': {
                'search_default_unreconciled': 1,
                'default_partner_id': self.partner_id.id if self.partner_id else False,
            },
            'target': 'current',
        }
    
    def action_view_reconciliation(self):
        """Ver la conciliación completa de esta NC"""
        self.ensure_one()
        
        if not self.credit_note_move_line_id:
            raise UserError(_('Esta nota de crédito no tiene un apunte contable en la cuenta 211040020000.'))
        
        if not self.reconciled:
            raise UserError(_('Esta nota de crédito aún no está conciliada.'))
        
        # Mostrar todos los apuntes de la conciliación
        reconcile_lines = self.credit_note_move_line_id.matched_debit_ids.mapped('debit_move_id') | \
                         self.credit_note_move_line_id.matched_credit_ids.mapped('credit_move_id') | \
                         self.credit_note_move_line_id
        
        return {
            'name': _('Detalles de Conciliación'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', reconcile_lines.ids)],
            'context': {'create': False},
            'target': 'current',
        }
    
    def action_remove_reconciliation(self):
        """Desconciliar esta nota de crédito"""
        self.ensure_one()
        
        if not self.credit_note_move_line_id:
            raise UserError(_('Esta nota de crédito no tiene un apunte contable en la cuenta 211040020000.'))
        
        if not self.reconciled:
            raise UserError(_('Esta nota de crédito no está conciliada.'))
        
        # Desconciliar
        self.credit_note_move_line_id.remove_move_reconcile()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Conciliación eliminada'),
                'message': _('La nota de crédito ha sido desconciliada exitosamente.'),
                'type': 'success',
                'sticky': False,
            }
        }


class PosSession(models.Model):
    _inherit = 'pos.session'
    
    credit_note_count = fields.Integer(
        string='Cantidad NC',
        compute='_compute_credit_note_info',
        store=True
    )
    
    credit_note_total = fields.Monetary(
        string='Total NC',
        compute='_compute_credit_note_info',
        store=True,
        currency_field='currency_id'
    )
    
    credit_note_ids = fields.One2many(
        'pos.order',
        'session_id',
        string='Notas de Crédito',
        domain=[('is_credit_note', '=', True)]  # SIN filtro de cuenta aquí
    )
    
    @api.depends('order_ids', 'order_ids.is_credit_note', 'order_ids.credit_note_amount', 'order_ids.has_nc_account')
    def _compute_credit_note_info(self):
        for session in self:
            # Solo contar NC que tengan la cuenta 211040020000 PARA EL ENCABEZADO
            credit_notes = session.order_ids.filtered(lambda o: o.is_credit_note and o.has_nc_account)
            session.credit_note_count = len(credit_notes)
            session.credit_note_total = sum(credit_notes.mapped('credit_note_amount'))