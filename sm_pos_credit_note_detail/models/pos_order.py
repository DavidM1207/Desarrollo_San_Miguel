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
        """Abre la vista de apuntes contables para conciliar/desconciliar
        Muestra el detalle de NC de la sesión y TODAS las NC en la cuenta 211040020000"""
        self.ensure_one()
        
        if not self.account_move:
            raise UserError(_('Esta nota de crédito no tiene un asiento contable asociado.'))
        
        # Buscar TODAS las NC que comparten el mismo asiento contable (sesión agrupada)
        all_nc_in_session = self.env['pos.order'].search([
            ('session_id', '=', self.session_id.id),
            ('is_credit_note', '=', True)
        ]) if self.session_id else self.browse(self.id)
        
        # Buscar la cuenta 211040020000 Notas de Crédito por Aplicar
        nc_account = self.env['account.account'].search([
            ('code', '=', '211040020000')
        ], limit=1)
        
        # Si no existe la cuenta específica, buscar cualquier cuenta reconciliable del asiento
        if not nc_account:
            move_lines = self.account_move.line_ids.filtered(
                lambda l: l.account_id.reconcile
            )
            if not move_lines:
                raise UserError(_('No hay líneas con cuentas reconciliables en el asiento contable.'))
            nc_account = move_lines[0].account_id
        
        # Obtener el partner (si existe)
        partner_id = self.partner_id.id if self.partner_id else False
        
        # Construir dominio para buscar TODOS los apuntes de la cuenta 211040020000
        domain = [
            ('account_id', '=', nc_account.id),
            ('parent_state', '=', 'posted'),
        ]
        
        # NO filtrar por partner para ver TODAS las NC de la cuenta
        # Si quieres filtrar por partner, descomenta la siguiente línea:
        # if partner_id:
        #     domain.append(('partner_id', '=', partner_id))
        
        all_lines = self.env['account.move.line'].search(domain, order='date desc, id desc')
        
        # Construir el nombre de la ventana con detalle de NC de esta sesión
        if len(all_nc_in_session) > 1:
            nc_references = ', '.join(all_nc_in_session.mapped('pos_reference')[:5])  # Primeras 5
            if len(all_nc_in_session) > 5:
                nc_references += f' ... (+{len(all_nc_in_session) - 5} más)'
            window_name = _('Conciliación - Sesión %s con %s NC') % (
                self.session_id.name if self.session_id else 'N/A',
                len(all_nc_in_session)
            )
        else:
            window_name = _('Gestionar Conciliación - %s') % self.pos_reference
        
        # Construir el mensaje de ayuda con el detalle
        help_text = '<div style="padding: 10px;">'
        help_text += '<h4>📋 Apuntes de la cuenta: %s - Notas de Crédito por Aplicar</h4>' % nc_account.code
        
        # Información de esta sesión
        if len(all_nc_in_session) > 1:
            help_text += '<div style="background-color: #e8f5e9; padding: 10px; margin: 10px 0; border-radius: 5px;">'
            help_text += '<h5>🔍 Detalle de NC en esta Sesión (%s):</h5>' % (self.session_id.name if self.session_id else 'N/A')
            help_text += '<table style="width: 100%; border-collapse: collapse;">'
            help_text += '<tr style="background-color: #c8e6c9;"><th style="padding: 5px; text-align: left;">Referencia</th><th style="padding: 5px; text-align: right;">Monto</th><th style="padding: 5px; text-align: center;">Estado</th></tr>'
            
            total_session = 0
            for nc in all_nc_in_session:
                estado = '✅ Conciliada' if nc.reconciled else '⏳ Pendiente'
                color_fila = '#ffffff' if nc.reconciled else '#fff9c4'
                help_text += '<tr style="background-color: %s;"><td style="padding: 5px;">%s</td><td style="padding: 5px; text-align: right;">%s%s</td><td style="padding: 5px; text-align: center;">%s</td></tr>' % (
                    color_fila,
                    nc.pos_reference or nc.name,
                    nc.currency_id.symbol,
                    '{:,.2f}'.format(nc.credit_note_amount),
                    estado
                )
                total_session += nc.credit_note_amount
            
            help_text += '<tr style="background-color: #a5d6a7; font-weight: bold;"><td style="padding: 5px;">TOTAL SESIÓN</td><td style="padding: 5px; text-align: right;">%s%s</td><td></td></tr>' % (
                all_nc_in_session[0].currency_id.symbol if all_nc_in_session else '',
                '{:,.2f}'.format(total_session)
            )
            help_text += '</table>'
            help_text += '</div>'
        
        # Instrucciones
        help_text += '<div style="background-color: #e3f2fd; padding: 10px; margin: 10px 0; border-radius: 5px;">'
        help_text += '<h5>📝 Instrucciones para Conciliar:</h5>'
        help_text += '<ol style="margin: 5px 0;">'
        help_text += '<li>A continuación verás <b>TODAS las NC</b> disponibles en la cuenta %s</li>' % nc_account.code
        help_text += '<li>Selecciona los apuntes que deseas conciliar (usa los <b>checkboxes</b>)</li>'
        help_text += '<li>Puedes seleccionar NC de esta sesión u otras sesiones</li>'
        help_text += '<li>Ve al menú <b>"Acción"</b> en la parte superior</li>'
        help_text += '<li>Selecciona <b>"Reconciliar apuntes"</b></li>'
        help_text += '</ol>'
        help_text += '</div>'
        
        # Resumen de apuntes disponibles
        total_apuntes = len(all_lines)
        apuntes_conciliados = len(all_lines.filtered(lambda l: l.reconciled))
        apuntes_pendientes = total_apuntes - apuntes_conciliados
        
        help_text += '<div style="background-color: #fff3e0; padding: 10px; margin: 10px 0; border-radius: 5px;">'
        help_text += '<h5>📊 Resumen de Apuntes Disponibles:</h5>'
        help_text += '<ul style="margin: 5px 0;">'
        help_text += '<li><b>Total apuntes:</b> %s</li>' % total_apuntes
        help_text += '<li><b>Conciliados:</b> %s ✅</li>' % apuntes_conciliados
        help_text += '<li><b>Pendientes:</b> %s ⏳</li>' % apuntes_pendientes
        help_text += '</ul>'
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
                'search_default_unreconciled': 1,  # Mostrar por defecto las no conciliadas
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