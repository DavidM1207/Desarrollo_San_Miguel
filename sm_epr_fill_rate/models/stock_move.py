# -*- coding: utf-8 -*-

from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_done(self, cancel_backorder=False):
        res = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)
        
        requisitions_to_update = self.env['employee.purchase.requisition']
        
        for move in self:
            if move.purchase_line_id and move.purchase_line_id.order_id:
                purchase_order = move.purchase_line_id.order_id
                if hasattr(purchase_order, 'requisition_id') and purchase_order.requisition_id:
                    requisitions_to_update |= purchase_order.requisition_id
        
        if requisitions_to_update:
            FillRate = self.env['purchase.requisition.fill.rate']
            for requisition in requisitions_to_update:
                fill_rate_records = FillRate.search([
                    ('requisition_id', '=', requisition.id)
                ])
                if fill_rate_records:
                    fill_rate_records._compute_cantidad_entregada()
        
        return res

    def _action_cancel(self):
        requisitions_to_update = self.env['employee.purchase.requisition']
        
        for move in self:
            if move.purchase_line_id and move.purchase_line_id.order_id:
                purchase_order = move.purchase_line_id.order_id
                if hasattr(purchase_order, 'requisition_id') and purchase_order.requisition_id:
                    requisitions_to_update |= purchase_order.requisition_id
        
        res = super(StockMove, self)._action_cancel()
        
        if requisitions_to_update:
            FillRate = self.env['purchase.requisition.fill.rate']
            for requisition in requisitions_to_update:
                fill_rate_records = FillRate.search([
                    ('requisition_id', '=', requisition.id)
                ])
                if fill_rate_records:
                    fill_rate_records._compute_cantidad_entregada()
        
        return res