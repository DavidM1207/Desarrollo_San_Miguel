from odoo import models, fields, api


class FillRate(models.Model):
    _name = 'fill.rate'
    _description = 'Fill Rate Report'
    _order = 'create_date desc'

    create_date = fields.Datetime(string='Fecha de Creación', readonly=True)
    requisition_name = fields.Char(string='Número de Requisición', readonly=True)
    product_id = fields.Many2one('product.product', string='Producto', readonly=True)
    fill_rate_percentage = fields.Float(string='% Fill Rate', digits=(5, 2), readonly=True)
    demand_qty = fields.Float(string='Cantidad Demandada', digits=(16, 2), readonly=True)
    received_qty = fields.Float(string='Cantidad Recibida', digits=(16, 2), readonly=True)

    @api.model
    def _get_fill_rate_data(self):
        """Obtiene los datos calculados del fill rate"""
        # Buscar todos los movimientos done con requisition_order
        StockMove = self.env['stock.move']
        
        moves = StockMove.search([
            ('requisition_order', '!=', False),
            ('state', '=', 'done')
        ])
        
        if not moves:
            return []
        
        # Diccionario para agrupar datos: {(req_name, product_id): {'demand': X, 'received': Y, 'date': Z}}
        data_dict = {}
        
        for move in moves:
            req_name = move.requisition_order
            product = move.product_id
            key = (req_name, product.id)
            
            if key not in data_dict:
                # Buscar fecha de creación de la requisición
                requisition = self.env['employee.purchase.requisition'].search([
                    ('name', '=', req_name)
                ], limit=1)
                
                data_dict[key] = {
                    'requisition_name': req_name,
                    'product_id': product.id,
                    'create_date': requisition.create_date if requisition else fields.Datetime.now(),
                    'demand': 0.0,
                    'received': 0.0
                }
            
            # Identificar si es movimiento de origen o destino
            if move.usage_origin == 'internal' and move.usage_dest == 'transit':
                # Movimiento de ORIGEN - esto es lo que salió (DEMANDA)
                data_dict[key]['demand'] += move.quantity
                
            elif move.usage_origin == 'transit' and move.usage_dest == 'internal':
                # Movimiento de DESTINO - esto es lo que llegó (RECIBIDO)
                data_dict[key]['received'] += move.quantity
        
        # Convertir diccionario a lista de valores para crear registros
        result = []
        for key, values in data_dict.items():
            if values['demand'] > 0:
                fill_rate = (values['received'] / values['demand']) * 100
                result.append({
                    'create_date': values['create_date'],
                    'requisition_name': values['requisition_name'],
                    'product_id': values['product_id'],
                    'demand_qty': values['demand'],
                    'received_qty': values['received'],
                    'fill_rate_percentage': fill_rate,
                })
        
        return result

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """Override para generar datos dinámicamente"""
        # Limpiar datos existentes
        self.search([]).unlink()
        
        # Obtener datos calculados
        fill_rate_data = self._get_fill_rate_data()
        
        # Crear registros temporales
        for data in fill_rate_data:
            self.create(data)
        
        # Llamar al search_read original
        return super(FillRate, self).search_read(
            domain=domain, 
            fields=fields, 
            offset=offset, 
            limit=limit, 
            order=order
        )