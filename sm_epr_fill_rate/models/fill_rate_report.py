# models/fill_rate_report.py
from odoo import models, fields, api

class FillRateReport(models.TransientModel):
    _name = 'fill.rate.report'
    _description = 'Fill Rate Report'
    _order = 'date_created desc'

    requisition_name = fields.Char(string='Número Requisición', readonly=True)
    date_created = fields.Datetime(string='Fecha Creación', readonly=True)
    product_id = fields.Many2one('product.product', string='Producto', readonly=True)
    demand = fields.Char(string='Demanda', readonly=True)
    quantity_original = fields.Float(string='Cantidad Original', digits='Product Unit of Measure', readonly=True)
    quantity_delivered = fields.Float(string='Cantidad Demanda', digits='Product Unit of Measure', readonly=True)
    fill_rate = fields.Float(string='Fill Rate (%)', digits=(16, 2), readonly=True)

    @api.model
    def generate_report_data(self):
        report_data = []
        
        EmployeeRequisition = self.env['employee.purchase.requisition']
        StockMoveLine = self.env['stock.move.line']
        
        requisitions = EmployeeRequisition.search([])
        
        for requisition in requisitions:
            
            product_original = {}
            for line in requisition.line_ids:
                product_id = line.product_id.id
                if product_id not in product_original:
                    product_original[product_id] = 0.0
                product_original[product_id] += line.product_qty
            
            move_lines = StockMoveLine.search([
                ('picking_id.origin', '=', requisition.name),
                ('picking_id.picking_type_code', '=', 'internal'),
                ('state', '=', 'done')
            ])
            
            product_delivered = {}
            for move_line in move_lines:
                product_id = move_line.product_id.id
                if product_id not in product_delivered:
                    product_delivered[product_id] = 0.0
                product_delivered[product_id] += move_line.qty_done
            
            all_products = set(list(product_original.keys()) + list(product_delivered.keys()))
            
            for product_id in all_products:
                quantity_original = product_original.get(product_id, 0.0)
                quantity_delivered = product_delivered.get(product_id, 0.0)
                
                fill_rate = 0.0
                if quantity_original > 0:
                    fill_rate = (quantity_delivered / quantity_original) * 100
                
                Product = self.env['product.product'].browse(product_id)
                
                report_data.append({
                    'requisition_name': requisition.name,
                    'date_created': requisition.create_date,
                    'product_id': product_id,
                    'demand': requisition.employee_id.name if hasattr(requisition, 'employee_id') and requisition.employee_id else '',
                    'quantity_original': quantity_original,
                    'quantity_delivered': quantity_delivered,
                    'fill_rate': fill_rate,
                })
        
        return report_data

    @api.model
    def action_open_report(self):
        self.search([]).unlink()
        
        report_data = self.generate_report_data()
        
        for data in report_data:
            self.create(data)
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Fill Rate',
            'res_model': 'fill.rate.report',
            'view_mode': 'tree',
            'target': 'current',
        }