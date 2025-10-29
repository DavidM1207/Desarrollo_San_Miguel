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
        """Abre wizard para conciliar usando los move_line_id ya guardados"""
        
        if len(self) < 2:
            raise UserError(_('Debe seleccionar al menos 2 líneas para conciliar.'))
        
        # Obtener los move_line_id de las líneas seleccionadas
        move_lines = self.mapped('move_line_id').filtered(lambda l: l and not l.reconciled)
        
        if not move_lines:
            raise UserError(_('Las líneas seleccionadas no tienen apuntes contables o ya están conciliadas.'))
        
        if len(move_lines) < 2:
            raise UserError(_('Solo hay %s apunte sin conciliar. Se necesitan al menos 2 para conciliar.') % len(move_lines))
        
        # Calcular totales
        total_debit = sum(self.mapped('debit'))
        total_credit = sum(self.mapped('credit'))
        
        # Construir HTML con detalle
        html = '<h4>📋 Líneas Seleccionadas:</h4>'
        html += '<table style="width:100%; border-collapse: collapse; margin-bottom: 20px;">'
        html += '<tr style="background-color: #f0f0f0; font-weight: bold;">'
        html += '<th style="padding: 8px; border: 1px solid #ddd;">Fecha</th>'
        html += '<th style="padding: 8px; border: 1px solid #ddd;">Sesión</th>'
        html += '<th style="padding: 8px; border: 1px solid #ddd;">Orden</th>'
        html += '<th style="padding: 8px; border: 1px solid #ddd;">Tipo</th>'
        html += '<th style="padding: 8px; border: 1px solid #ddd;">Debe</th>'
        html += '<th style="padding: 8px; border: 1px solid #ddd;">Haber</th>'
        html += '</tr>'
        
        for line in self:
            tipo = '🔵 NC' if line.nc_type == 'nota_credito' else '🟡 Refact'
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
        
        # Asientos a conciliar
        html += '<hr/><h4>🔗 Apuntes Contables a Conciliar:</h4>'
        html += '<table style="width:100%; border-collapse: collapse;">'
        html += '<tr style="background-color: #e3f2fd; font-weight: bold;">'
        html += '<th style="padding: 8px; border: 1px solid #ddd;">Asiento</th>'
        html += '<th style="padding: 8px; border: 1px solid #ddd;">Diario</th>'
        html += '<th style="padding: 8px; border: 1px solid #ddd;">Fecha</th>'
        html += '<th style="padding: 8px; border: 1px solid #ddd;">Cuenta</th>'
        html += '<th style="padding: 8px; border: 1px solid #ddd;">Debe</th>'
        html += '<th style="padding: 8px; border: 1px solid #ddd;">Haber</th>'
        html += '</tr>'
        
        move_debit = 0
        move_credit = 0
        for ml in move_lines:
            html += '<tr>'
            html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % ml.move_id.name
            html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % ml.move_id.journal_id.name
            html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % ml.date
            html += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % ml.account_id.code
            html += '<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">Q %.2f</td>' % ml.debit
            html += '<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">Q %.2f</td>' % ml.credit
            html += '</tr>'
            move_debit += ml.debit
            move_credit += ml.credit
        
        html += '<tr style="background-color: #4caf50; color: white; font-weight: bold;">'
        html += '<td colspan="4" style="padding: 10px; border: 2px solid #4caf50; text-align: right;">TOTAL ASIENTOS:</td>'
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
            'move_line_ids': [(6, 0, move_lines.ids)],
        })
        
        return {
            'name': _('¿Confirmar Conciliación?'),
            'type': 'ir.actions.act_window',
            'res_model': 'reconcile.confirmation.wizard',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
        }