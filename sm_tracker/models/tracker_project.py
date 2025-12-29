# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class TrackerProject(models.Model):
    _name = 'tracker.project'
    _description = 'Proyecto de Seguimiento'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'promise_date desc, id desc'

    name = fields.Char(
        string='Referencia',
        required=True,
        copy=False,
        readonly=True,
        default='Nuevo',
        tracking=True
    )
    
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Orden de Venta',
        tracking=True,
        readonly=True,
        help='Orden de venta origen del proyecto'
    )
    
    pos_order_id = fields.Many2one(
        'pos.order',
        string='Orden POS',
        tracking=True,
        readonly=True,
        help='Orden del punto de venta origen del proyecto'
    )
    
    order_reference = fields.Char(
        string='Ref. Orden',
        compute='_compute_order_reference',
        store=True,
        help='Referencia de la orden de origen (Venta o POS)'
    )
    
    origen_type = fields.Char(
        string='Origen',
        compute='_compute_origen_type',
        store=True
    )
    
    invoice_ids = fields.Many2many(
        'account.move',
        'tracker_project_invoice_rel',
        'project_id',
        'invoice_id',
        string='Facturas',
        domain=[('move_type', '=', 'out_invoice')],
        tracking=True
    )
    
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Tienda',
        required=True,
        tracking=True,
        help='Cuenta analítica de la tienda donde se genera el proyecto'
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=True,
        tracking=True,
        readonly=True
    )
    
    promise_date = fields.Datetime(
        string='Fecha Prometida',
        required=False,
        tracking=True,
        help='Fecha y hora en que se prometió la entrega al cliente'
    )
    
    delivery_date = fields.Datetime(
        string='Fecha de Entrega',
        tracking=True,
        readonly=True,
        help='Fecha y hora real de entrega del proyecto'
    )
    
    own_transport = fields.Boolean(
        string='Entrega con Transporte Propio',
        default=False,
        tracking=True,
        help='Marcar si el proyecto se entregó con transporte propio'
    )
    
    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('processing', 'Procesando'),
        ('pending_delivery', 'Pendiente de Entrega'),
        ('cancel', 'Anulado'),
        ('delivered', 'Entregado'),
    ], string='Estado', default='pending', required=True, tracking=True)
    
    state_sequence = fields.Integer(
        string='Secuencia de Estado',
        compute='_compute_state_sequence',
        store=True,
        help='Secuencia para ordenar estados: Pendiente=1, Procesando=2, Pendiente Entrega=3, Entregado=4, Anulado=5'
    )
    
    completion_date = fields.Datetime(
        string='Fecha de Finalización',
        readonly=True,
        tracking=True,
        help='Fecha en que todas las tareas fueron completadas'
    )
    
    cancellation_reason = fields.Text(
        string='Motivo de Anulación',
        readonly=True,
        tracking=True,
        help='Razón por la cual se anuló el proyecto'
    )
    
    task_ids = fields.One2many(
        'tracker.task',
        'project_id',
        string='Tareas de Servicio'
    )
    
    pending_stock_move_ids = fields.Many2many(
        'stock.move',
        string='Movimientos Pendientes',
        compute='_compute_pending_stock_moves',
        help='Movimientos de inventario pendientes (no done ni cancel)'
    )
    
    has_waiting_stock = fields.Boolean(
        string='Tiene productos en espera',
        compute='_compute_has_waiting_stock',
        store=True,
        help='Indica si hay movimientos en estado waiting (esperando disponibilidad)'
    )
    
    task_count = fields.Integer(
        string='Total Tareas',
        compute='_compute_task_count',
        store=True
    )
    
    total_hours = fields.Float(
        string='Horas Totales',
        compute='_compute_total_hours',
        store=True,
        help='Total de horas trabajadas en todas las tareas'
    )
    
    delay_days = fields.Integer(
        string='Días de Retraso',
        compute='_compute_delay_days',
        store=True,
        help='Días de diferencia entre fecha prometida y entregada'
    )
    
    hours_unassigned = fields.Float(
        string='Horas sin Asignar',
        compute='_compute_hours_unassigned',
        store=True,
        help='Horas transcurridas desde la creación hasta que se asignó fecha promesa'
    )
    
    progress = fields.Float(
        string='Progreso (%)',
        compute='_compute_progress',
        store=True
    )
    
    all_tasks_done = fields.Boolean(
        string='Todas las Tareas Completadas',
        compute='_compute_all_tasks_done',
        help='Indica si todas las tareas están en estado Done'
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='Responsable',
        default=lambda self: self.env.user,
        tracking=True,
        domain="[('employee_id.tracker_analytic_account_responsable_ids', 'in', [analytic_account_id])]"
    )
    
    notes = fields.Text(string='Notas')
    
    is_despacho_host = fields.Boolean(
        string='Despacho Host',
        compute='_compute_is_despacho_host',
        store=True,
        help='Indica si el proyecto contiene servicios de despacho host'
    )
    
    is_cnc = fields.Boolean(
        string='CNC',
        compute='_compute_is_cnc',
        store=True,
        help='Indica si el proyecto contiene servicios de CNC'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company
    )
    
    previous_analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Tienda Anterior',
        readonly=True,
        help='Tienda anterior antes del último cambio'
    )
    
    store_change_reason = fields.Text(
        string='Razón del Cambio de Tienda',
        readonly=True,
        help='Razón del último cambio de tienda'
    )
    
    store_change_history = fields.Text(
        string='Historial de Cambios de Tienda',
        readonly=True,
        help='Historial completo de cambios de tienda'
    )
    
    state_changed_by = fields.Many2one(
        'res.users',
        string='Estado Cambiado Por',
        readonly=True
    )
    
    state_changed_date = fields.Datetime(
        string='Fecha Cambio Estado',
        readonly=True
    )
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'Nuevo') == 'Nuevo':
            vals['name'] = self.env['ir.sequence'].next_by_code('tracker.project') or 'Nuevo'
        return super(TrackerProject, self).create(vals)
    
    @api.onchange('promise_date')
    def _onchange_promise_date(self):
        """Validar fecha promesa en tiempo real cuando el usuario la cambia"""
        if self.promise_date:
            # Validar que la fecha promesa no sea anterior a la creación
            if self.create_date:
                promise_date_only = fields.Date.to_date(self.promise_date)
                create_date_only = fields.Date.to_date(self.create_date)
                if promise_date_only < create_date_only:
                    return {
                        'warning': {
                            'title': _('Fecha Prometida Inválida'),
                            'message': _(
                                'La Fecha Prometida (%s) no puede ser anterior a la fecha de creación del proyecto (%s).'
                            ) % (promise_date_only.strftime('%d/%m/%Y'), create_date_only.strftime('%d/%m/%Y'))
                        }
                    }
            
            # Validar que la fecha promesa tenga hora específica (no solo fecha)
            promise_time = self.promise_date.time()
            if promise_time.hour == 0 and promise_time.minute == 0 and promise_time.second == 0:
                return {
                    'warning': {
                        'title': _('Hora Requerida'),
                        'message': _(
                            'La Fecha Prometida debe incluir una hora específica (no solo la fecha). '
                            'Por favor, ingrese la hora de entrega prometida al cliente.'
                        )
                    }
                }
    
    @api.constrains('promise_date')
    def _check_promise_date(self):
        """Validar que la fecha promesa no sea anterior a la creación (validación al guardar)"""
        for record in self:
            if record.promise_date and record.create_date:
                # Comparar solo las fechas (sin hora)
                promise_date_only = fields.Date.to_date(record.promise_date)
                create_date_only = fields.Date.to_date(record.create_date)
                if promise_date_only < create_date_only:
                    raise ValidationError(_(
                        'La Fecha Prometida (%s) no puede ser anterior a la fecha de creación del proyecto (%s).'
                    ) % (promise_date_only.strftime('%d/%m/%Y'), create_date_only.strftime('%d/%m/%Y')))
            
            # Validar que la fecha promesa tenga hora específica (no solo fecha)
            if record.promise_date:
                promise_time = record.promise_date.time()
                if promise_time.hour == 0 and promise_time.minute == 0 and promise_time.second == 0:
                    raise ValidationError(_(
                        'La Fecha Prometida debe incluir una hora específica (no solo la fecha). '
                        'Por favor, ingrese la hora de entrega prometida al cliente.'
                    ))
    
    @api.constrains('user_id', 'state', 'task_ids')
    def _check_responsable_assignment(self):
        """Validar que no se asigne responsable si no se han finalizado servicios"""
        for record in self:
            # Permitir asignar responsable en estado pending (al crear)
            if record.state == 'pending':
                continue
                
            # Si hay cambio de responsable y hay tareas sin finalizar
            if record.user_id and record.task_ids:
                incomplete_tasks = record.task_ids.filtered(lambda t: t.state != 'done')
                if incomplete_tasks:
                    # Verificar si es un cambio de responsable (no asignación inicial)
                    if self._origin.user_id and self._origin.user_id != record.user_id:
                        raise ValidationError(_(
                            'No se puede cambiar el responsable del proyecto mientras haya servicios sin finalizar. '
                            'Complete todas las tareas antes de cambiar el responsable.'
                        ))
    
    def write(self, vals):
        """Validar que el responsable no se pueda modificar una vez asignado
        y manejar cambio de estado a 'Sin Iniciar' cuando se asigna fecha promesa
        y validar cambio de tienda con permiso especial"""
        
        for record in self:
            # Si se intenta cambiar el responsable y ya tenía uno asignado
            if 'user_id' in vals and record.user_id and vals.get('user_id') != record.user_id.id:
                # Verificar si el usuario tiene permiso especial
                if not self.env.user.has_group('sm_tracker.group_tracker_manager'):
                    raise ValidationError(_(
                        'No se puede modificar el responsable del proyecto una vez asignado. '
                        'Solo los gerentes tienen permiso para cambiar el responsable.'
                    ))
            
            # Si se intenta cambiar la tienda
            if 'analytic_account_id' in vals and record.analytic_account_id and vals.get('analytic_account_id') != record.analytic_account_id.id:
                # Verificar si el usuario tiene permiso especial
                if not self.env.user.has_group('sm_tracker.group_tracker_change_store'):
                    raise ValidationError(_(
                        'No tiene permiso para cambiar la tienda del proyecto. '
                        'Contacte a un supervisor para solicitar este permiso.'
                    ))
                
                # Obtener la nueva tienda
                new_store = self.env['account.analytic.account'].browse(vals.get('analytic_account_id'))
                
                # Abrir wizard para pedir razón del cambio
                return {
                    'name': _('Cambio de Tienda'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'tracker.project.change.store.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'default_project_id': record.id,
                        'default_old_store_id': record.analytic_account_id.id,
                        'default_new_store_id': vals.get('analytic_account_id'),
                    }
                }
        
        return super(TrackerProject, self).write(vals)
    
    @api.depends('task_ids')
    def _compute_task_count(self):
        for record in self:
            record.task_count = len(record.task_ids)
    
    @api.depends('state')
    def _compute_state_sequence(self):
        """Asignar secuencia numérica para ordenar estados correctamente en kanban"""
        state_order = {
            'pending': 1,
            'processing': 2,
            'pending_delivery': 3,
            'delivered': 4,
            'cancel': 5,
        }
        for record in self:
            record.state_sequence = state_order.get(record.state, 99)
    
    @api.depends('task_ids.total_hours')
    def _compute_total_hours(self):
        for record in self:
            record.total_hours = sum(record.task_ids.mapped('total_hours'))
    
    @api.depends('promise_date', 'delivery_date', 'state')
    def _compute_delay_days(self):
        for record in self:
            if record.state == 'delivered' and record.promise_date and record.delivery_date:
                delta = record.delivery_date - record.promise_date
                # Si se entregó antes (negativo), mostrar 0
                # Si se entregó después (positivo), mostrar los días de retraso
                record.delay_days = max(0, delta.days)
            elif record.state != 'delivered' and record.promise_date:
                today = fields.Datetime.now()
                if today > record.promise_date:
                    delta = today - record.promise_date
                    record.delay_days = delta.days
                else:
                    record.delay_days = 0
            else:
                record.delay_days = 0
    
    @api.depends('promise_date', 'create_date')
    @api.depends('promise_date', 'create_date')
    def _compute_hours_unassigned(self):
        """Calcular horas desde creación hasta asignación de fecha promesa"""
        for record in self:
            if not record.create_date:
                record.hours_unassigned = 0.0
                continue
            
            # Si NO tiene fecha promesa: calcular tiempo transcurrido desde creación hasta ahora
            if not record.promise_date:
                now = fields.Datetime.now()
                delta = now - record.create_date
                record.hours_unassigned = delta.total_seconds() / 3600.0
            else:
                # Si YA tiene fecha promesa: mostrar 0 (ya fue asignado)
                record.hours_unassigned = 0.0
    
    @api.depends('task_ids.state')
    def _compute_progress(self):
        for record in self:
            if record.task_ids:
                total_tasks = len(record.task_ids)
                completed_tasks = len(record.task_ids.filtered(lambda t: t.state == 'done'))
                record.progress = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
            else:
                record.progress = 0
    
    @api.depends('task_ids.state')
    def _compute_all_tasks_done(self):
        """Verificar si todas las tareas están completadas"""
        for record in self:
            if not record.task_ids:
                record.all_tasks_done = False
            else:
                pending_tasks = record.task_ids.filtered(lambda t: t.state != 'done')
                record.all_tasks_done = len(pending_tasks) == 0
    
    @api.depends('sale_order_id', 'pos_order_id')
    def _compute_order_reference(self):
        """Obtener referencia de la orden origen (Venta o POS)"""
        for record in self:
            if record.pos_order_id:
                # Intentar obtener pos_reference, si no existe usar name
                if hasattr(record.pos_order_id, 'pos_reference') and record.pos_order_id.pos_reference:
                    record.order_reference = record.pos_order_id.pos_reference
                else:
                    record.order_reference = record.pos_order_id.name
            elif record.sale_order_id:
                record.order_reference = record.sale_order_id.name
            else:
                record.order_reference = 'Manual'
    
    @api.depends('sale_order_id', 'pos_order_id')
    def _compute_origen_type(self):
        """Determinar el tipo de origen del proyecto"""
        for record in self:
            if record.sale_order_id:
                record.origen_type = 'Venta'
            elif record.pos_order_id:
                record.origen_type = 'POS'
            else:
                record.origen_type = 'Manual'
    
    @api.depends('sale_order_id', 'sale_order_id.picking_ids', 'pos_order_id', 'pos_order_id.picking_ids')
    def _compute_pending_stock_moves(self):
        """Obtener movimientos en estado 'confirmed' (En espera de disponibilidad) sin BoM
        Solo productos que se COMPRAN, no los que se FABRICAN"""
        for record in self:
            pending_moves = self.env['stock.move']
            
            # Obtener pickings de la venta
            if record.sale_order_id:
                pickings = record.sale_order_id.picking_ids
            # Obtener pickings del POS
            elif record.pos_order_id:
                pickings = record.pos_order_id.picking_ids
            else:
                pickings = self.env['stock.picking']
            
            # Filtrar movimientos en confirmed sin lista de materiales
            if pickings:
                for picking in pickings:
                    # Solo productos en estado 'confirmed' y sin BoM (lista de materiales)
                    moves = picking.move_ids_without_package.filtered(
                        lambda m: m.state == 'confirmed' and 
                        not m.product_id.product_tmpl_id.bom_ids
                    )
                    pending_moves |= moves
            
            record.pending_stock_move_ids = pending_moves
    
    @api.depends('sale_order_id', 'sale_order_id.picking_ids', 'sale_order_id.picking_ids.move_ids_without_package',
                 'sale_order_id.picking_ids.move_ids_without_package.state',
                 'pos_order_id', 'pos_order_id.picking_ids', 'pos_order_id.picking_ids.move_ids_without_package',
                 'pos_order_id.picking_ids.move_ids_without_package.state')
    def _compute_has_waiting_stock(self):
        """Verificar si hay movimientos en estado waiting (esperando disponibilidad)"""
        for record in self:
            has_waiting = False
            
            # Obtener pickings de la venta o POS
            if record.sale_order_id:
                pickings = record.sale_order_id.picking_ids
            elif record.pos_order_id:
                pickings = record.pos_order_id.picking_ids
            else:
                pickings = self.env['stock.picking']
            
            # Verificar si hay algún movimiento en estado waiting
            if pickings:
                for picking in pickings:
                    waiting_moves = picking.move_ids_without_package.filtered(
                        lambda m: m.state == 'waiting'
                    )
                    if waiting_moves:
                        has_waiting = True
                        break
            
            record.has_waiting_stock = has_waiting
    
    @api.depends('task_ids.product_id')
    def _compute_is_despacho_host(self):
        """Determinar si el proyecto contiene servicios de despacho host"""
        # Códigos de referencia interna de los servicios de despacho host
        DESPACHO_HOST_CODES = [
            'CORTES',
            'CORTESEXTERNOS', 
            'PEGADOCANTO',
            'PEGADOCANTO2',
            'PEGADOCANTOEXTERNO',
            'S-024'
        ]
        
        for record in self:
            is_despacho = False
            
            # Verificar si alguna tarea tiene un producto con esos códigos
            for task in record.task_ids:
                if task.product_id and task.product_id.default_code in DESPACHO_HOST_CODES:
                    is_despacho = True
                    break
            
            record.is_despacho_host = is_despacho
    
    @api.depends('task_ids.product_id')
    def _compute_is_cnc(self):
        """Determinar si el proyecto contiene servicios de CNC"""
        for record in self:
            is_cnc = False
            
            # Verificar si alguna tarea tiene un producto que contenga "CNC" en el nombre
            for task in record.task_ids:
                if task.product_id and task.product_id.name and 'CNC' in task.product_id.name.upper():
                    is_cnc = True
                    break
            
            record.is_cnc = is_cnc
    
    def write(self, vals):
        if 'state' in vals:
            vals['state_changed_by'] = self.env.user.id
            vals['state_changed_date'] = fields.Datetime.now()
            
            if vals['state'] == 'delivered' and not self.delivery_date:
                vals['delivery_date'] = fields.Datetime.now()
        
        return super(TrackerProject, self).write(vals)
    
    def action_start_processing(self):
        self.ensure_one()
        if self.state not in ['pending', 'cancel']:
            raise UserError(_('Solo se puede procesar un proyecto pendiente.'))
        
        # Validar que tenga fecha prometida antes de iniciar
        if not self.promise_date:
            raise UserError(_('No se puede iniciar el proyecto sin una Fecha Prometida asignada.'))
        
        self.write({'state': 'processing'})
        return True
    
    def action_mark_delivered(self):
        self.ensure_one()
        if self.state != 'pending_delivery':
            raise UserError(_('Solo se puede entregar un proyecto pendiente de entrega.'))
        
        # Validar que tenga responsable asignado antes de entregar
        if not self.user_id:
            raise UserError(_(
                'Debe asignar un responsable al proyecto antes de marcarlo como entregado. '
                'Por favor, asigne un responsable en el campo "Responsable" y vuelva a intentar.'
            ))
        
        self.write({
            'state': 'delivered',
            'delivery_date': fields.Datetime.now()
        })
        return True
    
    def action_cancel_project(self):
        """Abrir wizard para anular proyecto con motivo"""
        self.ensure_one()
        if self.state == 'delivered':
            raise UserError(_('No se puede anular un proyecto ya entregado.'))
        
        return {
            'name': _('Anular Proyecto'),
            'type': 'ir.actions.act_window',
            'res_model': 'tracker.project.cancel.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_project_id': self.id,
            }
        }
        # return {
        #     'name': _('Anular Proyecto'),
        #     'type': 'ir.actions.act_window',
        #     'res_model': 'tracker.project.cancel.wizard',
        #     'view_mode': 'form',
        #     'target': 'new',
        #     'context': {'default_project_id': self.id}
        # }
    
    
    def action_view_tasks(self):
        self.ensure_one()
        return {
            'name': _('Tareas de %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'tracker.task',
            'view_mode': 'tree,form,kanban',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }