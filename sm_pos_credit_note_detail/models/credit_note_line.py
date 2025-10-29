from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CreditNoteLine(models.Model):
    _name = 'credit.note.line'
    _description = 'Línea de Nota de Crédito'
    _order = 'date desc, id desc'
    
    date = fields.Date(string='Fecha', required=True, index=True)
    name = fields.Char(string='Orden', required=True)
    account_id = fields.Many2one('account.account', string='Cuenta', required=True)
    session_name = fields.Char(string='Sesión POS', index=True)
    nc_type = fields.Selection([
        ('nota_credito', 'Nota de Crédito'),
        ('refacturacion', 'Refacturación'),
    ], string='Tipo', required=True, index=True)
    description = fields.Text(string='Detalle NC')
    debit = fields.Monetary(string='Debe', currency_field='currency_id')
    credit = fields.Monetary(string='Haber', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Moneda')
    vendedor = fields.Char(string='Vendedor')
    move_line_id = fields.Many2one('account.move.line', string='Apunte Contable')
    pos_order_id = fields.Many2one('pos.order', string='Orden POS')
    reconciled = fields.Boolean(string='Conciliado', related='move_line_id.reconciled', store=True)
    
    def action_reconcile_lines(self):
        """Busca los asientos del diario del método de pago y los concilia"""
        
        if len(self) < 2:
            raise UserError(_('Debe seleccionar al menos 2 líneas para conciliar.'))
        
        # Buscar la cuenta 211040020000
        nc_account = self.env['account.account'].search([('code', '=', '211040020000')], limit=1)
        if not nc_account:
            raise UserError(_('No se encontró la cuenta 211040020000'))
        
        # Obtener las órdenes y sesiones
        orders = self.mapped('pos_order_id').filtered(lambda o: o)
        sessions = orders.mapped('session_id').filtered(lambda s: s)
        
        if not sessions:
            raise UserError(_('No se encontraron sesiones en las líneas seleccionadas'))
        
        # Buscar todos los métodos de pago "Devolución/Nota" de las órdenes
        payment_methods = self.env['pos.payment.method']
        for order in orders:
            payments = order.payment_ids.filtered(
                lambda p: 'devolución' in (p.payment_method_id.name or '').lower() or 
                         'devolucion' in (p.payment_method_id.name or '').lower() or
                         'nota' in (p.payment_method_id.name or '').lower()
            )
            payment_methods |= payments.mapped('payment_method_id')
        
        if not payment_methods:
            raise UserError(_('No se encontraron métodos de pago Devolución/Nota en las órdenes'))
        
        payment_methods_with_journal = payment_methods.filtered(lambda m: m.journal_id)
        if not payment_methods_with_journal:
            raise UserError(_('Los métodos de pago no tienen diario configurado'))
        
        # Buscar asientos en los diarios de los métodos de pago
        move_lines_to_reconcile = self.env['account.move.line']
        
        for payment_method in payment_methods_with_journal:
            for session in sessions:
                # Buscar por nombre de sesión en ref o name
                moves = self.env['account.move'].search([
                    ('journal_id', '=', payment_method.journal_id.id),
                    ('state', '=', 'posted'),
                    '|',
                    ('ref', 'ilike', session.name),
                    ('name', 'ilike', session.name),
                ])
                
                # Si no encuentra por nombre, buscar por fecha
                if not moves and session.stop_at:
                    moves = self.env['account.move'].search([
                        ('journal_id', '=', payment_method.journal_id.id),
                        ('state', '=', 'posted'),
                        ('date', '=', session.stop_at.date()),
                    ])
                
                # De esos asientos, buscar líneas en cuenta 211040020000 NO conciliadas
                for move in moves:
                    nc_lines = move.line_ids.filtered(
                        lambda l: l.account_id.id == nc_account.id and not l.reconciled
                    )
                    move_lines_to_reconcile |= nc_lines
        
        if not move_lines_to_reconcile:
            raise UserError(_('No se encontraron asientos contables sin conciliar para las sesiones seleccionadas'))
        
        if len(move_lines_to_reconcile) < 2:
            raise UserError(_('Solo se encontró 1 asiento. Se necesitan al menos 2 para conciliar.'))
        
        # Calcular totales
        total_debit = sum(self.mapped('debit'))
        total_credit = sum(self.mapped('credit'))
        
        # Construir HTML
        html = '<h4>Lineas Seleccionadas:</h4>'
        html += '<table style="width:100%; border-collapse: collapse; margin-bottom: 20px;">'
        html += '<tr style="background-color: #f0f0f0; font-weight: bold;">'
        html += '<th style="padding: 8px; border: 1px solid #ddd;">Fecha</th>'
        html += '<th style="padding: 8px; border: 1px solid #ddd;">Sesion</th>'
        html += '<th style="padding: 8px; border: 1px solid #ddd;">Orden</th>'
        html += '<th style="padding: 8px; border: 1px solid #ddd;">Tipo</th>'
        html += '<th style="padding: 8px; border: 1px solid #ddd;">Debe</th>'
        html += '<th style="padding: 8px; border: 1px solid #ddd;">Haber</th>'
        html += '</tr>'
        
        for line in self:
            tipo = 'NC' if line.nc_type == 'nota_credito' else 'Refacturacion'
            html += '<tr>'
            html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % line.date
            html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % (line.session_name or '')
            html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % line.name
            html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % tipo
            html += '<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">Q %.2f</td>' % line.debit
            html += '<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">Q %.2f</td>' % line.credit
            html += '</tr>'
        
        html += '<tr style="background-color: #e8f5e9; font-weight: bold;">'
        html += '<td colspan="4" style="padding: 8px; border: 1px solid #ddd; text-align: right;">TOTAL:</td>'
        html += '<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">Q %.2f</td>' % total_debit
        html += '<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">Q %.2f</td>' % total_credit
        html += '</tr>'
        html += '</table>'
        
        # Asientos encontrados
        html += '<hr/><h4>Asientos Contables a Conciliar:</h4>'
        html += '<p><strong>Sesiones:</strong> %s</p>' % ', '.join(sessions.mapped('name'))
        html += '<p><strong>Metodos de Pago:</strong> %s</p>' % ', '.join(payment_methods_with_journal.mapped('name'))
        html += '<table style="width:100%; border-collapse: collapse;">'
        html += '<tr style="background-color: #e3f2fd; font-weight: bold;">'
        html += '<th style="padding: 8px; border: 1px solid #ddd;">Asiento</th>'
        html += '<th style="padding: 8px; border: 1px solid #ddd;">Diario</th>'
        html += '<th style="padding: 8px; border: 1px solid #ddd;">Ref</th>'
        html += '<th style="padding: 8px; border: 1px solid #ddd;">Fecha</th>'
        html += '<th style="padding: 8px; border: 1px solid #ddd;">Cuenta</th>'
        html += '<th style="padding: 8px; border: 1px solid #ddd;">Debe</th>'
        html += '<th style="padding: 8px; border: 1px solid #ddd;">Haber</th>'
        html += '</tr>'
        
        move_debit = 0
        move_credit = 0
        for ml in move_lines_to_reconcile:
            html += '<tr>'
            html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % ml.move_id.name
            html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % ml.move_id.journal_id.name
            html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % (ml.move_id.ref or '-')
            html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % ml.date
            html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % ml.account_id.code
            html += '<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">Q %.2f</td>' % ml.debit
            html += '<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">Q %.2f</td>' % ml.credit
            html += '</tr>'
            move_debit += ml.debit
            move_credit += ml.credit
        
        html += '<tr style="background-color: #4caf50; color: white; font-weight: bold;">'
        html += '<td colspan="5" style="padding: 10px; border: 2px solid #4caf50; text-align: right;">TOTAL ASIENTOS:</td>'
        html += '<td style="padding: 10px; border: 2px solid #4caf50; text-align: right;">Q %.2f</td>' % move_debit
        html += '<td style="padding: 10px; border: 2px solid #4caf50; text-align: right;">Q %.2f</td>' % move_credit
        html += '</tr>'
        html += '</table>'
        
        # Crear wizard
        wizard = self.env['reconcile.confirmation.wizard'].create({
            'line_count': len(self),
            'total_debit': total_debit,
            'total_credit': total_credit,
            'currency_id': self[0].currency_id.id,
            'line_details': html,
            'move_line_ids': [(6, 0, move_lines_to_reconcile.ids)],
        })
        
        return {
            'name': _('Confirmar Conciliacion'),
            'type': 'ir.actions.act_window',
            'res_model': 'reconcile.confirmation.wizard',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
        }