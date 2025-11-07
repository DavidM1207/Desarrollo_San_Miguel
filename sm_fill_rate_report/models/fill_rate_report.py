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
            # Buscar movimientos de stock relacionados con la requisición
            # Buscar por el campo origin o por referencia en picking_id
            moves = self.env['stock.move'].search([
                ('state', '=', 'done'),
                '|', '|',
                ('origin', '=', requisition.name),
                ('picking_id.origin', '=', requisition.name),
                ('reference', '=', requisition.name)
            ])
            
            # Si la requisición tiene un campo que vincule directamente con picking
            if hasattr(requisition, 'picking_ids'):
                picking_moves = self.env['stock.move'].search([
                    ('state', '=', 'done'),
                    ('picking_id', 'in', requisition.picking_ids.ids)
                ])
                moves = moves | picking_moves
            
            # Si la requisición tiene un campo que vincule directamente con moves
            if hasattr(requisition, 'move_ids'):
                direct_moves = requisition.move_ids.filtered(lambda m: m.state == 'done')
                moves = moves | direct_moves
            
            # Crear un registro por cada movimiento
            for move in moves:
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