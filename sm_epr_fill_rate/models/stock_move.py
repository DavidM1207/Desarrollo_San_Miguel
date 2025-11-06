# -*- coding: utf-8 -*-

from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_done(self, cancel_backorder=False):
        """Override _action_done para actualizar fill rate cuando se validan movimientos"""
        res = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)
        
        # Recopilar las requisiciones afectadas
        requisitions_to_update = self.env['purchase.requisition']
        
        for move in self:
            # Verificar si el movimiento está relacionado con una orden de compra
            if move.purchase_line_id and move.purchase_line_id.order_id:
                purchase_order = move.purchase_line_id.order_id
                
                # Verificar si la orden de compra está relacionada con una requisición
                if purchase_order.requisition_id:
                    requisitions_to_update |= purchase_order.requisition_id
        
        # Actualizar los registros de fill rate para las requisiciones afectadas
        if requisitions_to_update:
            FillRate = self.env['purchase.requisition.fill.rate']
            for requisition in requisitions_to_update:
                # Buscar los registros de fill rate relacionados con esta requisición
                fill_rate_records = FillRate.search([
                    ('requisition_id', '=', requisition.id)
                ])
                
                # Forzar el recálculo de la cantidad entregada
                if fill_rate_records:
                    fill_rate_records._compute_cantidad_entregada()
        
        return res

    def _action_cancel(self):
        """Override _action_cancel para actualizar fill rate cuando se cancelan movimientos"""
        # Recopilar las requisiciones afectadas antes de cancelar
        requisitions_to_update = self.env['purchase.requisition']
        
        for move in self:
            if move.purchase_line_id and move.purchase_line_id.order_id:
                purchase_order = move.purchase_line_id.order_id
                if purchase_order.requisition_id:
                    requisitions_to_update |= purchase_order.requisition_id
        
        res = super(StockMove, self)._action_cancel()
        
        # Actualizar los registros de fill rate
        if requisitions_to_update:
            FillRate = self.env['purchase.requisition.fill.rate']
            for requisition in requisitions_to_update:
                fill_rate_records = FillRate.search([
                    ('requisition_id', '=', requisition.id)
                ])
                
                if fill_rate_records:
                    fill_rate_records._compute_cantidad_entregada()
        
        return res