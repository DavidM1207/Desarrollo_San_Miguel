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
            
            # Buscar el MÉTODO DE PAGO con "devolución" o "nota"
            nc_payment_method = self.env['pos.payment.method'].search([
                '|', '|',
                ('name', 'ilike', 'devolución'),
                ('name', 'ilike', 'devolucion'),
                ('name', 'ilike', 'nota'),
            ], limit=1)
            
            if not nc_payment_method:
                wizard.line_details = '<p style="color: red;">⚠️ No se encontró el método de pago Devolución/Nota</p>'
                continue
            
            if not nc_payment_method.journal_id:
                wizard.line_details = '<p style="color: red;">⚠️ El método de pago %s no tiene diario configurado</p>' % nc_payment_method.name
                continue
            
            # Obtener las sesiones de las líneas seleccionadas
            sessions = wizard.credit_note_line_ids.mapped('pos_order_id').mapped('session_id').filtered(lambda s: s)
            
            if not sessions:
                wizard.line_details = '<p style="color: red;">⚠️ No se encontraron sesiones en las líneas seleccionadas</p>'
                continue
            
            # Buscar asientos en el DIARIO del método de pago para esas sesiones
            move_lines_to_reconcile = self.env['account.move.line']
            
            for session in sessions:
                # Buscar asientos en el diario del método de pago de esta sesión
                moves = self.env['account.move'].search([
                    ('journal_id', '=', nc_payment_method.journal_id.id),
                    ('date', '>=', session.start_at.date() if session.start_at else fields.Date.today()),
                    ('date', '<=', session.stop_at.date() if session.stop_at else fields.Date.today()),
                    ('state', '=', 'posted'),
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
            
            # Mostrar asientos del DIARIO que se van a conciliar
            if move_lines_to_reconcile:
                html += '<hr style="margin: 20px 0;"/>'
                html += '<h4>🔗 Asientos del Diario del Método de Pago a Conciliar:</h4>'
                html += '<p><strong>Método de Pago:</strong> %s</p>' % nc_payment_method.name
                html += '<p><strong>Diario:</strong> %s</p>' % nc_payment_method.journal_id.name
                html += '<p><strong>Total de asientos encontrados:</strong> %s</p>' % len(move_lines_to_reconcile)
                html += '<table style="width:100%; border-collapse: collapse;">'
                html += '<tr style="background-color: #e3f2fd; font-weight: bold;">'
                html += '<th style="padding: 8px; border: 1px solid #ddd;">Asiento</th>'
                html += '<th style="padding: 8px; border: 1px solid #ddd;">Fecha</th>'
                html += '<th style="padding: 8px; border: 1px solid #ddd;">Cuenta</th>'
                html += '<th style="padding: 8px; border: 1px solid #ddd;">Debe</th>'
                html += '<th style="padding: 8px; border: 1px solid #ddd;">Haber</th>'
                html += '</tr>'
                
                for move_line in move_lines_to_reconcile:
                    html += '<tr>'
                    html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % move_line.move_id.name
                    html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % move_line.date
                    html += '<td style="padding: 8px; border: 1px solid #ddd;">%s - %s</td>' % (move_line.account_id.code, move_line.account_id.name)
                    html += '<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">Q %.2f</td>' % move_line.debit
                    html += '<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">Q %.2f</td>' % move_line.credit
                    html += '</tr>'
                
                total_move_debit = sum(move_lines_to_reconcile.mapped('debit'))
                total_move_credit = sum(move_lines_to_reconcile.mapped('credit'))
                
                html += '<tr style="background-color: #e8f5e9; font-weight: bold;">'
                html += '<td colspan="3" style="padding: 8px; border: 1px solid #ddd; text-align: right;">TOTAL ASIENTOS:</td>'
                html += '<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">Q %.2f</td>' % total_move_debit
                html += '<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">Q %.2f</td>' % total_move_credit
                html += '</tr>'
                html += '</table>'
            else:
                html += '<div style="padding: 10px; background-color: #ffebee; border: 1px solid #f44336; margin-top: 10px;">'
                html += '⚠️ No se encontraron asientos en el diario <strong>%s</strong> del método de pago <strong>%s</strong> para las fechas de las sesiones seleccionadas' % (nc_payment_method.journal_id.name, nc_payment_method.name)
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