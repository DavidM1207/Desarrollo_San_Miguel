# -*- coding: utf-8 -*-

from odoo import models, fields, api


class TrackerEmployee(models.Model):
    _inherit = 'hr.employee'

    tracker_task_ids = fields.One2many(
        'tracker.task',
        'employee_id',
        string='Tareas Asignadas'
    )
    
    tracker_task_count = fields.Integer(
        string='Número de Tareas',
        compute='_compute_tracker_task_count'
    )
    
    @api.depends('tracker_task_ids')
    def _compute_tracker_task_count(self):
        for record in self:
            record.tracker_task_count = len(record.tracker_task_ids)
    
    def action_view_tracker_tasks(self):
        self.ensure_one()
        return {
            'name': 'Mis Tareas',
            'type': 'ir.actions.act_window',
            'res_model': 'tracker.task',
            'view_mode': 'tree,kanban,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }