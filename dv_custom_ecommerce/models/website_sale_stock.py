from odoo import models, fields

class Website(models.Model):
    _inherit = 'website'

    website_warehouses_ids = fields.Many2many('stock.warehouse', string='Warehouses for Stock Display', help='Select warehouses to include in total stock calculation for website display')
