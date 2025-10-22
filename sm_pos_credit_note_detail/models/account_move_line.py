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
    
    origin_invoice_id = fields.Many2one(
        'account.move',
        string='Factura Origen',
        compute='_compute_origin_invoice',
        store=True,
        help='Factura que originó esta nota de crédito'
    )
    
    origin_invoice_name = fields.Char(
        string='Número Factura Origen',
        related='origin_invoice_id.name',
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
    
    @api.depends('move_id', 'move_id.reversed_entry_id', 'move_id.ref')
    def _compute_origin_invoice(self):
        for line in self:
            origin = False
            if line.is_credit_note_line and line.move_id:
                # Buscar si tiene una factura revertida asociada
                if line.move_id.reversed_entry_id:
                    origin = line.move_id.reversed_entry_id
                # Buscar por referencia en el campo ref
                elif line.move_id.ref:
                    origin = self.env['account.move'].search([
                        ('name', '=', line.move_id.ref),
                        ('move_type', '=', 'out_invoice'),
                        ('state', '=', 'posted')
                    ], limit=1)
                # Buscar en las órdenes de POS
                elif line.move_id.pos_session_id:
                    pos_order = self.env['pos.order'].search([
                        ('account_move', '=', line.move_id.id)
                    ], limit=1)
                    if pos_order and pos_order.amount_total < 0:
                        # Es una nota de crédito, buscar la orden original
                        original_ref = pos_order.pos_reference.replace('REFUND', '').strip()
                        origin_order = self.env['pos.order'].search([
                            ('pos_reference', '=', original_ref)
                        ], limit=1)
                        if origin_order and origin_order.account_move:
                            origin = origin_order.account_move
            
            line.origin_invoice_id = origin.id if origin else False