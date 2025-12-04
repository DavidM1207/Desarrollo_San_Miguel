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
    
    def _order_fields(self, ui_order):
        """Override para crear tracker después de procesar la orden"""
        res = super(PosOrder, self)._order_fields(ui_order)
        return res
    
    @api.model
    def _process_order(self, order, draft, existing_order):
        """Override para crear tracker project automáticamente"""
        pos_order = super(PosOrder, self)._process_order(order, draft, existing_order)
        
        if pos_order and not draft:
            order_obj = self.browse(pos_order)
            if order_obj.has_service_products and not order_obj.tracker_project_ids:
                try:
                    order_obj._auto_create_tracker_project()
                except Exception as e:
                    _logger.error('Error al crear proyecto tracker para POS %s: %s', order_obj.name, str(e))
        
        return pos_order
    
    def _auto_create_tracker_project(self):
        """Crear proyecto tracker automáticamente desde orden POS"""
        self.ensure_one()
        
        # Obtener cuenta analítica de la sesión POS o config
        analytic_account = False
        if self.session_id and self.session_id.config_id:
            # Intentar obtener de la configuración del POS
            if hasattr(self.session_id.config_id, 'analytic_account_id'):
                analytic_account = self.session_id.config_id.analytic_account_id
        
        # Si no hay cuenta analítica, intentar de las líneas
        if not analytic_account:
            for line in self.lines:
                if line.product_id and line.product_id.categ_id:
                    # Buscar cuenta analítica por defecto en la categoría o producto
                    if hasattr(line.product_id, 'analytic_account_id'):
                        analytic_account = line.product_id.analytic_account_id
                        break
        
        if not analytic_account:
            _logger.warning('No se pudo crear tracker para POS %s: No tiene cuenta analítica', self.name)
            return False
        
        project_vals = {
            'pos_order_id': self.id,
            'partner_id': self.partner_id.id if self.partner_id else self.env.ref('base.public_partner').id,
            'analytic_account_id': analytic_account.id,
            'promise_date': self.date_order.date(),
            'user_id': self.user_id.id if self.user_id else self.env.user.id,
        }
        
        project = self.env['tracker.project'].create(project_vals)
        _logger.info('Proyecto tracker %s creado para POS %s', project.name, self.name)
        
        service_products = self._get_service_products_from_bom()
        
        if not service_products:
            _logger.warning('No se encontraron servicios en POS %s', self.name)
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
    
    def action_view_tracker_projects(self):
        """Ver proyectos tracker de la orden POS"""
        self.ensure_one()
        return {
            'name': _('Proyectos Tracker'),
            'type': 'ir.actions.act_window',
            'res_model': 'tracker.project',
            'view_mode': 'tree,form,kanban',
            'domain': [('pos_order_id', '=', self.id)],
            'context': {'default_pos_order_id': self.id},
        }