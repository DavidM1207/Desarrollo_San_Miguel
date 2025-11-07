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
        import logging
        _logger = logging.getLogger(__name__)
        
        self.search([]).unlink()  # Limpiar datos anteriores
        
        requisitions = self.env['employee.purchase.requisition'].search([])
        _logger.info(f"Total requisiciones encontradas: {len(requisitions)}")
        
        for requisition in requisitions:
            _logger.info(f"Procesando requisición: {requisition.name}")
            
            # Buscar pickings con el nombre de la requisición y estado 'done'
            done_pickings = self.env['stock.picking'].search([
                ('requisition_order', '=', requisition.name),
                ('state', '=', 'done')
            ])
            _logger.info(f"Pickings en estado done para {requisition.name}: {len(done_pickings)}")
            
            if not done_pickings:
                continue
            
            # Obtener todos los movimientos de estos pickings
            all_moves = done_pickings.mapped('move_ids')
            _logger.info(f"Total movimientos encontrados: {len(all_moves)}")
            
            # Agrupar por producto
            products = all_moves.mapped('product_id')
            _logger.info(f"Productos únicos: {len(products)}")
            
            for product in products:
                # Filtrar movimientos de este producto
                product_moves = all_moves.filtered(lambda m: m.product_id.id == product.id)
                
                total_demand = sum(product_moves.mapped('product_uom_qty'))
                total_received = sum(product_moves.mapped('quantity'))
                
                _logger.info(f"Producto {product.name} - Demanda: {total_demand}, Recibido: {total_received}")
                
                # Calcular fill rate
                fill_rate = 0.0
                if total_demand > 0:
                    fill_rate = (total_received / total_demand) * 100
                
                _logger.info(f"Fill Rate calculado: {fill_rate}%")
                
                # Crear registro
                self.create({
                    'create_date': requisition.create_date,
                    'requisition_name': requisition.name,
                    'product_id': product.id,
                    'fill_rate_percentage': fill_rate,
                })
        
        _logger.info("Proceso de generación completado")
        return True