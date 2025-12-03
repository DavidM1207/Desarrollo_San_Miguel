# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    tracker_project_ids = fields.Many2many(
        'tracker.project',
        'tracker_project_invoice_rel',
        'invoice_id',
        'project_id',
        string='Proyectos Tracker'
    )
    
    tracker_project_count = fields.Integer(
        string='Trackers',
        compute='_compute_tracker_project_count'
    )
    
    @api.depends('tracker_project_ids')
    def _compute_tracker_project_count(self):
        for move in self:
            move.tracker_project_count = len(move.tracker_project_ids)
    
    def action_view_tracker_projects(self):
        """Ver proyectos tracker de la factura"""
        self.ensure_one()
        return {
            'name': _('Proyectos Tracker'),
            'type': 'ir.actions.act_window',
            'res_model': 'tracker.project',
            'view_mode': 'tree,form,kanban',
            'domain': [('invoice_ids', 'in', self.id)],
        }