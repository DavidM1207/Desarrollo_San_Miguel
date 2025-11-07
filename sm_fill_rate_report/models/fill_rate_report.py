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
            moves_to_process = self.env['stock.move']
            
            # Método 1: Si la requisición tiene relación directa con stock.move
            if hasattr(requisition, 'move_ids'):
                moves_to_process = requisition.move_ids.filtered(lambda m: m.state == 'done')
            
            # Método 2: Si la requisición tiene relación con stock.picking
            if not moves_to_process and hasattr(requisition, 'picking_ids'):
                for picking in requisition.picking_ids:
                    moves_to_process |= picking.move_ids.filtered(lambda m: m.state == 'done')
            
            # Método 3: Buscar por origin en stock.picking
            if not moves_to_process:
                pickings = self.env['stock.picking'].search([
                    ('origin', '=', requisition.name)
                ])
                for picking in pickings:
                    moves_to_process |= picking.move_ids.filtered(lambda m: m.state == 'done')
            
            # Método 4: Buscar directamente por origin en stock.move
            if not moves_to_process:
                moves_to_process = self.env['stock.move'].search([
                    ('origin', '=', requisition.name),
                    ('state', '=', 'done')
                ])
            
            # Método 5: Si la requisición tiene líneas con productos
            if not moves_to_process and hasattr(requisition, 'line_ids'):
                # Obtener los productos de las líneas de la requisición
                products = requisition.line_ids.mapped('product_id')
                
                # Buscar movimientos de esos productos relacionados con la requisición
                # por reference, origin o picking
                moves_to_process = self.env['stock.move'].search([
                    ('product_id', 'in', products.ids),
                    ('state', '=', 'done'),
                    '|', '|',
                    ('origin', '=', requisition.name),
                    ('reference', 'ilike', requisition.name),
                    ('picking_id.origin', '=', requisition.name)
                ])
            
            # Crear un registro por cada movimiento encontrado
            for move in moves_to_process:
                # Calcular fill rate
                cantidad_demandada = move.product_uom_qty or 0
                cantidad_recepcionada = move.quantity or 0
                
                if cantidad_demandada > 0:
                    fill_rate = (cantidad_recepcionada / cantidad_demandada) * 100
                else:
                    fill_rate = 0
                
                # Crear registro del reporte
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


class EmployeePurchaseRequisition(models.Model):
    _inherit = 'employee.purchase.requisition'

    @api.model
    def create(self, vals):
        """Override create para actualizar el reporte cuando se crea una requisición"""
        res = super(EmployeePurchaseRequisition, self).create(vals)
        self.env['fill.rate.report']._generate_report_data()
        return res

    def write(self, vals):
        """Override write para actualizar el reporte cuando se modifica una requisición"""
        res = super(EmployeePurchaseRequisition, self).write(vals)
        self.env['fill.rate.report']._generate_report_data()
        return res


class StockMove(models.Model):
    _inherit = 'stock.move'

    def write(self, vals):
        """Override write para actualizar el reporte cuando cambia el estado del movimiento"""
        res = super(StockMove, self).write(vals)
        if 'state' in vals and vals['state'] == 'done':
            self.env['fill.rate.report']._generate_report_data()
        return res

    @api.model
    def create(self, vals):
        """Override create para actualizar el reporte cuando se crea un movimiento"""
        res = super(StockMove, self).create(vals)
        if res.state == 'done':
            self.env['fill.rate.report']._generate_report_data()
        return res