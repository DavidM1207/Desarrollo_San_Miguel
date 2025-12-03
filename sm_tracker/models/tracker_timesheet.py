# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class TrackerTimesheet(models.Model):
    _name = 'tracker.timesheet'
    _description = 'Registro de Tiempo Tracker'
    _order = 'start_time desc'

    task_id = fields.Many2one(
        'tracker.task',
        string='Tarea',
        required=True,
        ondelete='cascade',
        readonly=True
    )
    
    project_id = fields.Many2one(
        'tracker.project',
        string='Proyecto',
        related='task_id.project_id',
        store=True,
        readonly=True
    )
    
    operator_id = fields.Many2one(
        'res.users',
        string='Operario',
        required=True,
        readonly=True
    )
    
    start_time = fields.Datetime(
        string='Hora de Inicio',
        required=True,
        readonly=True,
        default=fields.Datetime.now
    )
    
    end_time = fields.Datetime(
        string='Hora de Fin',
        readonly=True
    )
    
    duration = fields.Float(
        string='Duración (Horas)',
        compute='_compute_duration',
        store=True,
        readonly=True
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='Registrado por',
        required=True,
        readonly=True,
        default=lambda self: self.env.user
    )
    
    state = fields.Selection([
        ('running', 'En Ejecución'),
        ('stopped', 'Detenido'),
    ], string='Estado', compute='_compute_state', store=True, readonly=True)
    
    notes = fields.Text(string='Notas', readonly=True)
    
    @api.depends('end_time')
    def _compute_state(self):
        for record in self:
            record.state = 'stopped' if record.end_time else 'running'
    
    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        """Calcular duración en horas"""
        for record in self:
            if record.start_time and record.end_time:
                delta = record.end_time - record.start_time
                record.duration = delta.total_seconds() / 3600.0
            elif record.start_time:
                # Si está en ejecución, calcular tiempo transcurrido hasta ahora
                delta = fields.Datetime.now() - record.start_time
                record.duration = delta.total_seconds() / 3600.0
            else:
                record.duration = 0.0
    
    @api.constrains('start_time', 'end_time')
    def _check_times(self):
        """Validar que end_time sea posterior a start_time"""
        for record in self:
            if record.end_time and record.start_time:
                if record.end_time < record.start_time:
                    raise ValidationError(_(
                        'La hora de fin no puede ser anterior a la hora de inicio.'
                    ))
    
    def name_get(self):
        """Personalizar nombre mostrado"""
        result = []
        for record in self:
            name = '%s - %s (%s)' % (
                record.task_id.name,
                record.operator_id.name,
                record.start_time.strftime('%Y-%m-%d %H:%M') if record.start_time else ''
            )
            result.append((record.id, name))
        return result