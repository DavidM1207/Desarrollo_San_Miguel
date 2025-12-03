# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    tracker_project_ids = fields.One2many(
        'tracker.project',
        'sale_order_id',
        string='Proyectos Tracker'
    )
    
    has_service_products = fields.Boolean(
        string='Tiene Servicios',
        compute='_compute_has_service_products',
        store=True
    )
    
    @api.depends('order_line.product_id.type')
    def _compute_has_service_products(self):
        for order in self:
            has_services = False
            for line in order.order_line:
                if line.product_id.type == 'service':
                    has_services = True
                    break
                if self._check_bom_for_services(line.product_id):
                    has_services = True
                    break
            order.has_service_products = has_services
    
    def _check_bom_for_services(self, product):
        """Verifica si un producto tiene servicios en su BoM"""
        bom = self.env['mrp.bom']._bom_find(product=product, company_id=self.company_id.id, bom_type='normal')[product]
        if not bom:
            return False
        
        for line in bom.bom_line_ids:
            if line.product_id.type == 'service':
                return True
            if self._check_bom_for_services(line.product_id):
                return True
        
        return False
    
    def _get_service_products_from_bom(self):
        """Extrae todos los servicios de las BoMs de los productos vendidos, acumulando cantidades"""
        self.ensure_one()
        service_products = {}
        
        def process_bom_recursive(product, qty, parent_name=""):
            """Procesa una BoM recursivamente y acumula servicios"""
            _logger.debug(f"Procesando BoM de {product.name} (cantidad: {qty})")
            
            bom = self.env['mrp.bom']._bom_find(product=product, company_id=self.company_id.id, bom_type='normal')[product]
            
            if bom:
                _logger.debug(f"BoM encontrada: {bom.code or bom.product_tmpl_id.name}")
                for line in bom.bom_line_ids:
                    component = line.product_id
                    component_qty = (line.product_qty / bom.product_qty) * qty
                    
                    if component.type == 'service':
                        _logger.debug(f"Servicio encontrado: {component.name} (qty: {component_qty})")
                        if component.id in service_products:
                            service_products[component.id]['qty'] += component_qty
                        else:
                            service_products[component.id] = {
                                'product': component,
                                'qty': component_qty
                            }
                    else:
                        process_bom_recursive(component, component_qty, component.name)
            else:
                if product.type == 'service':
                    _logger.debug(f"Producto es servicio directo: {product.name} (qty: {qty})")
                    if product.id in service_products:
                        service_products[product.id]['qty'] += qty
                    else:
                        service_products[product.id] = {
                            'product': product,
                            'qty': qty
                        }
        
        for line in self.order_line:
            product = line.product_id
            qty = line.product_uom_qty
            
            if product.type == 'service':
                if product.id in service_products:
                    service_products[product.id]['qty'] += qty
                else:
                    service_products[product.id] = {
                        'product': product,
                        'qty': qty
                    }
            else:
                process_bom_recursive(product, qty)
        
        return service_products
    
    def _auto_create_tracker_project(self):
        """Crea automáticamente un proyecto tracker para la orden de venta"""
        self.ensure_one()
        
        analytic_account = self.analytic_account_id
        if not analytic_account:
            _logger.warning(f"No se pudo crear tracker para venta {self.name}: No tiene cuenta analítica")
            return False
        
        service_products = self._get_service_products_from_bom()
        
        if not service_products:
            _logger.info(f"No se creó tracker para venta {self.name}: No tiene servicios")
            return False
        
        project_vals = {
            'sale_order_id': self.id,
            'partner_id': self.partner_id.id,
            'analytic_account_id': analytic_account.id,
            'promise_date': self.commitment_date or fields.Date.today(),
            'company_id': self.company_id.id,
        }
        
        project = self.env['tracker.project'].create(project_vals)
        _logger.info(f"Proyecto tracker {project.name} creado para venta {self.name}")
        
        for service_id, service_data in service_products.items():
            product = service_data['product']
            qty = service_data['qty']
            
            task_vals = {
                'project_id': project.id,
                'product_id': product.id,
                'name': product.name,
                'quantity': qty,
                'analytic_account_id': analytic_account.id,
                'company_id': self.company_id.id,
            }
            
            task = self.env['tracker.task'].create(task_vals)
            _logger.info(f"Tarea creada: {task.name} (cantidad: {qty}) para proyecto {project.name}")
        
        return project
    
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        
        for order in self:
            if order.has_service_products and not order.tracker_project_ids:
                order._auto_create_tracker_project()
        
        return res
    
    def action_view_tracker_projects(self):
        self.ensure_one()
        return {
            'name': _('Proyectos Tracker'),
            'type': 'ir.actions.act_window',
            'res_model': 'tracker.project',
            'view_mode': 'tree,form',
            'domain': [('sale_order_id', '=', self.id)],
            'context': {'default_sale_order_id': self.id},
        }