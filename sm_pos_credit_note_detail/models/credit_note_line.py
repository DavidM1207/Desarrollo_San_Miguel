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
        """Abre wizard de confirmación para conciliar"""
        move_lines = self.mapped('move_line_id').filtered(lambda l: l)
        
        if not move_lines:
            raise UserError(_('No hay líneas válidas seleccionadas.'))
        
        if len(move_lines) < 2:
            raise UserError(_('Debe seleccionar al menos 2 líneas para conciliar.'))
        
        # Calcular totales
        total_debit = sum(move_lines.mapped('debit'))
        total_credit = sum(move_lines.mapped('credit'))
        
        # Construir detalle HTML
        html_details = '<table style="width:100%; border-collapse: collapse;">'
        html_details += '<tr style="background-color: #f0f0f0; font-weight: bold;">'
        html_details += '<th style="padding: 8px; border: 1px solid #ddd;">Fecha</th>'
        html_details += '<th style="padding: 8px; border: 1px solid #ddd;">Sesión</th>'
        html_details += '<th style="padding: 8px; border: 1px solid #ddd;">Orden</th>'
        html_details += '<th style="padding: 8px; border: 1px solid #ddd;">Debe</th>'
        html_details += '<th style="padding: 8px; border: 1px solid #ddd;">Haber</th>'
        html_details += '</tr>'
        
        for line in self:
            if line.move_line_id in move_lines:
                html_details += '<tr>'
                html_details += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % line.date
                html_details += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % (line.session_name or '')
                html_details += '<td style="padding: 8px; border: 1px solid #ddd;">%s</td>' % line.name
                html_details += '<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">%.2f</td>' % line.debit
                html_details += '<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">%.2f</td>' % line.credit
                html_details += '</tr>'
        
        html_details += '<tr style="background-color: #e8f5e9; font-weight: bold;">'
        html_details += '<td colspan="3" style="padding: 8px; border: 1px solid #ddd; text-align: right;">TOTALES:</td>'
        html_details += '<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">%.2f</td>' % total_debit
        html_details += '<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">%.2f</td>' % total_credit
        html_details += '</tr>'
        html_details += '</table>'
        
        # Crear wizard
        wizard = self.env['reconcile.confirmation.wizard'].create({
            'line_count': len(move_lines),
            'total_debit': total_debit,
            'total_credit': total_credit,
            'currency_id': self[0].currency_id.id,
            'line_details': html_details,
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