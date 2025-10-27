from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ReconcileConfirmationWizard(models.TransientModel):
    _name = 'reconcile.confirmation.wizard'
    _description = 'Wizard de Confirmación de Conciliación'
    
    line_count = fields.Integer(string='Líneas Seleccionadas', readonly=True)
    lines_with_move = fields.Integer(string='Líneas con Apunte Contable', readonly=True)
    total_debit = fields.Monetary(string='Total Debe', readonly=True, currency_field='currency_id')
    total_credit = fields.Monetary(string='Total Haber', readonly=True, currency_field='currency_id')
    difference = fields.Monetary(string='Diferencia', readonly=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Moneda', readonly=True)
    line_details = fields.Html(string='Detalle', readonly=True, compute='_compute_line_details')
    move_line_ids = fields.Many2many('account.move.line', string='Apuntes a Conciliar')
    credit_note_line_ids = fields.Many2many('credit.note.line', string='Líneas Seleccionadas')
    
    @api.depends('credit_note_line_ids')
    def _compute_line_details(self):
        """Construir el detalle mostrando los asientos del DIARIO del método de pago"""
        for wizard in self:
            if not wizard.credit_note_line_ids:
                wizard.line_details = '<p>No hay líneas seleccionadas</p>'
                continue
            
            # Buscar la cuenta 211040020000
            nc_account = self.env['account.account'].search([('code', '=', '211040020000')], limit=1)
            
            if not nc_account:
                wizard.line_details = '<p style="color: red;">⚠️ No se encontró la cuenta 211040020000</p>'
                continue
            
            # Obtener las órdenes de las líneas seleccionadas
            orders = wizard.credit_note_line_ids.mapped('pos_order_id').filtered(lambda o: o)
            
            if not orders:
                wizard.line_details = '<p style="color: red;">⚠️ No se encontraron órdenes en las líneas seleccionadas</p>'
                continue
            
            # Obtener las sesiones
            sessions = orders.mapped('session_id').filtered(lambda s: s)
            
            if not sessions:
                wizard.line_details = '<p style="color: red;">⚠️ No se encontraron sesiones</p>'
                continue
            
            # Buscar los payments con método "devolución" o "nota" de esas órdenes
            nc_payments = self.env['pos.payment']
            for order in orders:
                payments = order.payment_ids.filtered(
                    lambda p: 'devolución' in (p.payment_method_id.name or '').lower() or 
                             'devolucion' in (p.payment_method_id.name or '').lower() or
                             'nota' in (p.payment_method_id.name or '').lower()
                )
                nc_payments |= payments
            
            if not nc_payments:
                wizard.line_details = '<p style="color: red;">⚠️ No se encontraron pagos con método Devolución/Nota en las órdenes</p>'
                continue
            
            # Obtener los métodos de pago y sus diarios
            payment_methods = nc_payments.mapped('payment_method_id').filtered(lambda m: m.journal_id)
            
            if not payment_methods:
                wizard.line_details = '<p style="color: red;">⚠️ Los métodos de pago encontrados no tienen diario configurado</p>'
                continue
            
            # Buscar asientos en los DIARIOS de los métodos de pago que contengan el nombre de la sesión
            move_lines_to_reconcile = self.env['account.move.line']
            
            for payment_method in payment_methods:
                for session in sessions:
                    # Buscar asientos que contengan el nombre de la sesión en ref, name o narration
                    moves = self.env['account.move'].search([
                        ('journal_id', '=', payment_method.journal_id.id),
                        ('state', '=', 'posted'),
                        '|', '|',
                        ('ref', 'ilike', session.name),
                        ('name', 'ilike', session.name),
                        ('narration', 'ilike', session.name),
                    ])
                    
                    # De esos asientos, buscar las líneas en la cuenta 211040020000
                    for move in moves:
                        nc_lines = move.line_ids.filtered(
                            lambda l: l.account_id.id == nc_account.id
                        )
                        move_lines_to_reconcile |= nc_lines
            
            # Guardar los move_lines encontrados
            wizard.move_line_ids = [(6, 0, move_lines_to_reconcile.ids)]
            wizard.lines_with_move = len(move_lines_to_reconcile)
            
            # Construir HTML
            html = '<h4>📋 Detalle de Líneas Seleccionadas:</h4>'
            html += '<table style="width:100%; border-collapse: collapse;">'
            html += '<tr style="background-color: #f0f0f0; font-weight: bold;">'
            html += '<th style="padding: 8px; border: 1px solid #ddd;">Fecha</th>'
            html += '<th style="padding: 8px; border: 1px solid #ddd;">Sesión</th>'
            html += '<th style="padding: 8px; border: 1px solid #ddd;">Orden</th>'
            html += '<th style="padding: 8px; border: 1px solid #ddd;">Tipo</th>'
            html += '<th style="padding: 8px; border: 1px solid #ddd;">Debe</th>'
            html += '<th style="padding: 8px; border: 1px solid #ddd;">Haber</th>'
            html += '</tr>'
            
            for line in wizard.credit_note_line_ids:
                tipo_badge = '🔵 NC Original' if line.nc_type == 'nota_credito' else '🟡 Refacturación'
                html += '<tr>'
                html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % line.date
                html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % (line.session_name or '')
                html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % line.name
                html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % tipo_badge
                html += '<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">Q %.2f</td>' % line.debit
                html += '<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">Q %.2f</td>' % line.credit
                html += '</tr>'
            
            html += '<tr style="background-color: #e8f5e9; font-weight: bold;">'
            html += '<td colspan="4" style="padding: 8px; border: 1px solid #ddd; text-align: right;">TOTALES:</td>'
            html += '<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">Q %.2f</td>' % wizard.total_debit
            html += '<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">Q %.2f</td>' % wizard.total_credit
            html += '</tr>'
            html += '</table>'
            
            # Información de búsqueda
            html += '<div style="padding: 10px; background-color: #e3f2fd; border-left: 4px solid #2196f3; margin: 15px 0;">'
            html += '<strong>🔍 Búsqueda Realizada:</strong><br/>'
            html += '<strong>Métodos de Pago:</strong><br/>'
            for pm in payment_methods:
                html += '• %s (Diario: %s)<br/>' % (pm.name, pm.journal_id.name)
            html += '<strong>Sesiones:</strong><br/>'
            for session in sessions:
                html += '• %s<br/>' % session.name
            html += '</div>'
            
            # Mostrar asientos del DIARIO que se van a conciliar
            if move_lines_to_reconcile:
                html += '<hr style="margin: 20px 0;"/>'
                html += '<h4>🔗 Asientos del Diario del Método de Pago a Conciliar:</h4>'
                html += '<p><strong>Total de asientos encontrados:</strong> %s</p>' % len(move_lines_to_reconcile)
                html += '<table style="width:100%; border-collapse: collapse;">'
                html += '<tr style="background-color: #e3f2fd; font-weight: bold;">'
                html += '<th style="padding: 8px; border: 1px solid #ddd;">Asiento</th>'
                html += '<th style="padding: 8px; border: 1px solid #ddd;">Ref</th>'
                html += '<th style="padding: 8px; border: 1px solid #ddd;">Fecha</th>'
                html += '<th style="padding: 8px; border: 1px solid #ddd;">Diario</th>'
                html += '<th style="padding: 8px; border: 1px solid #ddd;">Cuenta</th>'
                html += '<th style="padding: 8px; border: 1px solid #ddd;">Debe</th>'
                html += '<th style="padding: 8px; border: 1px solid #ddd;">Haber</th>'
                html += '</tr>'
                
                for move_line in move_lines_to_reconcile:
                    html += '<tr>'
                    html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % move_line.move_id.name
                    html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % (move_line.move_id.ref or '')
                    html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % move_line.date
                    html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % move_line.move_id.journal_id.name
                    html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % move_line.account_id.code
                    html += '<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">Q %.2f</td>' % move_line.debit
                    html += '<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">Q %.2f</td>' % move_line.credit
                    html += '</tr>'
                
                total_move_debit = sum(move_lines_to_reconcile.mapped('debit'))
                total_move_credit = sum(move_lines_to_reconcile.mapped('credit'))
                
                html += '<tr style="background-color: #e8f5e9; font-weight: bold;">'
                html += '<td colspan="5" style="padding: 8px; border: 1px solid #ddd; text-align: right;">TOTAL ASIENTOS:</td>'
                html += '<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">Q %.2f</td>' % total_move_debit
                html += '<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">Q %.2f</td>' % total_move_credit
                html += '</tr>'
                html += '</table>'
            else:
                html += '<div style="padding: 10px; background-color: #ffebee; border: 1px solid #f44336; margin-top: 10px;">'
                html += '⚠️ No se encontraron asientos en los diarios de los métodos de pago que contengan las sesiones seleccionadas'
                html += '</div>'
            
            wizard.line_details = html
    
    def action_confirm_reconcile(self):
        """Ejecuta la conciliación de los asientos del diario del método de pago"""
        self.ensure_one()
        
        if not self.move_line_ids:
            raise UserError(_('No se encontraron asientos del diario del método de pago para conciliar.'))
        
        if len(self.move_line_ids) < 2:
            raise UserError(_('Se requieren al menos 2 asientos para conciliar. Solo se encontró %s asiento.') % len(self.move_line_ids))
        
        try:
            self.move_line_ids.reconcile()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('✅ Conciliación Exitosa'),
                    'message': _('Se conciliaron %s asientos del diario del método de pago correctamente.') % len(self.move_line_ids),
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
        except Exception as e:
            raise UserError(_('❌ Error al conciliar: %s') % str(e))