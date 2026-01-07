# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime


class TrackerProjectChangeStoreWizard(models.TransientModel):
    _name = 'tracker.project.change.store.wizard'
    _description = 'Wizard para Cambiar Tienda del Proyecto'
    
    project_id = fields.Many2one(
        'tracker.project',
        string='Proyecto',
        required=True
    )
    
    old_store_id = fields.Many2one(
        'account.analytic.account',
        string='Tienda Actual',
        required=True,
        readonly=True
    )
    
    new_store_id = fields.Many2one(
        'account.analytic.account',
        string='Nueva Tienda',
        required=True
    )
    
    reason = fields.Text(
        string='Razón del Cambio',
        required=True,
        help='Explique por qué se está cambiando la tienda del proyecto'
    )
    
    @api.model
    def default_get(self, fields_list):
        """Obtener valores por defecto incluyendo el proyecto actual"""
        res = super(TrackerProjectChangeStoreWizard, self).default_get(fields_list)
        
        # Obtener el proyecto del contexto
        project_id = self.env.context.get('active_id')
        if project_id:
            project = self.env['tracker.project'].browse(project_id)
            res.update({
                'project_id': project.id,
                'old_store_id': project.analytic_account_id.id if project.analytic_account_id else False,
            })
        
        return res
    
    def action_confirm_change(self):
        """Confirmar el cambio de tienda"""
        self.ensure_one()
        
        if not self.reason:
            raise UserError(_('Debe proporcionar una razón para el cambio de tienda.'))
        
        # Preparar el registro del cambio
        change_date = fields.Datetime.now()
        user = self.env.user
        
        change_log = f"""
[{change_date}] {user.name}
Tienda anterior: {self.old_store_id.name}
Nueva tienda: {self.new_store_id.name}
Razón: {self.reason}
{'='*60}
"""
        
        # Actualizar el proyecto
        self.project_id.write({
            'analytic_account_id': self.new_store_id.id,
            'previous_analytic_account_id': self.old_store_id.id,
            'store_change_reason': self.reason,
            'store_change_history': (self.project_id.store_change_history or '') + change_log
        })
        
        # Actualizar la tienda de todas las tareas del proyecto
        self.project_id.task_ids.write({
            'analytic_account_id': self.new_store_id.id
        })
        
        return {'type': 'ir.actions.act_window_close'}