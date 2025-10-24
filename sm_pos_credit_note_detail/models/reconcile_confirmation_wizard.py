from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ReconcileConfirmationWizard(models.TransientModel):
    _name = 'reconcile.confirmation.wizard'
    _description = 'Wizard de Confirmación de Conciliación'
    
    line_count = fields.Integer(string='Cantidad de Líneas', readonly=True)
    total_debit = fields.Monetary(string='Total Debe', readonly=True, currency_field='currency_id')
    total_credit = fields.Monetary(string='Total Haber', readonly=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Moneda', readonly=True)
    line_details = fields.Html(string='Detalle', readonly=True)
    move_line_ids = fields.Many2many('account.move.line', string='Apuntes a Conciliar')
    
    def action_confirm_reconcile(self):
        """Ejecuta la conciliación después de confirmar"""
        self.ensure_one()
        
        if not self.move_line_ids:
            raise UserError(_('No hay apuntes para conciliar.'))
        
        try:
            self.move_line_ids.reconcile()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Conciliación Exitosa'),
                    'message': _('Se conciliaron %s apuntes correctamente.') % len(self.move_line_ids),
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
        except Exception as e:
            raise UserError(_('Error al conciliar: %s') % str(e))