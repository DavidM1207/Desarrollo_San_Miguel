from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo import _
from datetime import timedelta


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
    
    @api.model
    def load_all_credit_notes(self):
        """Carga todas las NC - Misma lógica que action_reconcile_credit_note"""
        # Generar token único
        import uuid
        search_token = str(uuid.uuid4())
        
        # Buscar la cuenta 211040020000
        nc_account = self.env['account.account'].search([
            ('code', '=', '211040020000')
        ], limit=1)
        
        if not nc_account:
            raise UserError(_('No se encontró la cuenta 211040020000 - Notas de Crédito por Aplicar'))
        
        # Limpiar líneas anteriores
        self.env['credit.note.line.view'].search([]).unlink()
        
        # ===== MISMA LÓGICA QUE action_reconcile_credit_note =====
        
        # Buscar TODAS las sesiones cerradas (del mes actual para optimizar)
        today = fields.Date.today()
        first_day = today.replace(day=1)
        
        all_sessions = self.env['pos.session'].search([
            ('state', '=', 'closed'),
            ('stop_at', '>=', first_day),
        ], order='stop_at desc')
        
        for session in all_sessions:
            # Buscar NC de esta sesión
            nc_orders = self.env['pos.order'].search([
                ('session_id', '=', session.id),
                ('is_credit_note', '=', True),
            ])
            
            # Buscar órdenes con pagos NC
            orders_with_nc = self.env['pos.order'].search([
                ('session_id', '=', session.id),
                ('amount_total', '>', 0),
            ])
            
            has_refacturacion = False
            for order in orders_with_nc:
                nc_payments = order.payment_ids.filtered(
                    lambda p: 'crédit' in (p.payment_method_id.name or '').lower() or 
                             'credit' in (p.payment_method_id.name or '').lower() or
                             'nota' in (p.payment_method_id.name or '').lower()
                )
                if nc_payments:
                    has_refacturacion = True
                    break
            
            if nc_orders:
                # Buscar el apunte contable
                move_line = False
                if session.move_id:
                    move_lines_credit = session.move_id.line_ids.filtered(
                        lambda l: l.account_id.id == nc_account.id and l.credit > 0
                    )
                    move_lines_debit = session.move_id.line_ids.filtered(
                        lambda l: l.account_id.id == nc_account.id and l.debit > 0
                    )
                    
                    if move_lines_credit:
                        move_line = move_lines_credit[0]
                    elif move_lines_debit:
                        move_line = move_lines_debit[0]
                
                # Saltar si está conciliado
                if move_line and move_line.reconciled:
                    continue
                
                # Determinar tipo
                nc_type = 'nota_credito'
                if move_line:
                    if move_line.debit > 0:
                        nc_type = 'refacturacion'
                    elif move_line.credit > 0:
                        nc_type = 'nota_credito'
                
                vendedor = session.user_id.name if session.user_id else ''
                
                # Crear líneas por cada NC
                for nc in nc_orders:
                    factura_origen = ''
                    if nc.origin_order_id and nc.origin_order_id.account_move:
                        factura_origen = nc.origin_order_id.account_move.name
                    
                    debit_amount = 0.0
                    credit_amount = 0.0
                    
                    if nc_type == 'nota_credito':
                        credit_amount = nc.credit_note_amount
                    else:
                        debit_amount = nc.credit_note_amount
                    
                    self.env['credit.note.line.view'].create({
                        'search_token': search_token,
                        'date': nc.date_order.date() if nc.date_order else fields.Date.today(),
                        'name': nc.pos_reference or nc.name,
                        'account_id': nc_account.id,
                        'session_name': session.name,
                        'nc_type': nc_type,
                        'description': 'NC del %s factura nota %s' % (session.name, factura_origen),
                        'debit': debit_amount,
                        'credit': credit_amount,
                        'currency_id': nc.currency_id.id,
                        'vendedor': vendedor,
                        'move_line_id': move_line.id if move_line else False,
                        'pos_order_id': nc.id,
                    })
            
            # Procesar refacturaciones
            if has_refacturacion:
                move_line_debit = False
                if session.move_id:
                    move_line_debit = session.move_id.line_ids.filtered(
                        lambda l: l.account_id.id == nc_account.id and l.debit > 0
                    )
                    move_line_debit = move_line_debit[0] if move_line_debit else False
                
                if move_line_debit and move_line_debit.reconciled:
                    continue
                
                vendedor = session.user_id.name if session.user_id else ''
                
                for order in orders_with_nc:
                    nc_payments = order.payment_ids.filtered(
                        lambda p: 'crédit' in (p.payment_method_id.name or '').lower() or 
                                 'credit' in (p.payment_method_id.name or '').lower() or
                                 'nota' in (p.payment_method_id.name or '').lower()
                    )
                    
                    if nc_payments:
                        for payment in nc_payments:
                            self.env['credit.note.line.view'].create({
                                'search_token': search_token,
                                'date': order.date_order.date() if order.date_order else fields.Date.today(),
                                'name': order.pos_reference or order.name,
                                'account_id': nc_account.id,
                                'session_name': session.name,
                                'nc_type': 'refacturacion',
                                'description': 'Orden %s Uso NC' % (order.pos_reference or order.name),
                                'debit': abs(payment.amount),
                                'credit': 0.0,
                                'currency_id': order.currency_id.id,
                                'vendedor': vendedor,
                                'move_line_id': move_line_debit.id if move_line_debit else False,
                                'pos_order_id': order.id,
                            })
        
        # Contar líneas creadas
        created_lines = self.env['credit.note.line.view'].search_count([('search_token', '=', search_token)])
        
        # Abrir la vista
        return {
            'name': _('Libro Mayor - Notas de Crédito (%s registros)') % created_lines,
            'type': 'ir.actions.act_window',
            'res_model': 'credit.note.line.view',
            'view_mode': 'tree',
            'view_id': self.env.ref('sm_pos_credit_note_detail.view_credit_note_line_expanded_tree').id,
            'domain': [('search_token', '=', search_token)],
            'context': {
                'create': False,
                'edit': False,
                'delete': False,
            },
            'target': 'current',
        }

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
        """Abre una vista expandida mostrando cada NC como línea individual"""
        self.ensure_one()
        
        # Generar token único para esta búsqueda
        import uuid
        search_token = str(uuid.uuid4())
        
        # Buscar la cuenta 211040020000
        nc_account = self.env['account.account'].search([
            ('code', '=', '211040020000')
        ], limit=1)
        
        if not nc_account:
            raise UserError(_('No se encontró la cuenta 211040020000 - Notas de Crédito por Aplicar'))
        
        # Limpiar líneas anteriores
        self.env['credit.note.line.view'].search([('search_token', '=', search_token)]).unlink()
        
        # ===== BUSCAR TODAS LAS SESIONES CERRADAS (SIN LÍMITE) =====
        all_sessions = self.env['pos.session'].search([
            ('state', '=', 'closed'),
        ], order='stop_at desc')
        
        for session in all_sessions:
            # Buscar NC de esta sesión
            nc_orders = self.env['pos.order'].search([
                ('session_id', '=', session.id),
                ('is_credit_note', '=', True),
            ])
            
            # Buscar órdenes normales de esta sesión que usaron NC como pago
            orders_with_nc = self.env['pos.order'].search([
                ('session_id', '=', session.id),
                ('amount_total', '>', 0),
            ])
            
            has_refacturacion = False
            for order in orders_with_nc:
                nc_payments = order.payment_ids.filtered(
                    lambda p: 'crédit' in (p.payment_method_id.name or '').lower() or 
                             'credit' in (p.payment_method_id.name or '').lower() or
                             'nota' in (p.payment_method_id.name or '').lower()
                )
                if nc_payments:
                    has_refacturacion = True
                    break
            
            if nc_orders:
                # Buscar el apunte contable de esta sesión en la cuenta NC
                move_line = False
                if session.move_id:
                    # Buscar línea con crédito (NC) o débito (Refacturación)
                    move_lines_credit = session.move_id.line_ids.filtered(
                        lambda l: l.account_id.id == nc_account.id and l.credit > 0
                    )
                    move_lines_debit = session.move_id.line_ids.filtered(
                        lambda l: l.account_id.id == nc_account.id and l.debit > 0
                    )
                    
                    # Si hay crédito, usar esa línea para NC
                    if move_lines_credit:
                        move_line = move_lines_credit[0]
                    # Si solo hay débito, es refacturación
                    elif move_lines_debit:
                        move_line = move_lines_debit[0]
                
                # Saltar si está conciliado
                if move_line and move_line.reconciled:
                    continue
                
                # Determinar el tipo basado en el pago de la sesión
                # Si el pago es negativo = Nota de Crédito
                # Si el pago es positivo = Refacturación
                nc_type = 'nota_credito'
                if move_line:
                    # Si tiene débito > 0 = Refacturación (se usó la NC)
                    # Si tiene crédito > 0 = Nota de Crédito (se generó la NC)
                    if move_line.debit > 0:
                        nc_type = 'refacturacion'
                    elif move_line.credit > 0:
                        nc_type = 'nota_credito'
                
                # Determinar vendedor (usuario de la sesión)
                vendedor = session.user_id.name if session.user_id else ''
                
                # Crear UNA línea por cada NC individual
                for nc in nc_orders:
                    factura_origen = ''
                    # Buscar factura de la orden original que generó esta NC
                    if nc.origin_order_id and nc.origin_order_id.account_move:
                        factura_origen = nc.origin_order_id.account_move.name
                    
                    # Determinar debe/haber según el tipo
                    debit_amount = 0.0
                    credit_amount = 0.0
                    
                    if nc_type == 'nota_credito':
                        credit_amount = nc.credit_note_amount
                    else:
                        debit_amount = nc.credit_note_amount
                    
                    self.env['credit.note.line.view'].create({
                        'search_token': search_token,
                        'date': nc.date_order.date() if nc.date_order else fields.Date.today(),
                        'name': nc.pos_reference or nc.name,
                        'account_id': nc_account.id,
                        'session_name': session.name,
                        'nc_type': nc_type,
                        'description': 'NC del %s factura nota %s' % (session.name, factura_origen),
                        'debit': debit_amount,
                        'credit': credit_amount,
                        'currency_id': nc.currency_id.id,
                        'vendedor': vendedor,
                        'move_line_id': move_line.id if move_line else False,
                        'pos_order_id': nc.id,
                    })
            
            # Procesar refacturaciones por separado si las hay
            if has_refacturacion:
                # Buscar el apunte con débito
                move_line_debit = False
                if session.move_id:
                    move_line_debit = session.move_id.line_ids.filtered(
                        lambda l: l.account_id.id == nc_account.id and l.debit > 0
                    )
                    move_line_debit = move_line_debit[0] if move_line_debit else False
                
                # Saltar si está conciliado
                if move_line_debit and move_line_debit.reconciled:
                    continue
                
                vendedor = session.user_id.name if session.user_id else ''
                
                for order in orders_with_nc:
                    nc_payments = order.payment_ids.filtered(
                        lambda p: 'crédit' in (p.payment_method_id.name or '').lower() or 
                                 'credit' in (p.payment_method_id.name or '').lower() or
                                 'nota' in (p.payment_method_id.name or '').lower()
                    )
                    
                    if nc_payments:
                        for payment in nc_payments:
                            self.env['credit.note.line.view'].create({
                                'search_token': search_token,
                                'date': order.date_order.date() if order.date_order else fields.Date.today(),
                                'name': order.pos_reference or order.name,
                                'account_id': nc_account.id,
                                'session_name': session.name,
                                'nc_type': 'refacturacion',
                                'description': 'Orden %s Uso NC' % (order.pos_reference or order.name),
                                'debit': abs(payment.amount),
                                'credit': 0.0,
                                'currency_id': order.currency_id.id,
                                'vendedor': vendedor,
                                'move_line_id': move_line_debit.id if move_line_debit else False,
                                'pos_order_id': order.id,
                            })
        
        # Contar líneas creadas
        created_lines = self.env['credit.note.line.view'].search_count([('search_token', '=', search_token)])
        
        if created_lines == 0:
            raise UserError(_('No se encontraron notas de crédito pendientes de conciliar.'))
        
        # Abrir la vista
        return {
            'name': _('Notas de Crédito Pendientes (%s)') % created_lines,
            'type': 'ir.actions.act_window',
            'res_model': 'credit.note.line.view',
            'view_mode': 'tree',
            'views': [(self.env.ref('sm_pos_credit_note_detail.view_credit_note_line_expanded_tree').id, 'tree')],
            'domain': [('search_token', '=', search_token)],
            'context': {'create': False, 'edit': False, 'delete': False},
            'target': 'current',
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