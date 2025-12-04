# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class TrackerStockShortage(models.Model):
    _name = 'tracker.stock.shortage'
    _description = 'Productos sin Abasto'
    _order = 'id'

    project_id = fields.Many2one(
        'tracker.project',
        string='Proyecto',
        required=True,
        ondelete='cascade'
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Producto',
        required=True
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
        string='Bodega'
    )
    
    analytic_account_id = fields.Many2one(
        related='project_id.analytic_account_id',
        string='Tienda',
        store=True,
        readonly=True
    )