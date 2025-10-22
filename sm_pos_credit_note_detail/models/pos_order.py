from odoo import models, fields, api


class PosOrder(models.Model):
    _inherit = 'pos.order'

    credit_note_detail_ids = fields.One2many(
        'credit.note.detail',
        'pos_order_id',
        string='Detalles de Nota de Crédito'
    )
    
    def _create_credit_note_detail(self):
        """Crea el detalle de nota de crédito después de crear el asiento contable"""
        self.ensure_one()
        CreditNoteDetail = self.env['credit.note.detail']
        
        # Solo procesar si es una nota de crédito (monto negativo)
        if self.amount_total >= 0:
            return
        
        # Buscar si ya existe un detalle para esta orden
        existing_detail = CreditNoteDetail.search([
            ('pos_order_id', '=', self.id)
        ], limit=1)
        
        if existing_detail:
            return
        
        # Buscar el apunte contable de nota de crédito relacionado
        if self.account_move:
            credit_line = self.account_move.line_ids.filtered(
                lambda l: l.account_id.code == '211040020000' and l.credit > 0
            )
            
            if credit_line:
                # Obtener la factura origen si existe
                origin_invoice = None
                if self.name and 'REFUND' in self.name.upper():
                    # Buscar la factura original en las referencias
                    origin_ref = self.account_move.ref or self.pos_reference
                    if origin_ref:
                        origin_invoice = self.env['account.move'].search([
                            '|',
                            ('name', 'ilike', origin_ref),
                            ('ref', 'ilike', origin_ref),
                            ('move_type', '=', 'out_invoice')
                        ], limit=1)
                
                # Crear el detalle
                CreditNoteDetail.create({
                    'reference': self.pos_reference or self.name,
                    'date': self.date_order.date() if self.date_order else fields.Date.today(),
                    'partner_id': self.partner_id.id if self.partner_id else self.env.company.partner_id.id,
                    'account_move_line_id': credit_line[0].id,
                    'pos_order_id': self.id,
                    'origin_invoice_id': origin_invoice.id if origin_invoice else False,
                    'notes': f'Nota de crédito generada desde POS - Sesión: {self.session_id.name if self.session_id else "N/A"}'
                })


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _create_account_move(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        """Override para crear detalles de notas de crédito después de crear el asiento"""
        move = super()._create_account_move(balancing_account, amount_to_balance, bank_payment_method_diffs)
        
        # Procesar todas las órdenes de esta sesión que sean notas de crédito
        credit_note_orders = self.order_ids.filtered(lambda o: o.amount_total < 0)
        for order in credit_note_orders:
            order._create_credit_note_detail()
        
        return move
    
    def action_pos_session_closing_control(self):
        """Override para asegurar que se crean los detalles al cerrar sesión"""
        res = super().action_pos_session_closing_control()
        
        # Crear detalles para notas de crédito de esta sesión
        credit_note_orders = self.order_ids.filtered(lambda o: o.amount_total < 0)
        for order in credit_note_orders:
            if order.account_move:
                order._create_credit_note_detail()
        
        return res