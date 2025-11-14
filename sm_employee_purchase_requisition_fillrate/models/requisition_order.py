# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import timedelta


class RequisitionOrderFillRate(models.Model):
    """Herencia del modelo requisition.order para agregar campos de Fill Rate"""
    _inherit = 'requisition.order'

    # Campos relacionados de la requisición padre
    requisition_name = fields.Char(
        string='Requisición',
        related='requisition_product_id.name',
        store=True,
        readonly=True,
        help='Nombre/Referencia de la requisición')
    
    requisition_date = fields.Date(
        string='Fecha de Creación',
        related='requisition_product_id.requisition_date',
        store=True,
        readonly=True,
        help='Fecha de creación de la requisición')
    
    receive_date = fields.Date(
        string='Fecha de Recepción',
        related='requisition_product_id.receive_date',
        store=True,
        readonly=True,
        help='Fecha de recepción del producto')
    
    # Campos computados
    date_diff_days = fields.Integer(
        string='Días de Diferencia',
        compute='_compute_date_diff',
        store=True,
        readonly=True,
        help='Diferencia en días entre fecha de creación y recepción')
    
    qty_received = fields.Float(
        string='Cantidad Recepcionada',
        compute='_compute_qty_received',
        store=True,
        readonly=True,
        help='Cantidad total recepcionada del producto')
    
    fill_rate_percentage = fields.Float(
        string='Fill Rate (%)',
        compute='_compute_fill_rate',
        store=True,
        readonly=True,
        help='Porcentaje de Fill Rate: (Cantidad Recepcionada / Cantidad Solicitada) * 100')

    @api.depends('requisition_date', 'receive_date')
    def _compute_date_diff(self):
        """Calcula la diferencia en días entre fecha de creación y recepción"""
        for record in self:
            if record.requisition_date and record.receive_date:
                delta = record.receive_date - record.requisition_date
                record.date_diff_days = delta.days
            else:
                record.date_diff_days = 0

    @api.depends('product_id', 'requisition_product_id.name')
    def _compute_qty_received(self):
        """Calcula la cantidad recepcionada desde stock.move"""
        for record in self:
            if not record.requisition_product_id or not record.product_id:
                record.qty_received = 0.0
                continue
            
            # Buscar todos los movimientos de stock relacionados con esta requisición
            stock_moves = self.env['stock.move'].search([
                ('product_id', '=', record.product_id.id),
                ('state', '=', 'done'),
                ('picking_id.requisition_order', '=', record.requisition_product_id.name)
            ])
            
            # Sumar las cantidades recepcionadas
            total_received = sum(stock_moves.mapped('quantity'))
            record.qty_received = total_received

    @api.depends('quantity', 'qty_received')
    def _compute_fill_rate(self):
        """Calcula el porcentaje de Fill Rate"""
        for record in self:
            if record.quantity and record.quantity > 0:
                record.fill_rate_percentage = (record.qty_received / record.quantity) * 100
            else:
                record.fill_rate_percentage = 0.0
