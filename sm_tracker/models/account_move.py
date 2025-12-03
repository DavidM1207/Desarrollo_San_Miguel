# -*- coding: utf-8 -*-

from odoo import models, api, _
from odoo.exceptions import UserError
from collections import defaultdict


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    def action_post(self):
        """Override para generar proyecto tracker automáticamente al validar factura"""
        # Llamar al método original
        res = super(AccountMove, self).action_post()
        
        # Verificar que el módulo tracker esté instalado
        if 'tracker.project' not in self.env:
            return res
        
        # Generar proyecto tracker solo para facturas de cliente
        for move in self:
            if move.move_type == 'out_invoice' and move.state == 'posted':
                # Buscar si ya existe un proyecto para esta factura
                existing_project = self.env['tracker.project'].search([
                    ('invoice_id', '=', move.id)
                ], limit=1)
                
                # Solo generar si hay cuenta analítica y no existe ya un proyecto
                if move.invoice_line_ids and not existing_project:
                    # Verificar si alguna línea tiene cuenta analítica
                    has_analytic = any(line.analytic_distribution for line in move.invoice_line_ids)
                    if has_analytic:
                        move._generate_tracker_project_invoice()
        
        return res
    
    def _generate_tracker_project_invoice(self):
        """Generar proyecto tracker con sus tareas desde BoMs para facturas"""
        self.ensure_one()
        
        # Obtener cuenta analítica de la primera línea que la tenga
        analytic_account = None
        for line in self.invoice_line_ids:
            if line.analytic_distribution:
                # analytic_distribution es un dict tipo {account_id: percentage}
                # Tomamos la primera cuenta analítica
                analytic_account_id = int(list(line.analytic_distribution.keys())[0])
                analytic_account = self.env['account.analytic.account'].browse(analytic_account_id)
                break
        
        if not analytic_account:
            # No hay cuenta analítica, no generar proyecto
            return
        
        # Extraer servicios de las líneas de factura y sus BoMs
        services_data = self._extract_services_from_boms_invoice()
        
        if not services_data:
            # No hay servicios para procesar
            return
        
        # Crear proyecto tracker
        project_vals = {
            'invoice_id': self.id,
            'analytic_account_id': analytic_account.id,
            'user_id': self.invoice_user_id.id if self.invoice_user_id else self.env.user.id,
            'state': 'pending',
        }
        
        tracker_project = self.env['tracker.project'].create(project_vals)
        
        # Crear tareas para cada servicio
        for service_id, data in services_data.items():
            task_vals = {
                'project_id': tracker_project.id,
                'product_id': service_id,
                'quantity': data['quantity'],
                'invoice_line_id': data.get('invoice_line_id'),
                'state': 'draft',
            }
            self.env['tracker.task'].create(task_vals)
        
        return tracker_project
    
    def _extract_services_from_boms_invoice(self):
        """
        Extraer servicios desde BoMs recursivamente y acumular cantidades para facturas
        Retorna: dict {product_id: {'quantity': float, 'invoice_line_id': int}}
        """
        services_dict = defaultdict(lambda: {'quantity': 0.0, 'invoice_line_id': False})
        
        for line in self.invoice_line_ids:
            # Solo procesar líneas de productos (no secciones, notas, etc)
            if not line.product_id:
                continue
                
            product = line.product_id
            qty_invoiced = line.quantity
            
            # Si el producto mismo es un servicio, agregarlo
            if product.type == 'service':
                services_dict[product.id]['quantity'] += qty_invoiced
                if not services_dict[product.id]['invoice_line_id']:
                    services_dict[product.id]['invoice_line_id'] = line.id
            
            # Buscar BoM del producto
            bom = self.env['mrp.bom']._bom_find(
                product=product,
                company_id=self.company_id.id,
                bom_type='normal'
            )
            
            if bom:
                # Extraer servicios de la BoM recursivamente
                services_from_bom = self._extract_services_from_bom_invoice(
                    bom, qty_invoiced, line.id
                )
                
                # Acumular cantidades
                for service_id, data in services_from_bom.items():
                    services_dict[service_id]['quantity'] += data['quantity']
                    if not services_dict[service_id]['invoice_line_id']:
                        services_dict[service_id]['invoice_line_id'] = data['invoice_line_id']
        
        return dict(services_dict)
    
    def _extract_services_from_bom_invoice(self, bom, multiplier, invoice_line_id):
        """
        Extraer servicios de una BoM recursivamente para facturas
        
        Args:
            bom: mrp.bom record
            multiplier: cantidad a multiplicar (cantidad facturada)
            invoice_line_id: ID de la línea de factura
        
        Returns:
            dict {product_id: {'quantity': float, 'invoice_line_id': int}}
        """
        services_dict = defaultdict(lambda: {'quantity': 0.0, 'invoice_line_id': invoice_line_id})
        
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
                sub_services = self._extract_services_from_bom_invoice(
                    sub_bom, total_qty, invoice_line_id
                )
                
                # Acumular servicios de la sub-BoM
                for service_id, data in sub_services.items():
                    services_dict[service_id]['quantity'] += data['quantity']
        
        return dict(services_dict)