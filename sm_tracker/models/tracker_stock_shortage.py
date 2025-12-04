# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class TrackerStockShortage(models.Model):
    _name = 'tracker.stock.shortage'
    _description = 'Productos sin Abasto'
    _order = 'id'
    _check_company_auto = True  # No aplicar reglas automáticas de compañía

    project_id = fields.Many2one(
        'tracker.project',
        string='Proyecto',
        required=True,
        ondelete='cascade',
        check_company=False
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Producto',
        required=True,
        check_company=False
    )
    
    demand_qty = fields.Float(
        string='Demanda',
        help='Cantidad demandada por la orden'
    )
    
    available_qty = fields.Float(
        string='Cantidad',
        help='Cantidad disponible en inventario'
    )
    
    state = fields.Selection([
        ('sin_abasto', 'Sin Abasto'),
        ('con_abasto', 'Con Abasto'),
    ], string='Estado', default='sin_abasto', required=True)
    
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Bodega',
        check_company=False
    )
    
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Tienda',
        check_company=False
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company,
        required=False
    )