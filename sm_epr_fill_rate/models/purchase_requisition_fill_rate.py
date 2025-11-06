# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PurchaseRequisitionFillRate(models.Model):
    _name = 'purchase.requisition.fill.rate'
    _description = 'Reporte Fill Rate de Requisiciones'
    _order = 'create_date desc, requisition_id, product_id'

    requisition_id = fields.Many2one(
        'purchase.requisition',
        string='Requisición',
        required=True,
        ondelete='cascade',
        index=True
    )
    requisition_name = fields.Char(
        string='Número Requisición',
        related='requisition_id.name',
        store=True
    )
    create_date = fields.Datetime(
        string='Fecha Creación',
        related='requisition_id.create_date',
        store=True
    )
    product_id = fields.Many2one(
        'product.product',
        string='Producto',
        required=True,
        ondelete='cascade',
        index=True
    )
    product_name = fields.Char(
        string='Nombre Producto',
        related='product_id.display_name',
        store=True
    )
    demanda = fields.Float(
        string='Demanda (Unidades Solicitadas)',
        digits='Product Unit of Measure',
        required=True
    )
    cantidad_entregada = fields.Float(
        string='Cantidad (Unidades Entregadas)',
        digits='Product Unit of Measure',
        compute='_compute_cantidad_entregada',
        store=True
    )
    fill_rate = fields.Float(
        string='Fill Rate (%)',
        compute='_compute_fill_rate',
        store=True,
        digits=(16, 2)
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unidad de Medida',
        related='product_id.uom_id',
        store=True
    )

    _sql_constraints = [
        ('unique_requisition_product',
         'UNIQUE(requisition_id, product_id)',
         'Ya existe un registro para este producto en esta requisición.')
    ]

    @api.depends('requisition_id', 'product_id', 'requisition_id.purchase_ids.order_line.move_ids.state')
    def _compute_cantidad_entregada(self):
        """Calcula la cantidad entregada basada en los movimientos validados"""
        for record in self:
            cantidad = 0.0
            if record.requisition_id and record.product_id:
                # Obtener todas las órdenes de compra relacionadas con la requisición
                purchase_orders = record.requisition_id.purchase_ids
                
                for po in purchase_orders:
                    # Buscar las líneas de la orden de compra con el producto
                    po_lines = po.order_line.filtered(
                        lambda l: l.product_id == record.product_id
                    )
                    
                    for line in po_lines:
                        # Obtener los movimientos de stock validados (done)
                        moves = line.move_ids.filtered(
                            lambda m: m.state == 'done' and m.product_id == record.product_id
                        )
                        
                        for move in moves:
                            # Sumar la cantidad del movimiento convertida a la UdM del producto
                            if move.product_uom != record.uom_id:
                                cantidad += move.product_uom._compute_quantity(
                                    move.product_uom_qty,
                                    record.uom_id
                                )
                            else:
                                cantidad += move.product_uom_qty
            
            record.cantidad_entregada = cantidad

    @api.depends('demanda', 'cantidad_entregada')
    def _compute_fill_rate(self):
        """Calcula el Fill Rate como (Cantidad Entregada / Demanda) * 100"""
        for record in self:
            if record.demanda > 0:
                record.fill_rate = (record.cantidad_entregada / record.demanda) * 100
            else:
                record.fill_rate = 0.0

    def name_get(self):
        """Método para mostrar el nombre en las referencias"""
        result = []
        for record in self:
            name = f"{record.requisition_name} - {record.product_name}"
            result.append((record.id, name))
        return result