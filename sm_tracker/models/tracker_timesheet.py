# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime


class TrackerTimesheet(models.Model):
    _name = 'tracker.timesheet'
    _description = 'Registro de Tiempo de Trabajo'
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Descripción',
        required=True,
        readonly=True
    )
    
    task_id = fields.Many2one(
        'tracker.task',
        string='Tarea',
        required=True,
        readonly=True,
        ondelete='cascade'
    )
    
    project_id = fields.Many2one(
        'tracker.project',
        related='task_id.project_id',
        string='Proyecto',
        store=True,
        readonly=True
    )
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Empleado',
        required=True,
        readonly=True,
        default=lambda self: self.env.user.employee_id
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='Usuario',
        default=lambda self: self.env.user,
        readonly=True
    )
    
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Tienda',
        required=True,
        readonly=True
    )
    
    date = fields.Date(
        string='Fecha',
        required=True,
        readonly=True,
        default=fields.Date.context_today
    )
    
    start_time = fields.Datetime(
        string='Hora Inicio',
        readonly=True
    )
    
    end_time = fields.Datetime(
        string='Hora Fin',
        readonly=True
    )
    
    hours = fields.Float(
        string='Horas',
        compute='_compute_hours',
        store=True,
        readonly=True
    )
    
    notes = fields.Text(string='Notas')
    
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company
    )
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('running', 'En Progreso'),
        ('stopped', 'Detenido'),
    ], string='Estado', default='draft')
    
    @api.depends('start_time', 'end_time')
    def _compute_hours(self):
        for record in self:
            if record.start_time and record.end_time:
                delta = record.end_time - record.start_time
                record.hours = delta.total_seconds() / 3600.0
            elif record.start_time and not record.end_time:
                delta = fields.Datetime.now() - record.start_time
                record.hours = delta.total_seconds() / 3600.0
            else:
                record.hours = 0.0
    
    @api.constrains('hours')
    def _check_hours(self):
        for record in self:
            if record.hours < 0:
                raise ValidationError(_('Las horas no pueden ser negativas.'))
    
    def write(self, vals):
        """Prevenir modificación de campos críticos, solo permitir editar notas"""
        # Campos que NUNCA se pueden modificar
        protected_fields = [
            'name', 'task_id', 'employee_id', 'user_id', 
            'analytic_account_id', 'date', 'start_time', 'end_time', 'hours'
        ]
        
        # Si el usuario es Manager, permitir todo
        if self.env.user.has_group('sm_tracker.group_tracker_manager'):
            return super(TrackerTimesheet, self).write(vals)
        
        # Verificar si se está intentando modificar campos protegidos
        attempting_to_modify = [field for field in protected_fields if field in vals]
        
        if attempting_to_modify:
            raise UserError(_(
                'No se pueden modificar los siguientes campos: %s. '
                'Solo se pueden agregar notas.' % ', '.join(attempting_to_modify)
            ))
        
        return super(TrackerTimesheet, self).write(vals)
    
    def action_start_timer(self):
        for record in self:
            if record.start_time:
                raise UserError(_('El temporizador ya está en marcha.'))
            
            record.write({
                'start_time': fields.Datetime.now(),
                'state': 'running',
                'user_id': self.env.user.id
            })
        return True
    
    def action_stop_timer(self):
        for record in self:
            if not record.start_time:
                raise UserError(_('El temporizador no ha sido iniciado.'))
            
            if record.end_time:
                raise UserError(_('El temporizador ya ha sido detenido.'))
            
            record.write({
                'end_time': fields.Datetime.now(),
                'state': 'stopped',
                'user_id': self.env.user.id
            })
        return True