# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class TrackerTask(models.Model):
    _name = 'tracker.task'
    _description = 'Tarea Tracker'
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Número de Tarea',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('Nuevo')
    )
    
    project_id = fields.Many2one(
        'tracker.project',
        string='Proyecto',
        required=True,
        ondelete='cascade',
        readonly=True
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Servicio',
        required=True,
        readonly=True,
        domain=[('type', '=', 'service')]
    )
    
    sale_order_line_id = fields.Many2one(
        'sale.order.line',
        string='Línea de Venta',
        readonly=True
    )
    
    pos_order_line_id = fields.Many2one(
        'pos.order.line',
        string='Línea de POS',
        readonly=True
    )
    
    invoice_line_id = fields.Many2one(
        'account.move.line',
        string='Línea de Factura',
        readonly=True
    )
    
    quantity = fields.Float(
        string='Cantidad',
        required=True,
        readonly=True,
        help='Cantidad calculada desde BoM × Cantidad vendida'
    )
    
    operator_id = fields.Many2one(
        'res.users',
        string='Operario Asignado',
        tracking=True
    )
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('ready', 'Listo'),
        ('in_progress', 'En Proceso'),
        ('paused', 'Pausado'),
        ('done', 'Completado'),
        ('cancel', 'Cancelado'),
    ], string='Estado', default='draft', required=True, tracking=True)
    
    timesheet_ids = fields.One2many(
        'tracker.timesheet',
        'task_id',
        string='Registros de Tiempo',
        readonly=True
    )
    
    total_hours = fields.Float(
        string='Total de Horas',
        compute='_compute_total_hours',
        store=True
    )
    
    start_time = fields.Datetime(
        string='Inicio',
        readonly=True
    )
    
    end_time = fields.Datetime(
        string='Fin',
        readonly=True
    )
    
    started_by = fields.Many2one(
        'res.users',
        string='Iniciado por',
        readonly=True
    )
    
    paused_by = fields.Many2one(
        'res.users',
        string='Pausado por',
        readonly=True
    )
    
    completed_by = fields.Many2one(
        'res.users',
        string='Completado por',
        readonly=True
    )
    
    notes = fields.Text(string='Notas')
    
    @api.depends('timesheet_ids.duration')
    def _compute_total_hours(self):
        for task in self:
            task.total_hours = sum(task.timesheet_ids.mapped('duration'))
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nuevo')) == _('Nuevo'):
                vals['name'] = self.env['ir.sequence'].next_by_code('tracker.task') or _('Nuevo')
        return super(TrackerTask, self).create(vals_list)
    
    @api.onchange('operator_id')
    def _onchange_operator_id(self):
        """Cuando se asigna un operario, cambiar estado a 'ready'"""
        if self.operator_id and self.state == 'draft':
            self.state = 'ready'
    
    def write(self, vals):
        """Override write para manejar cambio de operario"""
        res = super(TrackerTask, self).write(vals)
        if 'operator_id' in vals:
            for task in self:
                if task.operator_id and task.state == 'draft':
                    task.state = 'ready'
        return res
    
    def action_start_task(self):
        """Iniciar tarea - Crea registro de timesheet automáticamente"""
        for task in self:
            # Validar que haya operario asignado
            if not task.operator_id:
                raise UserError(_(
                    'No se puede iniciar la tarea sin un operario asignado.'
                ))
            
            # Validar estado
            if task.state not in ['ready', 'paused']:
                raise UserError(_(
                    'Solo se pueden iniciar tareas en estado "Listo" o "Pausado".'
                ))
            
            # Crear registro de timesheet
            self.env['tracker.timesheet'].create({
                'task_id': task.id,
                'operator_id': task.operator_id.id,
                'start_time': fields.Datetime.now(),
                'user_id': self.env.user.id,
            })
            
            # Actualizar tarea
            task.write({
                'state': 'in_progress',
                'start_time': fields.Datetime.now() if not task.start_time else task.start_time,
                'started_by': self.env.user.id,
            })
            
            # Actualizar proyecto si está pendiente
            if task.project_id.state == 'pending':
                task.project_id.state = 'in_progress'
    
    def action_pause_task(self):
        """Pausar tarea - Detiene el timesheet activo"""
        for task in self:
            # Validar estado
            if task.state != 'in_progress':
                raise UserError(_(
                    'Solo se pueden pausar tareas que están en progreso.'
                ))
            
            # Buscar timesheet activo (sin end_time)
            active_timesheet = self.env['tracker.timesheet'].search([
                ('task_id', '=', task.id),
                ('end_time', '=', False)
            ], limit=1)
            
            if active_timesheet:
                active_timesheet.write({
                    'end_time': fields.Datetime.now(),
                })
            
            # Actualizar tarea
            task.write({
                'state': 'paused',
                'paused_by': self.env.user.id,
            })
    
    def action_complete_task(self):
        """Finalizar tarea - Detiene timesheet si hay uno activo"""
        for task in self:
            # Validar estado
            if task.state not in ['in_progress', 'paused']:
                raise UserError(_(
                    'Solo se pueden finalizar tareas en estado "En Proceso" o "Pausado".'
                ))
            
            # Buscar timesheet activo y detenerlo
            active_timesheet = self.env['tracker.timesheet'].search([
                ('task_id', '=', task.id),
                ('end_time', '=', False)
            ], limit=1)
            
            if active_timesheet:
                active_timesheet.write({
                    'end_time': fields.Datetime.now(),
                })
            
            # Actualizar tarea
            task.write({
                'state': 'done',
                'end_time': fields.Datetime.now(),
                'completed_by': self.env.user.id,
            })
    
    def action_cancel_task(self):
        """Cancelar tarea"""
        for task in self:
            # Detener timesheet activo si existe
            active_timesheet = self.env['tracker.timesheet'].search([
                ('task_id', '=', task.id),
                ('end_time', '=', False)
            ], limit=1)
            
            if active_timesheet:
                active_timesheet.write({
                    'end_time': fields.Datetime.now(),
                })
            
            task.write({'state': 'cancel'})
    
    def action_reset_to_draft(self):
        """Reiniciar tarea a borrador"""
        self.write({'state': 'draft'})