# models/requisition_order.py
# -*- coding: utf-8 -*-
from odoo import api, fields, models


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
    
    requisition_state = fields.Selection(
        string='Estado Requisición',
        related='requisition_product_id.state',
        store=True,
        readonly=True,
        help='Estado de la requisición')
    
    # Campos computados SIN store=True
    date_diff_days = fields.Integer(
        string='Días de Diferencia',
        compute='_compute_date_diff',
        readonly=True,
        store=True,
        help='Diferencia en días entre fecha de creación y recepción')
    
    qty_received = fields.Float(
        string='Cantidad Recepcionada',
        compute='_compute_qty_received',
        readonly=True,
        help='Cantidad total recepcionada del producto (solo transito -> destino)')
    
    fill_rate_percentage = fields.Float(
        string='Fill Rate (%)',
        compute='_compute_fill_rate',
        readonly=True,
        help='Porcentaje de Fill Rate: (Cantidad Recepcionada / Cantidad Solicitada) * 100')
    
    picking_state = fields.Selection(
        string='Estado Movimiento',
        selection=[
            ('draft', 'Borrador'),
            ('waiting', 'Esperando'),
            ('confirmed', 'Confirmado'),
            ('assigned', 'Asignado'),
            ('partially_available', 'Parcialmente Disponible'),
            ('done', 'Hecho'),
            ('cancel', 'Cancelado')
        ],
        compute='_compute_picking_state',
        readonly=True,
        store=True,
        help='Estado del movimiento de stock (transito -> destino)')

    @api.depends('requisition_date', 'receive_date')
    def _compute_date_diff(self):
        """Calcula la diferencia en días entre fecha de creación y recepción"""
        for record in self:
            if record.requisition_date and record.receive_date:
                delta = record.receive_date - record.requisition_date
                record.date_diff_days = delta.days
            else:
                record.date_diff_days = 0

    @api.depends('product_id', 'requisition_product_id.name', 'requisition_product_id.destination_location_id')
    def _compute_qty_received(self):
        """Calcula la cantidad recepcionada desde stock.move - SOLO transito -> destino"""
        for record in self:
            if not record.requisition_product_id or not record.product_id:
                record.qty_received = 0.0
                continue
            
            # Obtener ubicaciones de tránsito y destino
            transit_location_id = record.requisition_product_id.company_id.internal_transit_location_id
            destination_location_id = record.requisition_product_id.destination_location_id
            
            if not transit_location_id or not destination_location_id:
                record.qty_received = 0.0
                continue
            
            # Buscar SOLO los movimientos de tránsito -> destino
            stock_moves = self.env['stock.move'].search([
                ('product_id', '=', record.product_id.id),
                ('state', '=', 'done'),
                ('picking_id.requisition_order', '=', record.requisition_product_id.name),
                ('location_id', '=', transit_location_id.id),
                ('location_dest_id', '=', destination_location_id.id)
            ])
            
            # Sumar las cantidades recepcionadas
            total_received = sum(stock_moves.mapped('quantity'))
            record.qty_received = total_received

    @api.depends('product_id', 'requisition_product_id.name', 'requisition_product_id.destination_location_id')
    def _compute_picking_state(self):
        """Obtiene el estado del movimiento de stock (transito -> destino)"""
        for record in self:
            if not record.requisition_product_id or not record.product_id:
                record.picking_state = False
                continue
            
            # Obtener ubicaciones de tránsito y destino
            transit_location_id = record.requisition_product_id.company_id.internal_transit_location_id
            destination_location_id = record.requisition_product_id.destination_location_id
            
            if not transit_location_id or not destination_location_id:
                record.picking_state = False
                continue
            
            # Buscar el movimiento de tránsito -> destino
            stock_move = self.env['stock.move'].search([
                ('product_id', '=', record.product_id.id),
                ('picking_id.requisition_order', '=', record.requisition_product_id.name),
                ('location_id', '=', transit_location_id.id),
                ('location_dest_id', '=', destination_location_id.id)
            ], limit=1, order='id desc')
            
            record.picking_state = stock_move.state if stock_move else False

    @api.depends('quantity', 'qty_received')
    def _compute_fill_rate(self):
        """Calcula el porcentaje de Fill Rate"""
        for record in self:
            if record.quantity and record.quantity > 0:
                record.fill_rate_percentage = (record.qty_received / record.quantity) * 100
            else:
                record.fill_rate_percentage = 0.0