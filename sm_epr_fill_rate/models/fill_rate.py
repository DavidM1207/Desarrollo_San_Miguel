# -*- coding: utf-8 -*-
from odoo import models, fields, api


class FillRate(models.Model):
    _name = 'fill.rate.report'
    _description = 'Fill Rate'

    requisition_id = fields.Many2one('employee.purchase.requisition', string='Requisición', required=True)
    requisition_name = fields.Char(related='requisition_id.name', string='Número Requisición', store=True)
    create_date = fields.Datetime(related='requisition_id.create_date', string='Fecha Creación', store=True)
    product_id = fields.Many2one('product.product', string='Producto', required=True)
    product_name = fields.Char(related='product_id.display_name', string='Nombre Producto', store=True)
    demanda = fields.Float(string='Demanda', required=True)
    cantidad_entregada = fields.Float(string='Cantidad Entregada')
    fill_rate = fields.Float(string='Fill Rate (%)', compute='_compute_fill_rate', store=True)
    uom_id = fields.Many2one(related='product_id.uom_id', string='UdM', store=True)

    @api.depends('demanda', 'cantidad_entregada')
    def _compute_fill_rate(self):
        for rec in self:
            if rec.demanda > 0:
                rec.fill_rate = (rec.cantidad_entregada / rec.demanda) * 100
            else:
                rec.fill_rate = 0.0