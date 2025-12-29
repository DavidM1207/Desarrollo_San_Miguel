# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    tracker_project_ids = fields.One2many(
        'tracker.project',
        'sale_order_id',
        string='Proyectos Tracker'
    )
    
    tracker_project_count = fields.Integer(
        string='Trackers',
        compute='_compute_tracker_project_count'
    )
    
    has_service_products = fields.Boolean(
        string='Tiene Servicios',
        compute='_compute_has_service_products',
        store=True,
        help='Indica si la orden tiene productos de servicio en líneas o BoMs'
    )
    
    @api.depends('tracker_project_ids')
    def _compute_tracker_project_count(self):
        for order in self:
            order.tracker_project_count = len(order.tracker_project_ids)
    
    @api.depends('order_line.product_id')
    def _compute_has_service_products(self):
        for order in self:
            has_service = False
            for line in order.order_line:
                # Verificar que el producto tenga tracker_active=True
                if line.product_id and line.product_id.type == 'service' and line.product_id.tracker_active:
                    has_service = True
                    break
                
                if line.product_id:
                    has_service = self._check_bom_for_services(line.product_id)
                    if has_service:
                        break
            
            order.has_service_products = has_service
    
    def _check_bom_for_services(self, product):
        """Verificar recursivamente si un producto tiene servicios en su BoM (con tracker_active)"""
        bom = self.env['mrp.bom'].search([
            ('product_tmpl_id', '=', product.product_tmpl_id.id)
        ], limit=1)
        
        if not bom:
            return False
        
        for line in bom.bom_line_ids:
            # Verificar que el servicio tenga tracker_active=True
            if line.product_id.type == 'service' and line.product_id.tracker_active:
                return True
            
            if self._check_bom_for_services(line.product_id):
                return True
        
        return False
    
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        
        for order in self:
            # Solo crear proyecto si es una VENTA normal (no devoluciones ni notas de crédito)
            # Verificar que no tenga invoices con tipo out_refund (nota de crédito)
            is_refund = any(inv.move_type == 'out_refund' for inv in order.invoice_ids)
            
            if order.has_service_products and not order.tracker_project_ids and not is_refund:
                try:
                    order._auto_create_tracker_project()
                except Exception as e:
                    _logger.error('Error al crear proyecto tracker para venta %s: %s', order.name, str(e))
        
        return res
    
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
            # user_id se deja vacío intencionalmente - se asignará antes de entregar
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
        
        # Calcular abasto basado en almacén de la tienda
        self._calculate_stock_shortage(project, analytic_account)
        
        return project
    
    def _calculate_stock_shortage(self, project, analytic_account):
        """Calcular faltantes de stock basado en los pickings y cantidad real en almacén"""
        self.ensure_one()
        
        # Obtener almacén de la tienda
        warehouse = analytic_account.warehouse_id if analytic_account.warehouse_id else False
        
        if not warehouse:
            _logger.warning('⚠ Tienda %s no tiene almacén configurado, no se puede calcular abasto', 
                          analytic_account.name)
            return
        
        _logger.info('=== CALCULANDO ABASTO PARA ALMACÉN %s ===', warehouse.name)
        
        # Obtener ubicación de stock del almacén (donde está el inventario físico)
        stock_location = warehouse.lot_stock_id
        
        if not stock_location:
            _logger.warning('⚠ Almacén %s no tiene ubicación de stock configurada', warehouse.name)
            return
        
        _logger.info('Ubicación de stock: %s (ID: %s)', stock_location.complete_name, stock_location.id)
        
        # Limpiar registros de abasto previos del proyecto
        self.env['tracker.stock.shortage'].search([('project_id', '=', project.id)]).unlink()
        
        # Buscar pickings asociados a esta orden de venta (entregas pendientes)
        pickings = self.picking_ids.filtered(lambda p: p.state not in ['done', 'cancel'])
        
        if not pickings:
            _logger.info('No hay pickings pendientes para verificar abasto')
            return
        
        _logger.info('Pickings encontrados: %s', ', '.join(pickings.mapped('name')))
        
        shortage_obj = self.env['tracker.stock.shortage']
        products_checked = set()
        
        # Revisar movimientos de stock de los pickings
        for picking in pickings:
            _logger.info('Revisando picking: %s (estado: %s)', picking.name, picking.state)
            
            for move in picking.move_ids:
                product = move.product_id
                
                # Solo verificar productos almacenables
                if not product or product.type != 'product':
                    continue
                
                # Evitar duplicados
                if product.id in products_checked:
                    continue
                
                products_checked.add(product.id)
                
                demand_qty = move.product_uom_qty
                
                # Buscar cantidad directamente en stock.quant
                quants = self.env['stock.quant'].search([
                    ('product_id', '=', product.id),
                    ('location_id', '=', stock_location.id),
                ])
                product_qty = sum(quants.mapped('quantity'))
                
                # Solo crear registro si falta stock
                if product_qty < demand_qty:
                    shortage_vals = {
                        'project_id': project.id,
                        'product_id': product.id,
                        'demand_qty': demand_qty,
                        'available_qty': product_qty,
                        'state': 'sin_abasto',
                        'warehouse_id': warehouse.id,
                        'analytic_account_id': analytic_account.id,
                    }
                    shortage_obj.create(shortage_vals)
        
        _logger.info('=== CÁLCULO DE ABASTO COMPLETADO ===')
        return project
    
    def _get_service_products_from_bom(self):
        """Obtener productos de servicio de la venta y sus BoMs recursivamente (solo con tracker_active)"""
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
                    
                    # Solo agregar servicios con tracker_active=True
                    if component.type == 'service' and component.tracker_active:
                        _logger.debug('Servicio encontrado: %s (qty: %s)', component.name, component_qty)
                        if component in service_products:
                            service_products[component] += component_qty
                        else:
                            service_products[component] = component_qty
                    else:
                        process_bom_recursive(component, component_qty)
            else:
                # Solo agregar servicios con tracker_active=True
                if product.type == 'service' and product.tracker_active:
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
    
    def action_view_tracker_projects(self):
        self.ensure_one()
        return {
            'name': _('Proyectos Tracker'),
            'type': 'ir.actions.act_window',
            'res_model': 'tracker.project',
            'view_mode': 'tree,form,kanban',
            'domain': [('sale_order_id', '=', self.id)],
            'context': {'default_sale_order_id': self.id},
        }