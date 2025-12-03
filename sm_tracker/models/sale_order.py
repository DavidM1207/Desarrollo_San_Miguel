# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from collections import defaultdict


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    tracker_project_id = fields.Many2one(
        'tracker.project',
        string='Proyecto Tracker',
        readonly=True,
        copy=False,
        ondelete='set null'
    )
    
    tracker_project_count = fields.Integer(
        string='Proyectos Tracker',
        compute='_compute_tracker_project_count'
    )
    
    @api.depends('tracker_project_id')
    def _compute_tracker_project_count(self):
        for order in self:
            # Verificar si el modelo tracker.project existe (importante para desinstalación)
            if 'tracker.project' in self.env:
                order.tracker_project_count = 1 if order.tracker_project_id else 0
            else:
                order.tracker_project_count = 0
    
    def action_view_tracker_project(self):
        """Acción para ver el proyecto tracker"""
        self.ensure_one()
        
        # Verificar si el modelo existe (importante para desinstalación)
        if 'tracker.project' not in self.env:
            raise UserError(_('El módulo Tracker no está instalado o está siendo desinstalado.'))
        
        if not self.tracker_project_id:
            raise UserError(_('No hay proyecto tracker asociado a esta orden de venta.'))
        
        return {
            'name': _('Proyecto Tracker'),
            'type': 'ir.actions.act_window',
            'res_model': 'tracker.project',
            'view_mode': 'form',
            'res_id': self.tracker_project_id.id,
            'target': 'current',
        }
    
    def action_confirm(self):
        """Override para generar proyecto tracker automáticamente"""
        res = super(SaleOrder, self).action_confirm()
        
        # Verificar que el modelo tracker.project exista
        if 'tracker.project' not in self.env:
            return res
        
        for order in self:
            # Solo generar si hay cuenta analítica y no existe ya un proyecto
            if order.analytic_account_id and not order.tracker_project_id:
                order._generate_tracker_project()
        
        return res
    
    def _generate_tracker_project(self):
        """Generar proyecto tracker con sus tareas desde BoMs"""
        self.ensure_one()
        
        # Validar cuenta analítica
        if not self.analytic_account_id:
            raise UserError(_(
                'La orden de venta debe tener una cuenta analítica (Tienda) asignada.'
            ))
        
        # Extraer servicios de las líneas de venta y sus BoMs
        services_data = self._extract_services_from_boms()
        
        if not services_data:
            # No hay servicios para procesar
            return
        
        # Crear proyecto tracker
        project_vals = {
            'sale_order_id': self.id,
            'analytic_account_id': self.analytic_account_id.id,
            'user_id': self.user_id.id if self.user_id else self.env.user.id,
            'state': 'pending',
        }
        
        tracker_project = self.env['tracker.project'].create(project_vals)
        
        # Crear tareas para cada servicio
        for service_id, data in services_data.items():
            task_vals = {
                'project_id': tracker_project.id,
                'product_id': service_id,
                'quantity': data['quantity'],
                'sale_order_line_id': data.get('sale_line_id'),
                'state': 'draft',
            }
            self.env['tracker.task'].create(task_vals)
        
        # Vincular proyecto a la orden de venta
        self.tracker_project_id = tracker_project.id
        
        return tracker_project
    
    def _extract_services_from_boms(self):
        """
        Extraer servicios desde BoMs recursivamente y acumular cantidades
        Retorna: dict {product_id: {'quantity': float, 'sale_line_id': int}}
        """
        services_dict = defaultdict(lambda: {'quantity': 0.0, 'sale_line_id': False})
        
        for line in self.order_line:
            product = line.product_id
            qty_sold = line.product_uom_qty
            
            # Si el producto mismo es un servicio, agregarlo
            if product.type == 'service':
                services_dict[product.id]['quantity'] += qty_sold
                if not services_dict[product.id]['sale_line_id']:
                    services_dict[product.id]['sale_line_id'] = line.id
            
            # Buscar BoM del producto
            bom = self.env['mrp.bom']._bom_find(
                product=product,
                company_id=self.company_id.id,
                bom_type='normal'
            )
            
            if bom:
                # Extraer servicios de la BoM recursivamente
                services_from_bom = self._extract_services_from_bom(
                    bom, qty_sold, line.id
                )
                
                # Acumular cantidades
                for service_id, data in services_from_bom.items():
                    services_dict[service_id]['quantity'] += data['quantity']
                    if not services_dict[service_id]['sale_line_id']:
                        services_dict[service_id]['sale_line_id'] = data['sale_line_id']
        
        return dict(services_dict)
    
    def _extract_services_from_bom(self, bom, multiplier, sale_line_id):
        """
        Extraer servicios de una BoM recursivamente
        
        Args:
            bom: mrp.bom record
            multiplier: cantidad a multiplicar (cantidad vendida)
            sale_line_id: ID de la línea de venta
        
        Returns:
            dict {product_id: {'quantity': float, 'sale_line_id': int}}
        """
        services_dict = defaultdict(lambda: {'quantity': 0.0, 'sale_line_id': sale_line_id})
        
        for bom_line in bom.bom_line_ids:
            component = bom_line.product_id
            qty_in_bom = bom_line.product_qty
            
            # Calcular cantidad total: qty_en_bom × multiplier
            total_qty = qty_in_bom * multiplier
            
            # Si el componente es un servicio, agregarlo
            if component.type == 'service':
                services_dict[component.id]['quantity'] += total_qty
            
            # Si el componente tiene su propia BoM, buscar recursivamente
            sub_bom = self.env['mrp.bom']._bom_find(
                product=component,
                company_id=self.company_id.id,
                bom_type='normal'
            )
            
            if sub_bom:
                # Llamada recursiva con el nuevo multiplicador
                sub_services = self._extract_services_from_bom(
                    sub_bom, total_qty, sale_line_id
                )
                
                # Acumular servicios de la sub-BoM
                for service_id, data in sub_services.items():
                    services_dict[service_id]['quantity'] += data['quantity']
        
        return dict(services_dict)