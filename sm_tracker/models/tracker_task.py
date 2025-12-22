# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class TrackerTask(models.Model):
    _name = 'tracker.task'
    _description = 'Tarea de Servicio'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id'

    name = fields.Char(
        string='Descripción',
        required=True,
        tracking=True
    )
    
    project_id = fields.Many2one(
        'tracker.project',
        string='Proyecto',
        required=True,
        ondelete='cascade',
        tracking=True
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Servicio',
        required=True,
        domain=[('type', '=', 'service')],
        tracking=True,
        readonly=True
    )
    
    quantity = fields.Float(
        string='Cantidad',
        default=1.0,
        tracking=True,
        readonly=True,
        help='Cantidad de servicios a realizar'
    )
    
    quantity_done = fields.Float(
        string='Cantidad Realizada',
        default=0.0,
        tracking=True,
        help='Cantidad de servicios ya completados'
    )
    
    quantity_remaining = fields.Float(
        string='Cantidad Restante',
        compute='_compute_quantity_remaining',
        store=True,
        help='Cantidad pendiente de realizar'
    )
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Operario Asignado',
        tracking=True,
        domain="['&', ('tracker_analytic_account_operario_ids', 'in', [analytic_account_id]), ('tracker_product_ids', 'in', [product_id])]",
        help='Empleado responsable de ejecutar esta tarea. Debe tener la tienda y el servicio asignados.'
    )
    
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Tienda',
        required=True,
        tracking=True
    )
    
    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('ready', 'Listo'),
        ('in_progress', 'En Progreso'),
        ('paused', 'Pausado'),
        ('done', 'Terminado'),
        ('cancel', 'Cancelado'),
    ], string='Estado', default='pending', required=True, tracking=True)
    
    timesheet_ids = fields.One2many(
        'tracker.timesheet',
        'task_id',
        string='Registro de Tiempos'
    )
    
    total_hours = fields.Float(
        string='Horas Totales',
        compute='_compute_total_hours',
        store=True,
        help='Total de horas trabajadas en esta tarea'
    )
    
    expected_hours = fields.Float(
        string='Duración Esperada',
        help='Horas estimadas para completar la tarea'
    )
    
    notes = fields.Text(string='Notas')
    
    promise_date = fields.Datetime(
        related='project_id.promise_date',
        string='Fecha Prometida',
        store=True,
        readonly=True
    )
    
    partner_id = fields.Many2one(
        related='project_id.partner_id',
        string='Cliente',
        store=True,
        readonly=True
    )
    
    project_state = fields.Selection(
        related='project_id.state',
        string='Estado Proyecto',
        store=True,
        readonly=True
    )
    
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
    
    active_timesheet_id = fields.Many2one(
        'tracker.timesheet',
        string='Registro Activo',
        help='Registro de tiempo actualmente en progreso'
    )
    
    current_start_time = fields.Datetime(
        string='Inicio Actual',
        help='Hora de inicio del registro actual'
    )
    
    @api.depends('quantity', 'quantity_done')
    def _compute_quantity_remaining(self):
        for record in self:
            record.quantity_remaining = record.quantity - record.quantity_done
    
    @api.depends('timesheet_ids.hours')
    def _compute_total_hours(self):
        for record in self:
            record.total_hours = sum(record.timesheet_ids.mapped('hours'))
    
    def write(self, vals):
        # Validar cambio de empleado en tareas iniciadas
        if 'employee_id' in vals:
            # Permitir el cambio si viene con otros campos (edición desde formulario)
            # o si tiene el permiso especial
            is_form_edit = len(vals) > 1  # Si viene con más campos, es edición de formulario
            has_permission = self.env.user.has_group('sm_tracker.group_tracker_change_employee')
            
            if not is_form_edit and not has_permission:
                for record in self:
                    # Si la tarea ya está en progreso, done o pausado, no permitir cambio sin permiso
                    if record.state in ['in_progress', 'done', 'paused']:
                        raise UserError(_(
                            'No puede cambiar el operario de una tarea que ya está en progreso, '
                            'pausada o terminada. Contacte a un supervisor si necesita hacer este cambio.'
                        ))
        
        if 'state' in vals:
            vals['state_changed_by'] = self.env.user.id
            vals['state_changed_date'] = fields.Datetime.now()
            
            # Si la tarea cambia a 'in_progress', cambiar el proyecto de 'unstarted' a 'processing'
            if vals['state'] == 'in_progress':
                for record in self:
                    if record.project_id and record.project_id.state == 'unstarted':
                        record.project_id.write({'state': 'processing'})
        
        return super(TrackerTask, self).write(vals)
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.name
    
    def action_start_task(self):
        """Abrir wizard para validar NIP del operario"""
        for record in self:
            if record.state not in ['ready', 'pending', 'paused']:
                raise UserError(_('Solo se puede iniciar una tarea en estado Listo, Pendiente o Pausado.'))
            
            # Validar que el proyecto tenga fecha prometida
            if not record.project_id.promise_date:
                raise UserError(_(
                    'No se puede iniciar la tarea porque el proyecto no tiene una Fecha Prometida asignada. '
                    'Por favor, asigne una fecha prometida al proyecto antes de iniciar las tareas.'
                ))
            
            if not record.employee_id:
                raise UserError(_('Debe asignar un operario antes de iniciar la tarea.'))
            
            # Abrir wizard para validar NIP
            return {
                'name': _('Validar NIP del Operario'),
                'type': 'ir.actions.act_window',
                'res_model': 'tracker.task.pin.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_task_id': record.id,
                }
            }
    
    def _start_task_internal(self):
        """Método interno para iniciar la tarea (después de validar NIP)"""
        for record in self:
            current_time = fields.Datetime.now()
            
            timesheet_vals = {
                'task_id': record.id,
                'employee_id': record.employee_id.id,
                'analytic_account_id': record.analytic_account_id.id,
                'name': record.name,
                'date': fields.Date.today(),
                'start_time': current_time,
                'state': 'running'
            }
            timesheet = self.env['tracker.timesheet'].create(timesheet_vals)
            
            record.write({
                'state': 'in_progress',
                'active_timesheet_id': timesheet.id,
                'current_start_time': current_time
            })
            
            if record.project_id.state == 'pending':
                record.project_id.write({'state': 'processing'})
        
        return True
    
    def action_pause_task(self):
        for record in self:
            if record.state != 'in_progress':
                raise UserError(_('Solo se puede pausar una tarea en progreso.'))
            
            if record.active_timesheet_id:
                record.active_timesheet_id.write({
                    'end_time': fields.Datetime.now(),
                    'state': 'stopped'
                })
            
            record.write({
                'state': 'paused',
                'active_timesheet_id': False,
                'current_start_time': False
            })
        
        return True
    
    def action_complete_task(self):
        for record in self:
            if record.state not in ['in_progress', 'paused']:
                raise UserError(_('Solo se puede completar una tarea en progreso o pausada.'))
            
            if record.active_timesheet_id:
                record.active_timesheet_id.write({
                    'end_time': fields.Datetime.now(),
                    'state': 'stopped'
                })
            
            record.write({
                'state': 'done',
                'active_timesheet_id': False,
                'current_start_time': False,
                'quantity_done': record.quantity
            })
            
            # Verificar si todas las tareas del proyecto están terminadas
            project = record.project_id
            if project.state == 'processing':
                # Obtener solo tareas con estado válido (no NULL, no cancel)
                valid_tasks = project.task_ids.filtered(
                    lambda t: t.state and t.state != 'cancel'
                )
                
                # Si hay tareas válidas y todas están terminadas
                if valid_tasks and all(t.state == 'done' for t in valid_tasks):
                    project.write({
                        'state': 'pending_delivery',
                        'completion_date': fields.Datetime.now()
                    })
        
        return True
    
    def action_cancel_task(self):
        for record in self:
            if record.state == 'done':
                raise UserError(_('No se puede cancelar una tarea terminada.'))
            
            if record.active_timesheet_id:
                record.active_timesheet_id.write({
                    'end_time': fields.Datetime.now(),
                    'state': 'stopped'
                })
            
            record.write({
                'state': 'cancel',
                'active_timesheet_id': False,
                'current_start_time': False
            })
        return True
    
    def action_reset_to_pending(self):
        for record in self:
            record.write({
                'state': 'pending',
                'current_start_time': False
            })
        return True
    
    def action_view_timesheets(self):
        self.ensure_one()
        return {
            'name': _('Registros de Tiempo - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'tracker.timesheet',
            'view_mode': 'tree,form',
            'domain': [('task_id', '=', self.id)],
            'context': {
                'default_task_id': self.id,
                'default_employee_id': self.employee_id.id,
                'default_analytic_account_id': self.analytic_account_id.id,
                'create': False,
                'edit': False,
            },
        }