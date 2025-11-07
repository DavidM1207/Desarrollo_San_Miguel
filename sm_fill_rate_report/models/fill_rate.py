from odoo import models, fields, api


class FillRate(models.Model):
    _name = 'fill.rate'
    _description = 'Fill Rate'
    _order = 'create_date desc'

    create_date = fields.Datetime(string='Fecha de Creación')
    requisition_name = fields.Char(string='Número de Requisición')
    product_id = fields.Many2one('product.product', string='Producto')
    fill_rate_percentage = fields.Float(string='% Fill Rate', digits=(5, 2))

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """Generar datos automáticamente al abrir la vista"""
        self.generate_fill_rate_data()
        return super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.model
    def generate_fill_rate_data(self):
        """Genera los datos del fill rate desde las requisiciones"""
        self.search([]).unlink()
        
        requisitions = self.env['employee.purchase.requisition'].search([])
        
        for requisition in requisitions:
            # Buscar pickings con estado 'done' para esta requisición
            done_pickings = self.env['stock.picking'].search([
                ('requisition_order', '=', requisition.name),
                ('state', '=', 'done')
            ])
            
            if not done_pickings:
                continue
            
            # Obtener todos los movimientos
            all_moves = done_pickings.mapped('move_ids_without_package')
            
            # Agrupar por producto
            products = all_moves.mapped('product_id')
            
            for product in products:
                # Filtrar movimientos de este producto
                product_moves = all_moves.filtered(lambda m: m.product_id.id == product.id)
                
                # Sumar cantidades
                total_demand = sum(product_moves.mapped('product_uom_qty'))
                total_received = sum(product_moves.mapped('quantity'))
                
                # Calcular fill rate
                fill_rate = 0.0
                if total_demand > 0:
                    fill_rate = (total_received / total_demand) * 100
                
                # Crear registro
                self.create({
                    'create_date': requisition.create_date,
                    'requisition_name': requisition.name,
                    'product_id': product.id,
                    'fill_rate_percentage': fill_rate,
                })
        
        return True