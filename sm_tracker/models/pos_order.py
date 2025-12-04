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
    
    @api.depends('lines.product_id', 'lines.qty')
    def _compute_has_service_products(self):
        """Detectar si la orden tiene productos de servicio"""
        for order in self:
            has_service = False
            _logger.info('=== VERIFICANDO SERVICIOS PARA POS %s ===', order.name or 'Nuevo')
            
            for line in order.lines:
                if not line.product_id:
                    continue
                    
                _logger.info('Línea: %s (tipo: %s, qty: %s)', 
                           line.product_id.name, 
                           line.product_id.type,
                           line.qty)
                
                # Verificar si es servicio directo
                if line.product_id.type == 'service':
                    _logger.info('  -> SERVICIO DIRECTO encontrado: %s', line.product_id.name)
                    has_service = True
                    break
                
                # Verificar si tiene servicios en BoM
                if self._check_bom_for_services(line.product_id):
                    _logger.info('  -> SERVICIO EN BOM encontrado para: %s', line.product_id.name)
                    has_service = True
                    break
            
            order.has_service_products = has_service
            _logger.info('Resultado has_service_products para %s: %s', 
                       order.name or 'Nuevo', has_service)
    
    def _check_bom_for_services(self, product):
        """Verificar recursivamente si un producto tiene servicios en su BoM"""
        bom = self.env['mrp.bom'].search([
            ('product_tmpl_id', '=', product.product_tmpl_id.id)
        ], limit=1)
        
        if not bom:
            return False
        
        _logger.debug('  BoM encontrado para %s con %d líneas', product.name, len(bom.bom_line_ids))
        
        for line in bom.bom_line_ids:
            if line.product_id.type == 'service':
                _logger.debug('    -> Componente SERVICIO: %s', line.product_id.name)
                return True
            
            if self._check_bom_for_services(line.product_id):
                return True
        
        return False
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create para generar tracker después de crear la orden"""
        orders = super(PosOrder, self).create(vals_list)
        
        _logger.info('=== POS CREATE: %d órdenes creadas ===', len(orders))
        
        for order in orders:
            _logger.info('Orden POS creada: %s, Estado: %s, Has Services: %s', 
                       order.name, order.state, order.has_service_products)
            
            # Intentar crear tracker si aplica
            self._try_create_tracker(order)
        
        return orders
    
    def write(self, vals):
        """Override write para crear tracker cuando cambia el estado"""
        # Guardar estados anteriores
        old_states = {order.id: order.state for order in self}
        
        res = super(PosOrder, self).write(vals)
        
        # Si cambió el estado, verificar si necesita tracker
        if 'state' in vals:
            _logger.info('=== POS WRITE: Estado cambió a %s para %d órdenes ===', 
                       vals.get('state'), len(self))
            
            for order in self:
                old_state = old_states.get(order.id)
                _logger.info('Orden %s: %s -> %s', order.name, old_state, order.state)
                self._try_create_tracker(order)
        
        return res
    
    def _try_create_tracker(self, order):
        """Intentar crear tracker para una orden si cumple las condiciones"""
        # Validar que tenga servicios
        if not order.has_service_products:
            _logger.debug('Orden %s no tiene servicios, skip tracker', order.name)
            return False
        
        # Validar que no tenga tracker ya creado
        if order.tracker_project_ids:
            _logger.debug('Orden %s ya tiene tracker, skip', order.name)
            return False
        
        # Validar estado - crear tracker cuando la orden esté pagada o completada
        if order.state not in ['paid', 'done', 'invoiced']:
            _logger.debug('Orden %s en estado %s, esperando paid/done/invoiced', 
                        order.name, order.state)
            return False
        
        # Intentar crear el tracker
        _logger.info('>>> CREANDO TRACKER para orden POS %s <<<', order.name)
        try:
            return order._auto_create_tracker_project()
        except Exception as e:
            _logger.error('ERROR al crear tracker para POS %s: %s', order.name, str(e), exc_info=True)
            return False
    
    def _auto_create_tracker_project(self):
        """Crear proyecto tracker automáticamente desde orden POS"""
        self.ensure_one()
        
        _logger.info('=== CREANDO TRACKER PROJECT PARA %s ===', self.name)
        
        # Buscar cuenta analítica
        analytic_account = self._get_analytic_account()
        
        if not analytic_account:
            _logger.warning('❌ No se pudo crear tracker para POS %s: No hay cuenta analítica', self.name)
            return False
        
        _logger.info('✓ Cuenta analítica: %s', analytic_account.name)
        
        # Determinar partner
        partner = self.partner_id if self.partner_id else self.env.ref('base.public_partner')
        _logger.info('✓ Partner: %s', partner.name)
        
        # Determinar usuario responsable
        user_id = self.user_id.id if self.user_id else self.env.user.id
        _logger.info('✓ Usuario responsable: %s', self.env['res.users'].browse(user_id).name)
        
        # Obtener referencia correcta de POS
        pos_reference = self.pos_reference if hasattr(self, 'pos_reference') and self.pos_reference else self.name
        _logger.info('✓ Referencia POS: %s', pos_reference)
        
        # Crear proyecto SIN fecha prometida
        project_vals = {
            'pos_order_id': self.id,
            'partner_id': partner.id,
            'analytic_account_id': analytic_account.id,
            'user_id': user_id,
        }
        
        _logger.info('Valores del proyecto: %s', project_vals)
        project = self.env['tracker.project'].create(project_vals)
        _logger.info('✓✓✓ Proyecto tracker %s CREADO para POS %s (sin fecha prometida)', project.name, pos_reference)
        
        # Obtener servicios
        service_products = self._get_service_products_from_bom()
        
        if not service_products:
            _logger.warning('⚠ No se encontraron servicios específicos en POS %s', pos_reference)
            return project
        
        # Crear tareas
        _logger.info('Creando %d tarea(s)...', len(service_products))
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
            _logger.info('  ✓ Tarea creada: %s (qty: %s)', product.name, qty)
        
        _logger.info('=== TRACKER CREATION COMPLETADO ===')
        return project
    
    def _get_analytic_account(self):
        """Buscar cuenta analítica para el tracker - PRIORIDAD: sh_pos_order_analytic_account"""
        analytic_account = False
        
        # PRIORIDAD 1: Campo sh_pos_order_analytic_account (módulo Softhealer)
        if hasattr(self, 'sh_pos_order_analytic_account') and self.sh_pos_order_analytic_account:
            analytic_account = self.sh_pos_order_analytic_account
            _logger.info('✓ Cuenta analítica encontrada en sh_pos_order_analytic_account: %s', analytic_account.name)
            return analytic_account
        
        # PRIORIDAD 2: Desde la configuración del POS (campo personalizado)
        if self.session_id and self.session_id.config_id:
            config = self.session_id.config_id
            _logger.info('Buscando cuenta analítica en config POS: %s', config.name)
            
            if hasattr(config, 'analytic_account_id') and config.analytic_account_id:
                analytic_account = config.analytic_account_id
                _logger.info('  -> Encontrada en config.analytic_account_id: %s', analytic_account.name)
                return analytic_account
        
        # PRIORIDAD 3: Desde las líneas de la orden
        _logger.info('Buscando cuenta analítica en líneas de orden...')
        for line in self.lines:
            # Buscar en account_analytic_line o similar
            if hasattr(line, 'analytic_account_id') and line.analytic_account_id:
                analytic_account = line.analytic_account_id
                _logger.info('  -> Encontrada en línea: %s', analytic_account.name)
                return analytic_account
        
        # PRIORIDAD 4: Buscar cuenta analítica por nombre del POS
        if self.session_id and self.session_id.config_id:
            _logger.info('Buscando cuenta analítica por nombre del POS...')
            config_name = self.session_id.config_id.name
            analytic_account = self.env['account.analytic.account'].search([
                ('name', 'ilike', config_name)
            ], limit=1)
            
            if analytic_account:
                _logger.info('  -> Encontrada por nombre: %s', analytic_account.name)
                return analytic_account
        
        # PRIORIDAD 5: Buscar cualquier cuenta analítica activa con "POS" o "TIENDA"
        _logger.info('Buscando cuenta analítica genérica...')
        analytic_account = self.env['account.analytic.account'].search([
            '|', '|',
            ('name', 'ilike', 'POS'),
            ('name', 'ilike', 'TIENDA'),
            ('name', 'ilike', 'PUNTO')
        ], limit=1)
        
        if analytic_account:
            _logger.info('  -> Encontrada cuenta genérica: %s', analytic_account.name)
            return analytic_account
        
        # PRIORIDAD 6: Tomar la primera cuenta analítica disponible
        _logger.info('Buscando primera cuenta analítica disponible...')
        analytic_account = self.env['account.analytic.account'].search([], limit=1)
        
        if analytic_account:
            _logger.info('  -> Usando primera disponible: %s', analytic_account.name)
        else:
            _logger.warning('  -> NO SE ENCONTRÓ NINGUNA CUENTA ANALÍTICA')
        
        return analytic_account
    
    def _get_service_products_from_bom(self):
        """Obtener productos de servicio de la orden POS y sus BoMs recursivamente"""
        self.ensure_one()
        service_products = {}
        
        pos_reference = self.pos_reference if hasattr(self, 'pos_reference') and self.pos_reference else self.name
        _logger.info('=== EXTRAYENDO SERVICIOS DE LA ORDEN %s ===', pos_reference)
        
        def process_bom_recursive(product, qty, level=0):
            indent = "  " * level
            bom = self.env['mrp.bom'].search([
                ('product_tmpl_id', '=', product.product_tmpl_id.id),
            ], limit=1)
            
            if bom:
                _logger.info('%sBoM encontrado para %s (%d componentes)', 
                           indent, product.name, len(bom.bom_line_ids))
                
                for line in bom.bom_line_ids:
                    component = line.product_id
                    component_qty = qty * line.product_qty
                    
                    _logger.info('%s  -> %s (tipo: %s, qty: %s)', 
                               indent, component.name, component.type, component_qty)
                    
                    if component.type == 'service':
                        _logger.info('%s     ✓ SERVICIO AGREGADO', indent)
                        if component in service_products:
                            service_products[component] += component_qty
                        else:
                            service_products[component] = component_qty
                    else:
                        # Procesar recursivamente
                        process_bom_recursive(component, component_qty, level + 1)
            else:
                # No tiene BoM, verificar si es servicio directo
                if product.type == 'service':
                    _logger.info('%sServicio directo: %s (qty: %s)', indent, product.name, qty)
                    if product in service_products:
                        service_products[product] += qty
                    else:
                        service_products[product] = qty
        
        # Procesar cada línea de la orden
        for line in self.lines:
            if line.product_id:
                _logger.info('Procesando línea: %s (qty: %s)', line.product_id.name, line.qty)
                process_bom_recursive(line.product_id, line.qty)
        
        _logger.info('=== SERVICIOS ENCONTRADOS: %d ===', len(service_products))
        for product, qty in service_products.items():
            _logger.info('  - %s: %s', product.name, qty)
        
        return service_products