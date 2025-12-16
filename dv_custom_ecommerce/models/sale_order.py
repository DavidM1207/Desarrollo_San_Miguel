from odoo import models, fields, api
from datetime import datetime, timedelta
from markupsafe import Markup


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    state = fields.Selection(
        selection_add=[('web_quote', 'Cotización Web')],
        ondelete={'web_quote': 'cascade'}
    )
    
    payment_method_id = fields.Many2one('payment.method', string='Método de pago', help='Método de pago seleccionado por el cliente')
    transfer_proof = fields.Binary(string='Comprobante de transferencia', help='Imagen del comprobante de pago')
    transfer_proof_filename = fields.Char(string='Nombre del archivo')
    
    def action_web_quote(self):
        """Mover orden a estado Cotización Web"""
        self.write({'state': 'web_quote'})
        return True
    
    def _can_be_confirmed(self):
        self.ensure_one()
        return self.state in {'draft', 'sent', 'web_quote'}

    @api.model
    def _cron_cancel_old_draft_website_orders(self):
        """Cancelar órdenes draft/web_quote del website cuando llegue a vencimiento"""
        expire = datetime.now()
        
        orders = self.search([
            ('state', 'in', ['draft', 'web_quote']),
            ('website_id', '!=', False),
            ('validity_date', '<', expire)
        ], limit=1000)
        
        if orders:
            orders.action_cancel()
            for order in orders:
                order.message_post(
                    body=Markup('<p>⛔ Esta orden fue cancelada automáticamente. Al ser una orden web sin actividad y en estado de cotización, alcanzó su fecha de vencimiento sin ser confirmada.</p>'),
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )
        
        return True
