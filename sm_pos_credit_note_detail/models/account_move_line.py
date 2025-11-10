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
                # Método 1: Buscar si tiene una factura revertida asociada
                if line.move_id.reversed_entry_id:
                    origin = line.move_id.reversed_entry_id
                
                # Método 2: Buscar por referencia en el campo ref
                elif line.move_id.ref:
                    # Intentar buscar por nombre exacto
                    origin = self.env['account.move'].search([
                        ('name', '=', line.move_id.ref),
                        ('move_type', '=', 'out_invoice'),
                        ('state', '=', 'posted')
                    ], limit=1)
                    
                    # Si no se encuentra, intentar buscar por ref
                    if not origin:
                        origin = self.env['account.move'].search([
                            ('ref', '=', line.move_id.ref),
                            ('move_type', '=', 'out_invoice'),
                            ('state', '=', 'posted')
                        ], limit=1)
                
                # Método 3: Buscar en las órdenes de POS usando el asiento contable
                if not origin:
                    # Buscar orden POS que tenga este asiento contable
                    pos_order = self.env['pos.order'].search([
                        ('account_move', '=', line.move_id.id)
                    ], limit=1)
                    
                    if pos_order and pos_order.amount_total < 0:
                        # Es una nota de crédito de POS, buscar la orden original
                        # La referencia de refund típicamente contiene la referencia original
                        if pos_order.pos_reference:
                            # Remover "REFUND" y caracteres especiales para buscar la original
                            original_ref = pos_order.pos_reference.upper()
                            
                            # Intentar extraer la referencia original
                            if 'REFUND' in original_ref:
                                # Formato típico: "Order 12345-001-0001 REFUND"
                                original_ref = original_ref.replace('REFUND', '').strip()
                                original_ref = original_ref.replace('-', '').strip()
                            
                            # Buscar la orden original por referencia similar
                            origin_order = self.env['pos.order'].search([
                                ('pos_reference', 'ilike', original_ref),
                                ('amount_total', '>', 0),  # Asegurar que no sea otra NC
                                ('id', '!=', pos_order.id)
                            ], limit=1)
                            
                            if origin_order and origin_order.account_move:
                                origin = origin_order.account_move
            
            line.origin_invoice_id = origin.id if origin else False