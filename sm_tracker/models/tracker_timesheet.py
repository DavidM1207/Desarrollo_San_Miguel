# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class TrackerTimesheet(models.Model):
    _name = 'tracker.timesheet'
    _description = 'Registro de Tiempo de Tarea'
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Descripción',
        required=True
    )
    
    task_id = fields.Many2one(
        'tracker.task',
        string='Tarea',
        required=True,
        ondelete='cascade'
    )
    
    project_id = fields.Many2one(
        related='task_id.project_id',
        string='Proyecto',
        store=True,
        readonly=True
    )
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Empleado',
        required=True,
        default=lambda self: self.env.user.employee_id
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='Usuario',
        related='employee_id.user_id',
        store=True,
        readonly=True
    )
    
    date = fields.Date(
        string='Fecha',
        required=True,
        default=fields.Date.today
    )
    
    start_time = fields.Datetime(
        string='Hora Inicio',
        help='Hora de inicio del trabajo'
    )
    
    end_time = fields.Datetime(
        string='Hora Fin',
        help='Hora de fin del trabajo'
    )
    
    hours = fields.Float(
        string='Horas',
        required=True,
        help='Horas trabajadas'
    )
    
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Tienda',
        required=True
    )
    
    notes = fields.Text(string='Notas')
    
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company
    )
    
    @api.onchange('start_time', 'end_time')
    def _onchange_times(self):
        """Calcular horas automáticamente si se ingresan hora inicio y fin"""
        if self.start_time and self.end_time:
            if self.end_time < self.start_time:
                raise ValidationError(_('La hora de fin no puede ser menor a la hora de inicio.'))
            
            delta = self.end_time - self.start_time
            self.hours = delta.total_seconds() / 3600.0
    
    @api.constrains('hours')
    def _check_hours(self):
        for record in self:
            if record.hours <= 0:
                raise ValidationError(_('Las horas deben ser mayor a 0.'))
            if record.hours > 24:
                raise ValidationError(_('No se pueden registrar más de 24 horas por día.'))
    
    @api.constrains('start_time', 'end_time')
    def _check_times(self):
        for record in self:
            if record.start_time and record.end_time:
                if record.end_time < record.start_time:
                    raise ValidationError(_('La hora de fin no puede ser menor a la hora de inicio.'))
    
    @api.onchange('task_id')
    def _onchange_task_id(self):
        if self.task_id:
            self.name = self.task_id.name
            self.analytic_account_id = self.task_id.analytic_account_id
            if self.task_id.employee_id:
                self.employee_id = self.task_id.employee_id
    
    def action_start_timer(self):
        """Iniciar temporizador"""
        self.ensure_one()
        if not self.start_time:
            self.write({'start_time': fields.Datetime.now()})
        return True
    
    def action_stop_timer(self):
        """Detener temporizador y calcular horas"""
        self.ensure_one()
        if not self.start_time:
            raise UserError(_('Debe iniciar el temporizador primero.'))
        
        if self.end_time:
            raise UserError(_('El temporizador ya fue detenido.'))
        
        end_time = fields.Datetime.now()
        delta = end_time - self.start_time
        hours = delta.total_seconds() / 3600.0
        
        self.write({
            'end_time': end_time,
            'hours': hours
        })
        
        return True