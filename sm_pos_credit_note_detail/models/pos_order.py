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
    
    
    # Campo editable para conciliar/desconciliar
    reconciled = fields.Boolean(
        string='Conciliado',
        compute='_compute_reconciled',
        inverse='_inverse_reconciled',
        store=True,
        help='Marcar para conciliar, desmarcar para desconciliar'
    )
    
    reconciliation_state = fields.Selection([
        ('pending', 'Pendiente'),
        ('reconciled', 'Conciliado'),
        ('no_account', 'Sin Cuenta NC'),
    ], string='Estado Conciliación', compute='_compute_reconciliation_state', store=True)
    
    balance = fields.Monetary(
        string='Saldo',
        compute='_compute_balance',
        store=True,
        currency_field='currency_id'
    )
    
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
    
    can_reconcile = fields.Boolean(
        string='Puede Conciliar',
        compute='_compute_can_reconcile',
        store=True,
        help='Indica si se puede conciliar esta NC'
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
                original_ref = order.pos_reference.upper()
                if 'REFUND' in original_ref:
                    original_ref = original_ref.replace('REFUND', '').strip()
                    original_ref = original_ref.replace('-', '').strip()
                    
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
    
    @api.depends('credit_note_move_line_id', 'credit_note_move_line_id.reconciled')
    def _compute_reconciled(self):
        for order in self:
            if order.credit_note_move_line_id:
                order.reconciled = order.credit_note_move_line_id.reconciled
            else:
                order.reconciled = False
    
    def _inverse_reconciled(self):
        """Método que se ejecuta cuando se cambia el campo reconciled"""
        for order in self:
            if not order.credit_note_move_line_id:
                raise UserError(_('Esta nota de crédito no tiene un apunte contable en la cuenta 211040020000.'))
            
            current_state = order.credit_note_move_line_id.reconciled
            
            # Si se marcó como conciliado pero no lo está
            if order.reconciled and not current_state:
                order.action_reconcile_credit_note()
            
            # Si se desmarcó pero está conciliado
            elif not order.reconciled and current_state:
                order.action_remove_reconciliation()
    
    @api.depends('credit_note_move_line_id', 'credit_note_move_line_id.reconciled')
    def _compute_can_reconcile(self):
        for order in self:
            if order.credit_note_move_line_id:
                order.can_reconcile = not order.credit_note_move_line_id.reconciled
            else:
                order.can_reconcile = False
    
    @api.depends('reconciled', 'has_nc_account')
    def _compute_reconciliation_state(self):
        for order in self:
            if not order.has_nc_account:
                order.reconciliation_state = 'no_account'
            elif order.reconciled:
                order.reconciliation_state = 'reconciled'
            else:
                order.reconciliation_state = 'pending'

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
        """Abre el widget de conciliación para esta nota de crédito"""
        self.ensure_one()
        
        if not self.credit_note_move_line_id:
            raise UserError(_('Esta nota de crédito no tiene un apunte contable en la cuenta 211040020000.'))
        
        if self.credit_note_move_line_id.reconciled:
            raise UserError(_('Esta nota de crédito ya está conciliada.'))
        
        # Buscar apuntes del mismo cliente para conciliar
        partner_id = self.partner_id.id if self.partner_id else False
        
        # Buscar facturas/apuntes pendientes del cliente
        domain = [
            ('partner_id', '=', partner_id),
            ('account_id.account_type', 'in', ['asset_receivable', 'liability_payable']),
            ('reconciled', '=', False),
            ('parent_state', '=', 'posted'),
            ('amount_residual', '!=', 0),
        ]
        
        move_lines = self.env['account.move.line'].search(domain)
        
        # Incluir la línea de la NC
        move_lines |= self.credit_note_move_line_id
        
        return {
            'name': _('Conciliar Nota de Crédito'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'tree',
            'domain': [('id', 'in', move_lines.ids)],
            'context': {
                'default_partner_id': partner_id,
                'search_default_unreconciled': 1,
            },
            'target': 'current',
        }
    
    def action_view_reconciliation(self):
        """Ver la conciliación completa de esta NC"""
        self.ensure_one()
        
        if not self.credit_note_move_line_id:
            raise UserError(_('Esta nota de crédito no tiene un apunte contable en la cuenta 211040020000.'))
        
        if not self.credit_note_move_line_id.reconciled:
            raise UserError(_('Esta nota de crédito aún no está conciliada.'))
        
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
            return True
        
        if not self.credit_note_move_line_id.reconciled:
            return True
        
        # Desconciliar
        self.credit_note_move_line_id.remove_move_reconcile()
        
        return True


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
        domain=[('is_credit_note', '=', True)]
    )
    
    @api.depends('order_ids', 'order_ids.is_credit_note', 'order_ids.credit_note_amount', 'order_ids.has_nc_account')
    def _compute_credit_note_info(self):
        for session in self:
            credit_notes = session.order_ids.filtered(lambda o: o.is_credit_note and o.has_nc_account)
            session.credit_note_count = len(credit_notes)
            session.credit_note_total = sum(credit_notes.mapped('credit_note_amount'))