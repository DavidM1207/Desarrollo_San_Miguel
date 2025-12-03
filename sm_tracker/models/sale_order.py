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
    
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        
        for order in self:
            if not order.tracker_project_ids and order.analytic_account_id:
                # Buscar servicios en líneas de venta
                services = {}
                for line in order.order_line:
                    if line.product_id.type == 'service':
                        product = line.product_id
                        qty = line.product_uom_qty
                        if product.id in services:
                            services[product.id]['qty'] += qty
                        else:
                            services[product.id] = {'product': product, 'qty': qty}
                
                # Crear proyecto si hay servicios
                if services:
                    project = self.env['tracker.project'].create({
                        'sale_order_id': order.id,
                        'partner_id': order.partner_id.id,
                        'analytic_account_id': order.analytic_account_id.id,
                        'promise_date': order.commitment_date or fields.Date.today(),
                        'company_id': order.company_id.id,
                    })
                    
                    # Crear tareas
                    for service_data in services.values():
                        self.env['tracker.task'].create({
                            'project_id': project.id,
                            'product_id': service_data['product'].id,
                            'name': service_data['product'].name,
                            'quantity': service_data['qty'],
                            'analytic_account_id': order.analytic_account_id.id,
                            'company_id': order.company_id.id,
                        })
                    
                    _logger.info(f"Proyecto tracker {project.name} creado para venta {order.name}")
        
        return res