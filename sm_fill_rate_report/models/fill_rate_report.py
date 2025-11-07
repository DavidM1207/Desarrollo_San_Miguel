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
            # Buscar movimientos relacionados
            moves = self._get_moves_for_requisition(requisition)
            
            # Crear un registro por cada movimiento encontrado
            for move in moves:
                # Calcular fill rate
                cantidad_demandada = move.product_uom_qty or 0.0
                cantidad_recepcionada = move.quantity or 0.0
                
                if cantidad_demandada > 0:
                    fill_rate = (cantidad_recepcionada / cantidad_demandada) * 100.0
                else:
                    fill_rate = 0.0
                
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
    def _get_moves_for_requisition(self, requisition):
        """Obtiene los movimientos de stock relacionados con una requisición"""
        StockMove = self.env['stock.move']
        moves = StockMove
        
        # Buscar por relación directa si existe
        if hasattr(requisition, 'move_ids') and requisition.move_ids:
            moves = requisition.move_ids.filtered(lambda m: m.state == 'done')
            if moves:
                return moves
        
        # Buscar por pickings si existe
        if hasattr(requisition, 'picking_ids') and requisition.picking_ids:
            for picking in requisition.picking_ids:
                moves |= picking.move_ids.filtered(lambda m: m.state == 'done')
            if moves:
                return moves
        
        # Buscar por origin en picking
        pickings = self.env['stock.picking'].search([('origin', '=', requisition.name)])
        if pickings:
            for picking in pickings:
                moves |= picking.move_ids.filtered(lambda m: m.state == 'done')
            if moves:
                return moves
        
        # Buscar directamente por origin en move
        moves = StockMove.search([
            ('origin', '=', requisition.name),
            ('state', '=', 'done')
        ])
        if moves:
            return moves
        
        # Buscar por productos de las líneas de requisición
        if hasattr(requisition, 'line_ids') and requisition.line_ids:
            products = requisition.line_ids.mapped('product_id')
            if products:
                moves = StockMove.search([
                    ('product_id', 'in', products.ids),
                    ('state', '=', 'done'),
                    '|', '|',
                    ('origin', '=', requisition.name),
                    ('reference', 'ilike', requisition.name),
                    ('picking_id.origin', '=', requisition.name)
                ])
        
        return moves

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
        try:
            self.env['fill.rate.report']._generate_report_data()
        except:
            pass
        return res

    def write(self, vals):
        """Override write para actualizar el reporte cuando se modifica una requisición"""
        res = super(EmployeePurchaseRequisition, self).write(vals)
        try:
            self.env['fill.rate.report']._generate_report_data()
        except:
            pass
        return res


class StockMove(models.Model):
    _inherit = 'stock.move'

    def write(self, vals):
        """Override write para actualizar el reporte cuando cambia el estado del movimiento"""
        res = super(StockMove, self).write(vals)
        if 'state' in vals and vals['state'] == 'done':
            try:
                self.env['fill.rate.report']._generate_report_data()
            except:
                pass
        return res

    @api.model
    def create(self, vals):
        """Override create para actualizar el reporte cuando se crea un movimiento"""
        res = super(StockMove, self).create(vals)
        if res.state == 'done':
            try:
                self.env['fill.rate.report']._generate_report_data()
            except:
                pass
        return res