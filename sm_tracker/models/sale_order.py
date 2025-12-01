def _get_service_products_from_bom(self):
    """Obtener productos de servicio de la venta y sus BoMs recursivamente"""
    self.ensure_one()
    service_products = {}
    
    def process_bom_recursive(product, qty):
        bom = self.env['mrp.bom'].search([
            ('product_tmpl_id', '=', product.product_tmpl_id.id),
        ], limit=1)
        
        if bom:
            _logger.debug('Procesando BoM de %s', product.name)
            for line in bom.bom_line_ids:
                component = line.product_id
                component_qty = qty * line.product_qty
                
                if component.type == 'service':
                    _logger.debug('Servicio encontrado: %s (qty: %s)', component.name, component_qty)
                    if component in service_products:
                        service_products[component] += component_qty
                    else:
                        service_products[component] = component_qty
                else:
                    process_bom_recursive(component, component_qty)
        else:
            if product.type == 'service':
                _logger.debug('Producto servicio directo: %s (qty: %s)', product.name, qty)
                if product in service_products:
                    service_products[product] += qty
                else:
                    service_products[product] = qty
    
    for line in self.order_line:
        if line.product_id:
            _logger.debug('Procesando línea de venta: %s (qty: %s)', line.product_id.name, line.product_uom_qty)
            process_bom_recursive(line.product_id, line.product_uom_qty)
    
    _logger.info('Total servicios encontrados en venta %s: %s', self.name, len(service_products))
    return service_products

def _auto_create_tracker_project(self):
    self.ensure_one()
    
    analytic_account = False
    if self.analytic_account_id:
        analytic_account = self.analytic_account_id
    else:
        for line in self.order_line:
            if line.analytic_distribution:
                account_ids = [int(k) for k in line.analytic_distribution.keys()]
                if account_ids:
                    analytic_account = self.env['account.analytic.account'].browse(account_ids[0])
                    break
    
    if not analytic_account:
        _logger.warning('No se pudo crear tracker para venta %s: No tiene cuenta analítica', self.name)
        return False
    
    project_vals = {
        'sale_order_id': self.id,
        'partner_id': self.partner_id.id,
        'analytic_account_id': analytic_account.id,
        'promise_date': self.commitment_date or self.date_order.date(),
        'user_id': self.user_id.id,
    }
    
    project = self.env['tracker.project'].create(project_vals)
    _logger.info('Proyecto tracker %s creado para venta %s', project.name, self.name)
    
    service_products = self._get_service_products_from_bom()
    
    if not service_products:
        _logger.warning('No se encontraron servicios en la venta %s', self.name)
        return project
    
    task_obj = self.env['tracker.task']
    for product, qty in service_products.items():
        task_vals = {
            'project_id': project.id,
            'product_id': product.id,
            'name': product.name,
            'quantity': qty,
            'analytic_account_id': analytic_account.id,
        }
        task = task_obj.create(task_vals)
        _logger.info('Tarea creada: %s (cantidad: %s) para proyecto %s', product.name, qty, project.name)
    
    return project