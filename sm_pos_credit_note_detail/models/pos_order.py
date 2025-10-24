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
        compute='_compute_reconciled',
        store=True,
        help='Estado de conciliación del asiento contable'
    )
    
    reconciliation_state = fields.Selection([
        ('pending', 'No Conciliado'),
        ('reconciled', 'Conciliado'),
    ], string='Estado', compute='_compute_reconciliation_state', store=True)
    
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
    
    @api.depends('account_move', 'account_move.line_ids', 'is_credit_note', 'account_move.state')
    def _compute_credit_note_move_line(self):
        """Busca el apunte contable del asiento de la nota de crédito"""
        for order in self:
            move_line = False
            
            if order.is_credit_note and order.account_move and order.account_move.state == 'posted':
                # Buscar líneas con crédito (positivas) en cuentas reconciliables
                credit_lines = order.account_move.line_ids.filtered(
                    lambda l: l.credit > 0 and l.account_id.reconcile
                )
                
                if credit_lines:
                    # Priorizar cuentas por cobrar
                    receivable = credit_lines.filtered(
                        lambda l: l.account_id.account_type == 'asset_receivable'
                    )
                    move_line = receivable[0] if receivable else credit_lines[0]
            
            order.credit_note_move_line_id = move_line.id if move_line else False
    
    @api.depends('credit_note_move_line_id', 'credit_note_move_line_id.account_id')
    def _compute_has_nc_account(self):
        for order in self:
            if order.credit_note_move_line_id:
                order.has_nc_account = order.credit_note_move_line_id.account_id.code == '211040020000'
            else:
                order.has_nc_account = False
    
    @api.depends('account_move', 'account_move.line_ids', 'account_move.line_ids.reconciled')
    def _compute_reconciled(self):
        """Verifica si el asiento contable de la NC está conciliado"""
        for order in self:
            is_reconciled = False
            
            if order.account_move and order.account_move.state == 'posted':
                # Verificar si alguna línea reconciliable del asiento está conciliada
                reconcilable_lines = order.account_move.line_ids.filtered(
                    lambda l: l.account_id.reconcile and (l.debit > 0 or l.credit > 0)
                )
                
                if reconcilable_lines:
                    # Si al menos una línea está conciliada, considerarlo conciliado
                    is_reconciled = any(line.reconciled for line in reconcilable_lines)
            
            order.reconciled = is_reconciled
    
    @api.depends('reconciled')
    def _compute_reconciliation_state(self):
        for order in self:
            if order.reconciled:
                order.reconciliation_state = 'reconciled'
            else:
                order.reconciliation_state = 'pending'
    
    @api.depends('credit_note_move_line_id', 'reconciled')
    def _compute_can_reconcile(self):
        for order in self:
            order.can_reconcile = bool(order.credit_note_move_line_id) and not order.reconciled
    
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
        """Abre la vista de apuntes contables mostrando:
        1. Detalle de NC de esta sesión
        2. TODAS las NC disponibles en la cuenta 211040020000
        3. Permite conciliar NC originales con sus refacturaciones"""
        self.ensure_one()
        
        if not self.account_move:
            raise UserError(_('Esta nota de crédito no tiene un asiento contable asociado.'))
        
        # Buscar TODAS las NC de esta sesión
        all_nc_in_session = self.env['pos.order'].search([
            ('session_id', '=', self.session_id.id),
            ('is_credit_note', '=', True)
        ]) if self.session_id else self.browse(self.id)
        
        # Buscar la cuenta 211040020000
        nc_account = self.env['account.account'].search([
            ('code', '=', '211040020000')
        ], limit=1)
        
        if not nc_account:
            # Si no existe, buscar cualquier cuenta reconciliable
            move_lines = self.account_move.line_ids.filtered(
                lambda l: l.account_id.reconcile
            )
            if not move_lines:
                raise UserError(_('No hay líneas con cuentas reconciliables en el asiento contable.'))
            nc_account = move_lines[0].account_id
        
        # Buscar TODOS los apuntes de la cuenta 211040020000
        domain = [
            ('account_id', '=', nc_account.id),
            ('parent_state', '=', 'posted'),
        ]
        
        all_lines = self.env['account.move.line'].search(domain, order='date desc, id desc')
        
        # Construir título
        if len(all_nc_in_session) > 1:
            window_name = _('Conciliación NC - Sesión %s (%s NC)') % (
                self.session_id.name if self.session_id else 'N/A',
                len(all_nc_in_session)
            )
        else:
            window_name = _('Conciliar NC - %s') % self.pos_reference
        
        # Construir mensaje detallado
        help_text = '<div style="padding: 15px; font-family: Arial, sans-serif;">'
        help_text += '<h3 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">📋 Conciliación de Notas de Crédito</h3>'
        
        # Sección 1: Detalle de NC en esta sesión
        if len(all_nc_in_session) > 1:
            help_text += '<div style="background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%); padding: 15px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #4caf50;">'
            help_text += '<h4 style="margin-top: 0; color: #2e7d32;">🔍 Notas de Crédito en Sesión: %s</h4>' % (self.session_id.name if self.session_id else 'N/A')
            help_text += '<table style="width: 100%; border-collapse: collapse; background: white; border-radius: 4px; overflow: hidden;">'
            help_text += '<thead><tr style="background-color: #4caf50; color: white;">'
            help_text += '<th style="padding: 10px; text-align: left;">Referencia NC</th>'
            help_text += '<th style="padding: 10px; text-align: left;">Cliente</th>'
            help_text += '<th style="padding: 10px; text-align: right;">Monto</th>'
            help_text += '<th style="padding: 10px; text-align: center;">Estado</th>'
            help_text += '</tr></thead><tbody>'
            
            total_session = 0
            for idx, nc in enumerate(all_nc_in_session):
                estado = '✅ Conciliada' if nc.reconciled else '⏳ Pendiente'
                bg_color = '#f1f8e9' if idx % 2 == 0 else '#ffffff'
                help_text += '<tr style="background-color: %s;">' % bg_color
                help_text += '<td style="padding: 8px;"><strong>%s</strong></td>' % (nc.pos_reference or nc.name)
                help_text += '<td style="padding: 8px;">%s</td>' % (nc.partner_id.name if nc.partner_id else 'Sin cliente')
                help_text += '<td style="padding: 8px; text-align: right;"><strong>%s%s</strong></td>' % (
                    nc.currency_id.symbol,
                    '{:,.2f}'.format(nc.credit_note_amount)
                )
                help_text += '<td style="padding: 8px; text-align: center;">%s</td>' % estado
                help_text += '</tr>'
                total_session += nc.credit_note_amount
            
            help_text += '<tr style="background-color: #c8e6c9; font-weight: bold;">'
            help_text += '<td colspan="2" style="padding: 10px;">TOTAL SESIÓN</td>'
            help_text += '<td style="padding: 10px; text-align: right;">%s%s</td>' % (
                all_nc_in_session[0].currency_id.symbol if all_nc_in_session else '',
                '{:,.2f}'.format(total_session)
            )
            help_text += '<td></td></tr>'
            help_text += '</tbody></table>'
            help_text += '</div>'
        
        # Sección 2: Resumen general
        total_apuntes = len(all_lines)
        apuntes_conciliados = len(all_lines.filtered(lambda l: l.reconciled))
        apuntes_pendientes = total_apuntes - apuntes_conciliados
        
        help_text += '<div style="background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%); padding: 15px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #ff9800;">'
        help_text += '<h4 style="margin-top: 0; color: #e65100;">📊 Todos los Apuntes en Cuenta %s</h4>' % nc_account.code
        help_text += '<div style="display: flex; justify-content: space-around; text-align: center;">'
        help_text += '<div style="flex: 1;"><div style="font-size: 24px; font-weight: bold; color: #424242;">%s</div><div style="color: #757575;">Total</div></div>' % total_apuntes
        help_text += '<div style="flex: 1;"><div style="font-size: 24px; font-weight: bold; color: #4caf50;">%s</div><div style="color: #757575;">Conciliados ✅</div></div>' % apuntes_conciliados
        help_text += '<div style="flex: 1;"><div style="font-size: 24px; font-weight: bold; color: #f44336;">%s</div><div style="color: #757575;">Pendientes ⏳</div></div>' % apuntes_pendientes
        help_text += '</div></div>'
        
        # Sección 3: Instrucciones
        help_text += '<div style="background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); padding: 15px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #2196f3;">'
        help_text += '<h4 style="margin-top: 0; color: #0d47a1;">📝 Cómo Conciliar (Refacturaciones)</h4>'
        help_text += '<ol style="margin: 10px 0; padding-left: 20px; line-height: 1.8;">'
        help_text += '<li><strong>Encuentra las NC originales</strong> (las de esta sesión aparecen arriba)</li>'
        help_text += '<li><strong>Encuentra donde se usaron como método de pago</strong> (refacturaciones en otras sesiones)</li>'
        help_text += '<li><strong>Selecciona ambos apuntes</strong> usando los checkboxes</li>'
        help_text += '<li>Ve al menú <strong>"Acción"</strong> → <strong>"Reconciliar apuntes"</strong></li>'
        help_text += '<li>Odoo los conciliará automáticamente si los montos coinciden</li>'
        help_text += '</ol>'
        help_text += '<p style="background: white; padding: 10px; border-radius: 4px; margin-top: 10px;"><strong>💡 Tip:</strong> Usa los filtros de búsqueda para encontrar apuntes por fecha, cliente o monto</p>'
        help_text += '</div>'
        
        help_text += '</div>'
        
        return {
            'name': window_name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list',
            'views': [(False, 'list')],
            'domain': [('id', 'in', all_lines.ids)],
            'context': {
                'create': False,
                'edit': False,
                'group_by': [],
                'search_default_unreconciled': 1,
            },
            'target': 'current',
            'help': help_text,
        }
    
    def action_view_reconciliation(self):
        """Ver la conciliación completa de esta NC"""
        self.ensure_one()
        
        if not self.credit_note_move_line_id:
            raise UserError(_('No se encontró un apunte contable válido para esta nota de crédito.'))
        
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