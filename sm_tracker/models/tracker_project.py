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
        ('delivered', 'Entregado'),
    ], string='Estado', default='pending', required=True, tracking=True)
    
    state_sequence = fields.Integer(
        string='Secuencia de Estado',
        compute='_compute_state_sequence',
        store=True,
        help='Secuencia para ordenar estados: Pendiente=1, Procesando=2, Entregado=3'
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
    
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company
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
            'delivered': 3,
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
                record.delay_days = delta.days
            elif record.state != 'delivered' and record.promise_date:
                today = fields.Datetime.now()
                if today > record.promise_date:
                    delta = today - record.promise_date
                    record.delay_days = delta.days
                else:
                    record.delay_days = 0
            else:
                record.delay_days = 0
    
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
        """Obtener movimientos de inventario pendientes (no done ni cancel)
        Filtrados: solo productos de familia tableros, excluye retazos"""
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
            
            # Filtrar movimientos pendientes (no done ni cancel)
            if pickings:
                for picking in pickings:
                    # Obtener movimientos que no estén done ni cancel
                    moves = picking.move_ids_without_package.filtered(
                        lambda m: m.state not in ['done', 'cancel'] and
                        # Filtrar solo productos de familia tableros
                        m.product_id.categ_id.name and 'tablero' in m.product_id.categ_id.name.lower() and
                        # Excluir retazos
                        'retazo' not in m.product_id.name.lower()
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
    
    def write(self, vals):
        if 'state' in vals:
            vals['state_changed_by'] = self.env.user.id
            vals['state_changed_date'] = fields.Datetime.now()
            
            if vals['state'] == 'delivered' and not self.delivery_date:
                vals['delivery_date'] = fields.Datetime.now()
        
        return super(TrackerProject, self).write(vals)
    
    def action_start_processing(self):
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_('Solo se puede procesar un proyecto pendiente.'))
        
        # Validar que tenga fecha prometida antes de iniciar
        if not self.promise_date:
            raise UserError(_('No se puede iniciar el proyecto sin una Fecha Prometida asignada.'))
        
        self.write({'state': 'processing'})
        return True
    
    def action_mark_delivered(self):
        self.ensure_one()
        if self.state != 'processing':
            raise UserError(_('Solo se puede entregar un proyecto en procesamiento.'))
        
        pending_tasks = self.task_ids.filtered(lambda t: t.state != 'done')
        if pending_tasks:
            raise UserError(_(
                'No se puede marcar como entregado. '
                'Aún hay %d tarea(s) pendiente(s).'
            ) % len(pending_tasks))
        
        self.write({
            'state': 'delivered',
            'delivery_date': fields.Datetime.now()
        })
        return True
        
        self.write({
            'state': 'delivered',
            'delivery_date': fields.Date.today()
        })
        return True
    
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