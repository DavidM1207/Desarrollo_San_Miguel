# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    tracker_project_ids = fields.Many2many(
        'tracker.project',
        string='Proyectos Tracker',
        compute='_compute_tracker_project_ids'
    )
    
    @api.depends('invoice_line_ids.sale_line_ids.order_id.tracker_project_ids')
    def _compute_tracker_project_ids(self):
        for move in self:
            projects = self.env['tracker.project']
            for line in move.invoice_line_ids:
                for sale_line in line.sale_line_ids:
                    projects |= sale_line.order_id.tracker_project_ids
            move.tracker_project_ids = projects