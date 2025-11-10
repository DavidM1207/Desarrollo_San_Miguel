from odoo import models, fields, api


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'
    
    is_from_credit_note = fields.Boolean(
        string='De Nota de Crédito',
        related='order_id.is_credit_note',
        store=True
    )