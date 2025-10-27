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
        """Construir el detalle mostrando el asiento del diario del método de pago"""
        for wizard in self:
            if not wizard.credit_note_line_ids:
                wizard.line_details = '<p>No hay líneas seleccionadas</p>'
                continue
            
            # Buscar la cuenta 211040020000
            nc_account = self.env['account.account'].search([('code', '=', '211040020000')], limit=1)
            
            # Buscar el método de pago de Nota de Crédito
            nc_payment_method = self.env['pos.payment.method'].search([
                '|', '|',
                ('name', 'ilike', 'crédit'),
                ('name', 'ilike', 'credit'),
                ('name', 'ilike', 'nota'),
            ], limit=1)
            
            if not nc_payment_method:
                wizard.line_details = '<p style="color: red;">⚠️ No se encontró el método de pago de Nota de Crédito</p>'
                continue
            
            # Obtener las sesiones de las líneas seleccionadas
            sessions = self.env['pos.session'].browse(
                wizard.credit_note_line_ids.mapped('pos_order_id').mapped('session_id').ids
            ).filtered(lambda s: s)
            
            # Buscar los asientos del DIARIO del método de pago
            journal_moves = []
            for session in sessions:
                # Buscar el diario del método de pago
                if nc_payment_method.journal_id:
                    # Buscar asientos en ese diario de la sesión
                    moves = self.env['account.move'].search([
                        ('journal_id', '=', nc_payment_method.journal_id.id),
                        ('date', '>=', session.start_at.date() if session.start_at else fields.Date.today()),
                        ('date', '<=', session.stop_at.date() if session.stop_at else fields.Date.today()),
                        ('state', '=', 'posted'),
                    ])
                    
                    for move in moves:
                        # Buscar líneas en la cuenta 211040020000
                        move_lines = move.line_ids.filtered(
                            lambda l: l.account_id.id == nc_account.id
                        )
                        if move_lines:
                            journal_moves.extend(move_lines.ids)
            
            # Guardar los move_lines encontrados
            wizard.move_line_ids = [(6, 0, journal_moves)]
            
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
            
            # Mostrar asientos del diario que se van a conciliar
            if wizard.move_line_ids:
                html += '<hr style="margin: 20px 0;"/>'
                html += '<h4>🔗 Asientos del Diario a Conciliar:</h4>'
                html += '<p><strong>Diario:</strong> %s</p>' % nc_payment_method.journal_id.name
                html += '<table style="width:100%; border-collapse: collapse;">'
                html += '<tr style="background-color: #e3f2fd; font-weight: bold;">'
                html += '<th style="padding: 8px; border: 1px solid #ddd;">Asiento</th>'
                html += '<th style="padding: 8px; border: 1px solid #ddd;">Fecha</th>'
                html += '<th style="padding: 8px; border: 1px solid #ddd;">Cuenta</th>'
                html += '<th style="padding: 8px; border: 1px solid #ddd;">Debe</th>'
                html += '<th style="padding: 8px; border: 1px solid #ddd;">Haber</th>'
                html += '</tr>'
                
                for move_line in wizard.move_line_ids:
                    html += '<tr>'
                    html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % move_line.move_id.name
                    html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % move_line.date
                    html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % move_line.account_id.code
                    html += '<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">Q %.2f</td>' % move_line.debit
                    html += '<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">Q %.2f</td>' % move_line.credit
                    html += '</tr>'
                
                html += '</table>'
            else:
                html += '<div style="padding: 10px; background-color: #ffebee; border: 1px solid #f44336; margin-top: 10px;">'
                html += '⚠️ No se encontraron asientos del diario del método de pago para conciliar'
                html += '</div>'
            
            wizard.line_details = html
    
    def action_confirm_reconcile(self):
        """Ejecuta la conciliación de los asientos del diario"""
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
                    'message': _('Se conciliaron %s asientos del diario correctamente.') % len(self.move_line_ids),
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
        except Exception as e:
            raise UserError(_('❌ Error al conciliar: %s') % str(e))