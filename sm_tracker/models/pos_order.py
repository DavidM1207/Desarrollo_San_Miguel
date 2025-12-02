# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    tracker_project_ids = fields.One2many(
        'tracker.project',
        'pos_order_id',
        string='Proyectos Tracker'
    )
    
    has_service_products = fields.Boolean(
        string='Tiene Servicios',
        compute='_compute_has_service_products',
        store=True
    )
    
    @api.depends('lines.product_id.type')
    def _compute_has_service_products(self):
        for order in self:
            has_services = False
            for line in order.lines:
                if line.product_id.type == 'service':
                    has_services = True
                    break
                # Verificar si el producto tiene BoM con servicios
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
            # Verificar recursivamente
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
        
        for line in self.lines:
            product = line.product_id
            qty = line.qty
            
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
        """Crea automáticamente un proyecto tracker para la orden POS"""
        self.ensure_one()
        
        if not self.session_id.config_id.analytic_account_id:
            _logger.warning(f"No se pudo crear tracker para orden POS {self.pos_reference}: No tiene cuenta analítica")
            return False
        
        service_products = self._get_service_products_from_bom()
        
        if not service_products:
            _logger.info(f"No se creó tracker para orden POS {self.pos_reference}: No tiene servicios")
            return False
        
        project_vals = {
            'pos_order_id': self.id,
            'partner_id': self.partner_id.id,
            'analytic_account_id': self.session_id.config_id.analytic_account_id.id,
            'promise_date': self.date_order.date(),
            'company_id': self.company_id.id,
        }
        
        project = self.env['tracker.project'].create(project_vals)
        _logger.info(f"Proyecto tracker {project.name} creado para orden POS {self.pos_reference}")
        
        for service_id, service_data in service_products.items():
            product = service_data['product']
            qty = service_data['qty']
            
            task_vals = {
                'project_id': project.id,
                'product_id': product.id,
                'name': product.name,
                'quantity': qty,
                'analytic_account_id': self.session_id.config_id.analytic_account_id.id,
                'company_id': self.company_id.id,
            }
            
            task = self.env['tracker.task'].create(task_vals)
            _logger.info(f"Tarea creada: {task.name} (cantidad: {qty}) para proyecto {project.name}")
        
        return project
    
    def action_pos_order_paid(self):
        """Override para crear proyecto tracker después de pagar"""
        res = super(PosOrder, self).action_pos_order_paid()
        
        for order in self:
            if order.has_service_products and not order.tracker_project_ids:
                order._auto_create_tracker_project()
        
        return res