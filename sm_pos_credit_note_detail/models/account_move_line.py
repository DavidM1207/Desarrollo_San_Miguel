from odoo import models, fields, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_credit_note_line = fields.Boolean(
        string='Es Nota de Crédito',
        compute='_compute_is_credit_note_line',
        store=True,
        help='Indica si este apunte pertenece a una nota de crédito por aplicar'
    )
    
    credit_note_reference = fields.Char(
        string='Referencia NC',
        compute='_compute_credit_note_reference',
        store=True,
        help='Referencia de la nota de crédito'
    )
    
    credit_note_date = fields.Date(
        string='Fecha NC',
        related='move_id.date',
        store=True,
        help='Fecha de la nota de crédito'
    )
    
    credit_note_partner_id = fields.Many2one(
        'res.partner',
        string='Cliente NC',
        related='partner_id',
        store=True
    )
    
    @api.depends('account_id', 'account_id.code')
    def _compute_is_credit_note_line(self):
        for line in self:
            # Verifica si la cuenta es la de notas de crédito por aplicar
            line.is_credit_note_line = line.account_id.code == '211040020000'
    
    @api.depends('move_id.name', 'move_id.ref', 'name')
    def _compute_credit_note_reference(self):
        for line in self:
            if line.is_credit_note_line:
                line.credit_note_reference = line.move_id.ref or line.move_id.name or line.name
            else:
                line.credit_note_reference = False