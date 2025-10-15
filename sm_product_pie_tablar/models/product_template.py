# -*- coding: utf-8 -*-
from odoo import fields, models

class ProductTemplate(models.Model):
    _inherit = "product.template"

    pie_tablar = fields.Float(
        string="Pie tablar (PT)",
        help="Medida o factor en pies tablares (board feet) asociada al producto.",
        digits=(16, 4),
    )
