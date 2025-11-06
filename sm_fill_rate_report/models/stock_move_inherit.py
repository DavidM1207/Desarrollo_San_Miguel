# -*- coding: utf-8 -*-

from odoo import api, models


class StockMoveInherit(models.Model):
    """
    Extiende stock.move para actualizar automáticamente el reporte Fill Rate
    cuando un movimiento se marca como 'done'
    """
    _inherit = 'stock.move'

    def _action_done(self, cancel_backorder=False):
        """
        Override del método _action_done para actualizar el reporte Fill Rate
        cuando se completan movimientos relacionados con requisiciones
        """
        # Llamar al método padre primero
        res = super(StockMoveInherit, self)._action_done(cancel_backorder=cancel_backorder)
        
        # Actualizar reporte para los movimientos que tienen requisición asociada
        moves_with_requisition = self.filtered(lambda m: hasattr(m, 'requisition_line_id') and m.requisition_line_id)
        
        if moves_with_requisition:
            self._update_fill_rate_report(moves_with_requisition)
        
        return res

    def _update_fill_rate_report(self, moves):
        """
        Actualiza o crea registros en el reporte Fill Rate para los movimientos dados
        """
        fill_rate_model = self.env['fill.rate.report']
        
        # Agrupar movimientos por línea de requisición
        requisition_lines = moves.mapped('requisition_line_id')
        
        for req_line in requisition_lines:
            # Verificar si es transferencia interna
            if req_line.requisition_type != 'internal_transfer':
                continue
            
            # Buscar o crear registro en el reporte
            existing_report = fill_rate_model.search([
                ('requisition_line_id', '=', req_line.id)
            ], limit=1)
            
            # Calcular cantidad entregada
            qty_delivered = fill_rate_model._get_delivered_quantity(req_line)
            
            data = {
                'requisition_id': req_line.requisition_id.id,
                'requisition_line_id': req_line.id,
                'product_id': req_line.product_id.id,
                'demand': req_line.demand if hasattr(req_line, 'demand') else req_line.qty,
                'qty_original': req_line.qty,
                'qty_delivered': qty_delivered,
            }
            
            if existing_report:
                existing_report.write(data)
            else:
                fill_rate_model.create(data)


class StockPickingInherit(models.Model):
    """
    Extiende stock.picking para actualizar el reporte cuando se valida un picking
    """
    _inherit = 'stock.picking'

    def button_validate(self):
        """
        Override para actualizar el reporte Fill Rate después de validar
        """
        res = super(StockPickingInherit, self).button_validate()
        
        # Actualizar reporte para pickings relacionados con requisiciones
        if self.move_ids_without_package:
            moves_with_requisition = self.move_ids_without_package.filtered(
                lambda m: hasattr(m, 'requisition_line_id') and m.requisition_line_id
            )
            if moves_with_requisition:
                stock_move_model = self.env['stock.move']
                stock_move_model._update_fill_rate_report(moves_with_requisition)
        
        return res
