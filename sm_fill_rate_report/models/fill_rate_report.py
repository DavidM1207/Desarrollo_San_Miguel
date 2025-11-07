# -*- coding: utf-8 -*-
from odoo import models, fields, api

class FillRateReport(models.Model):
    _name = 'fill.rate.report'
    _description = 'Reporte de Fill Rate'
    _order = 'create_date desc'
    _rec_name = 'requisition_name'

    create_date = fields.Datetime(string='Fecha de Creación', readonly=True)
    requisition_id = fields.Many2one('employee.purchase.requisition', string='Requisición', readonly=True, ondelete='cascade')
    requisition_name = fields.Char(string='Nombre de Requisición', readonly=True)
    product_id = fields.Many2one('product.product', string='Producto', readonly=True)
    cantidad_demandada = fields.Float(string='Cantidad Demandada', readonly=True)
    cantidad_recepcionada = fields.Float(string='Cantidad Recepcionada', readonly=True)
    fill_rate = fields.Float(string='% Fill Rate', readonly=True)
    stock_move_id = fields.Many2one('stock.move', string='Movimiento', readonly=True, ondelete='cascade')

    @api.model
    def _generate_report_data(self):
        """Genera los datos del reporte desde employee_purchase_requisition y stock.move"""
        # Limpiar registros existentes
        self.search([]).unlink()
        
        # Buscar todas las requisiciones
        requisitions = self.env['employee.purchase.requisition'].search([])
        
        for requisition in requisitions:
            # Buscar movimientos en estado done directamente
            moves = self.env['stock.move'].search([
                ('state', '=', 'done')
            ])
            
            # Filtrar movimientos relacionados con esta requisición
            moves_relacionados = moves.filtered(
                lambda m: m.origin == requisition.name or 
                (m.picking_id and m.picking_id.origin == requisition.name)
            )
            
            # Crear un registro por cada movimiento encontrado
            for move in moves_relacionados:
                cantidad_demandada = move.product_uom_qty or 0.0
                cantidad_recepcionada = move.quantity or 0.0
                
                if cantidad_demandada > 0:
                    fill_rate = (cantidad_recepcionada / cantidad_demandada) * 100.0
                else:
                    fill_rate = 0.0
                
                self.create({
                    'create_date': requisition.create_date,
                    'requisition_id': requisition.id,
                    'requisition_name': requisition.name,
                    'product_id': move.product_id.id,
                    'cantidad_demandada': cantidad_demandada,
                    'cantidad_recepcionada': cantidad_recepcionada,
                    'fill_rate': fill_rate,
                    'stock_move_id': move.id,
                })
        
        return True

    @api.model
    def action_refresh_report(self):
        """Acción para refrescar el reporte"""
        self._generate_report_data()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }