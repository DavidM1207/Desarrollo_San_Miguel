from odoo import models, fields


class PaymentMethod(models.Model):
    _inherit = 'payment.method'
    
    transfer_image = fields.Image(string='Imagen de transferencia', help='Imagen con datos de cuenta bancaria para transferencias')
