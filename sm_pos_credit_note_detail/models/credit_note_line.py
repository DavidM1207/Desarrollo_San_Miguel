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
    
     