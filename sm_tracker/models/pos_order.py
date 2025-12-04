# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
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
        store=True,
        help='Indica si la orden tiene productos de servicio en líneas o BoMs'
    )
    
    @api.depends('lines.product_id')
    def _compute_has_service_products(self):
        for order in self:
            has_service = False
            for line in order.lines:
                if line.product_id and line.product_id.type == 'service':
                    has_service = True
                    break
                
                if line.product_id:
                    has_service = self._check_bom_for_services(line.product_id)
                    if has_service:
                        break
            
            order.has_service_products = has_service
    
    def _check_bom_for_services(self, product):
        """Verificar recursivamente si un producto tiene servicios en su BoM"""
        bom = self.env['mrp.bom'].search([
            ('product_tmpl_id', '=', product.product_tmpl_id.id)
        ], limit=1)
        
        if not bom:
            return False
        
        for line in bom.bom_line_ids:
            if line.product_id.type == 'service':
                return True
            
            if self._check_bom_for_services(line.product_id):
                return True
        
        return False
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create para generar tracker automáticamente después de crear la orden"""
        orders = super(PosOrder, self).create(vals_list)
        
        for order in orders:
            # Solo crear tracker si la orden está confirmada (estado 'paid' o 'done')
            if order.state in ['paid', 'done', 'invoiced']:
                if order.has_service_products and not order.tracker_project_ids:
                    try:
                        order._auto_create_tracker_project()
                    except Exception as e:
                        _logger.error('Error al crear proyecto tracker para POS %s: %s', order.name, str(e))
        
        return orders
    
    def write(self, vals):
        """Override write para crear tracker cuando el estado cambia a pagado"""
        res = super(PosOrder, self).write(vals)
        
        # Si el estado cambió a pagado/completado, verificar si necesita tracker
        if vals.get('state') in ['paid', 'done', 'invoiced']:
            for order in self:
                if order.has_service_products and not order.tracker_project_ids:
                    try:
                        order._auto_create_tracker_project()
                    except Exception as e:
                        _logger.error('Error al crear proyecto tracker para POS %s: %s', order.name, str(e))
        
        return res
    
    def _auto_create_tracker_project(self):
        """Crear proyecto tracker automáticamente desde orden POS"""
        self.ensure_one()
        
        # Obtener cuenta analítica de la sesión POS
        analytic_account = False
        
        # Opción 1: Desde la configuración del POS
        if self.session_id and self.session_id.config_id:
            if hasattr(self.session_id.config_id, 'analytic_account_id'):
                analytic_account = self.session_id.config_id.analytic_account_id
        
        # Opción 2: Desde las líneas de la orden
        if not analytic_account:
            for line in self.lines:
                if hasattr(line, 'analytic_account_id') and line.analytic_account_id:
                    analytic_account = line.analytic_account_id
                    break
        
        # Opción 3: Buscar cuenta analítica por defecto de la tienda
        if not analytic_account and self.session_id and self.session_id.config_id:
            # Buscar por nombre de la tienda o config_id
            analytic_account = self.env['account.analytic.account'].search([
                '|',
                ('name', 'ilike', self.session_id.config_id.name),
                ('name', 'ilike', 'POS')
            ], limit=1)
        
        if not analytic_account:
            _logger.warning('No se pudo crear tracker para POS %s: No tiene cuenta analítica', self.name)
            return False
        
        # Determinar partner
        partner = self.partner_id if self.partner_id else self.env.ref('base.public_partner')
        
        project_vals = {
            'pos_order_id': self.id,
            'partner_id': partner.id,
            'analytic_account_id': analytic_account.id,
            'promise_date': self.date_order.date(),
            'user_id': self.user_id.id if self.user_id else self.env.user.id,
        }
        
        project = self.env['tracker.project'].create(project_vals)
        _logger.info('Proyecto tracker %s creado para POS %s', project.name, self.name)
        
        # Obtener servicios de la orden
        service_products = self._get_service_products_from_bom()
        
        if not service_products:
            _logger.warning('No se encontraron servicios en POS %s', self.name)
            return project
        
        # Crear tareas para cada servicio
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
    
    def _get_service_products_from_bom(self):
        """Obtener productos de servicio de la orden POS y sus BoMs recursivamente"""
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
        
        for line in self.lines:
            if line.product_id:
                _logger.debug('Procesando línea de POS: %s (qty: %s)', line.product_id.name, line.qty)
                process_bom_recursive(line.product_id, line.qty)
        
        _logger.info('Total servicios encontrados en POS %s: %s', self.name, len(service_products))
        return service_products