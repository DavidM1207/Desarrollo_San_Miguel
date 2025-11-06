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
        # La relación es por string: move.requisition_order contiene el nombre de la requisición
        moves_with_requisition = self.filtered(lambda m: m.requisition_order)
        
        if moves_with_requisition:
            self._update_fill_rate_report(moves_with_requisition)
        
        return res

    def _update_fill_rate_report(self, moves):
        """
        Actualiza o crea registros en el reporte Fill Rate para los movimientos dados
        """
        fill_rate_model = self.env['fill.rate.report']
        
        # Agrupar movimientos por requisición
        requisitions_to_update = {}
        for move in moves:
            if move.requisition_order not in requisitions_to_update:
                requisitions_to_update[move.requisition_order] = set()
            requisitions_to_update[move.requisition_order].add(move.product_id.id)
        
        # Actualizar cada requisición afectada
        for req_name, product_ids in requisitions_to_update.items():
            # Buscar la requisición por nombre
            requisition = self.env['employee.purchase.requisition'].search([
                ('name', '=', req_name)
            ], limit=1)
            
            if not requisition:
                continue
            
            # Actualizar cada línea afectada
            for line in requisition.requisition_order_ids:
                if line.product_id.id not in product_ids:
                    continue
                    
                # Verificar si es transferencia interna
                if line.requisition_type != 'internal_transfer':
                    continue
                
                # Buscar o crear registro en el reporte
                existing_report = fill_rate_model.search([
                    ('requisition_id', '=', requisition.id),
                    ('requisition_line_id', '=', line.id)
                ], limit=1)
                
                # Calcular cantidad entregada
                qty_delivered = fill_rate_model._get_delivered_quantity(requisition, line)
                
                data = {
                    'requisition_id': requisition.id,
                    'requisition_line_id': line.id,
                    'product_id': line.product_id.id,
                    'demand': line.demand if hasattr(line, 'demand') else line.qty,
                    'qty_original': line.qty,
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
                lambda m: m.requisition_order
            )
            if moves_with_requisition:
                stock_move_model = self.env['stock.move']
                stock_move_model._update_fill_rate_report(moves_with_requisition)
        
        return res
