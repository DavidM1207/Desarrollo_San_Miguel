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
        
        # Validar que se hayan seleccionado al menos 2 líneas
        if len(self) < 2:
            raise UserError(_('Debe seleccionar al menos 2 líneas para conciliar.'))
        
        # Calcular totales
        total_debit = sum(self.mapped('debit'))
        total_credit = sum(self.mapped('credit'))
        diferencia = abs(total_debit - total_credit)
        
        # Crear wizard pasándole las líneas seleccionadas
        wizard = self.env['reconcile.confirmation.wizard'].create({
            'line_count': len(self),
            'total_debit': total_debit,
            'total_credit': total_credit,
            'difference': diferencia,
            'currency_id': self[0].currency_id.id,
            'credit_note_line_ids': [(6, 0, self.ids)],
        })
        
        return {
            'name': _('¿Confirmar Conciliación?'),
            'type': 'ir.actions.act_window',
            'res_model': 'reconcile.confirmation.wizard',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
        }