from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CreditNoteReconcileWizard(models.TransientModel):
    _name = 'credit.note.reconcile.wizard'
    _description = 'Asistente de Conciliación de Notas de Crédito'
    
    session_id = fields.Many2one('pos.session', string='Sesión', readonly=True)
    line_ids = fields.One2many('credit.note.reconcile.line', 'wizard_id', string='Líneas')
    total_amount = fields.Monetary(string='Total', compute='_compute_total_amount', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='session_id.currency_id')
    account_id = fields.Many2one('account.account', string='Cuenta', readonly=True)
    
    # Líneas de apuntes disponibles para conciliar
    available_line_ids = fields.Many2many(
        'account.move.line',
        'reconcile_wizard_move_line_rel',
        'wizard_id',
        'line_id',
        string='Apuntes Disponibles'
    )
    
    @api.depends('line_ids', 'line_ids.selected', 'line_ids.amount')
    def _compute_total_amount(self):
        for wizard in self:
            wizard.total_amount = sum(wizard.line_ids.filtered('selected').mapped('amount'))
    
    def action_open_reconciliation(self):
        """Abre la vista de apuntes contables completa para conciliar"""
        self.ensure_one()
        
        # Obtener todas las líneas seleccionadas
        selected_lines = self.line_ids.filtered('selected')
        
        if not selected_lines:
            raise UserError(_('Debe seleccionar al menos una nota de crédito para continuar.'))
        
        # Buscar los apuntes contables reales relacionados
        move_line_ids = []
        for line in selected_lines:
            if line.move_line_id:
                move_line_ids.append(line.move_line_id.id)
        
        # Agregar los apuntes disponibles
        if self.available_line_ids:
            move_line_ids.extend(self.available_line_ids.ids)
        
        # Eliminar duplicados
        move_line_ids = list(set(move_line_ids))
        
        # Construir mensaje con las NC seleccionadas
        help_text = '<div style="padding: 10px;">'
        help_text += '<h4>📋 Notas de Crédito Seleccionadas para Conciliar:</h4>'
        help_text += '<table style="width: 100%; border-collapse: collapse; margin: 10px 0;">'
        help_text += '<tr style="background-color: #e8f5e9;"><th style="padding: 5px; text-align: left;">Referencia</th><th style="padding: 5px; text-align: right;">Monto</th></tr>'
        
        total = 0
        for line in selected_lines:
            help_text += '<tr><td style="padding: 5px;">%s</td><td style="padding: 5px; text-align: right;">%s%s</td></tr>' % (
                line.reference,
                line.currency_id.symbol,
                '{:,.2f}'.format(line.amount)
            )
            total += line.amount
        
        help_text += '<tr style="background-color: #a5d6a7; font-weight: bold;"><td style="padding: 5px;">TOTAL</td><td style="padding: 5px; text-align: right;">%s%s</td></tr>' % (
            self.currency_id.symbol,
            '{:,.2f}'.format(total)
        )
        help_text += '</table>'
        
        help_text += '<div style="background-color: #e3f2fd; padding: 10px; margin: 10px 0; border-radius: 5px;">'
        help_text += '<h5>📝 Instrucciones:</h5>'
        help_text += '<ol>'
        help_text += '<li>Selecciona los apuntes que deseas conciliar con las NC seleccionadas</li>'
        help_text += '<li>Ve al menú <b>"Acción"</b> → <b>"Reconciliar apuntes"</b></li>'
        help_text += '</ol>'
        help_text += '</div>'
        help_text += '</div>'
        
        return {
            'name': _('Conciliar Notas de Crédito - Sesión %s') % self.session_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list',
            'views': [(False, 'list')],
            'domain': [('id', 'in', move_line_ids)],
            'context': {
                'create': False,
                'edit': False,
                'search_default_unreconciled': 1,
            },
            'target': 'current',
            'help': help_text,
        }


class CreditNoteReconcileLine(models.TransientModel):
    _name = 'credit.note.reconcile.line'
    _description = 'Línea de Nota de Crédito para Conciliación'
    _order = 'date desc, id desc'
    
    wizard_id = fields.Many2one('credit.note.reconcile.wizard', string='Wizard', required=True, ondelete='cascade')
    pos_order_id = fields.Many2one('pos.order', string='Orden POS', readonly=True)
    move_line_id = fields.Many2one('account.move.line', string='Apunte Contable', readonly=True)
    
    selected = fields.Boolean(string='Seleccionar', default=False)
    reference = fields.Char(string='Referencia', readonly=True)
    date = fields.Date(string='Fecha', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Cliente', readonly=True)
    amount = fields.Monetary(string='Monto', readonly=True, currency_field='currency_id')
    reconciled = fields.Boolean(string='Conciliado', readonly=True)
    currency_id = fields.Many2one('res.currency', related='wizard_id.currency_id')