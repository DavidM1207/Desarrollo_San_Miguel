# -*- coding: utf-8 -*-

from odoo import models, api, _
from odoo.exceptions import UserError
from collections import defaultdict


class PosOrder(models.Model):
    _inherit = 'pos.order'
    
    def _process_order(self, order, draft, existing_order):
        """Override para generar proyecto tracker automáticamente después de procesar la orden"""
        # Llamar al método original
        pos_order = super(PosOrder, self)._process_order(order, draft, existing_order)
        
        # Verificar que el módulo tracker esté instalado
        if 'tracker.project' not in self.env:
            return pos_order
        
        # Generar proyecto tracker si aplica
        if pos_order and not draft:
            # Buscar si ya existe un proyecto para esta orden
            existing_project = self.env['tracker.project'].search([
                ('pos_order_id', '=', pos_order.id)
            ], limit=1)
            
            # Solo generar si hay cuenta analítica y no existe ya un proyecto
            if pos_order.session_id.config_id.analytic_account_id and not existing_project:
                pos_order._generate_tracker_project_pos()
        
        return pos_order
    
    def _generate_tracker_project_pos(self):
        """Generar proyecto tracker con sus tareas desde BoMs para órdenes POS"""
        self.ensure_one()
        
        # Obtener cuenta analítica de la configuración del POS
        analytic_account = self.session_id.config_id.analytic_account_id
        
        if not analytic_account:
            # No hay cuenta analítica, no generar proyecto
            return
        
        # Extraer servicios de las líneas de POS y sus BoMs
        services_data = self._extract_services_from_boms_pos()
        
        if not services_data:
            # No hay servicios para procesar
            return
        
        # Crear proyecto tracker
        project_vals = {
            'pos_order_id': self.id,
            'analytic_account_id': analytic_account.id,
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
                'pos_order_line_id': data.get('pos_line_id'),
                'state': 'draft',
            }
            self.env['tracker.task'].create(task_vals)
        
        return tracker_project
    
    def _extract_services_from_boms_pos(self):
        """
        Extraer servicios desde BoMs recursivamente y acumular cantidades para POS
        Retorna: dict {product_id: {'quantity': float, 'pos_line_id': int}}
        """
        services_dict = defaultdict(lambda: {'quantity': 0.0, 'pos_line_id': False})
        
        for line in self.lines:
            product = line.product_id
            qty_sold = line.qty
            
            # Si el producto mismo es un servicio, agregarlo
            if product.type == 'service':
                services_dict[product.id]['quantity'] += qty_sold
                if not services_dict[product.id]['pos_line_id']:
                    services_dict[product.id]['pos_line_id'] = line.id
            
            # Buscar BoM del producto
            bom = self.env['mrp.bom']._bom_find(
                product=product,
                company_id=self.company_id.id,
                bom_type='normal'
            )
            
            if bom:
                # Extraer servicios de la BoM recursivamente
                services_from_bom = self._extract_services_from_bom_pos(
                    bom, qty_sold, line.id
                )
                
                # Acumular cantidades
                for service_id, data in services_from_bom.items():
                    services_dict[service_id]['quantity'] += data['quantity']
                    if not services_dict[service_id]['pos_line_id']:
                        services_dict[service_id]['pos_line_id'] = data['pos_line_id']
        
        return dict(services_dict)
    
    def _extract_services_from_bom_pos(self, bom, multiplier, pos_line_id):
        """
        Extraer servicios de una BoM recursivamente para POS
        
        Args:
            bom: mrp.bom record
            multiplier: cantidad a multiplicar (cantidad vendida)
            pos_line_id: ID de la línea de POS
        
        Returns:
            dict {product_id: {'quantity': float, 'pos_line_id': int}}
        """
        services_dict = defaultdict(lambda: {'quantity': 0.0, 'pos_line_id': pos_line_id})
        
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
                sub_services = self._extract_services_from_bom_pos(
                    sub_bom, total_qty, pos_line_id
                )
                
                # Acumular servicios de la sub-BoM
                for service_id, data in sub_services.items():
                    services_dict[service_id]['quantity'] += data['quantity']
        
        return dict(services_dict)