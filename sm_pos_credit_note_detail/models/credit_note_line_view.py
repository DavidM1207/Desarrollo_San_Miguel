from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CreditNoteLineView(models.TransientModel):
    _name = 'credit.note.line.view'
    _description = 'Vista Expandida de Líneas de NC para Conciliación'
    _order = 'date, id'
    
    # Campo para agrupar todas las líneas de una misma búsqueda
    search_token = fields.Char(string='Token de Búsqueda', index=True)
    
    # Campos de la tabla
    date = fields.Date(string='Fecha', required=True)
    name = fields.Char(string='Asiento', required=True)
    account_id = fields.Many2one('account.account', string='Cuenta', required=True)
    account_name = fields.Char(string='Nombre Cuenta', related='account_id.name')
    session_name = fields.Char(string='Sesión POS')
    nc_type = fields.Selection([
        ('original', 'O NC Original'),
        ('refund', 'Refacturación'),
    ], string='Tipo', required=True)
    description = fields.Text(string='Detalle NC')
    debit = fields.Monetary(string='Debe', currency_field='currency_id')
    credit = fields.Monetary(string='Haber', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Moneda')
    analytic_distribution = fields.Char(string='Distribución Analítica')
    
    # Campos de control
    selected = fields.Boolean(string='Conciliar', default=False)
    move_line_id = fields.Many2one('account.move.line', string='Apunte Contable Real')
    pos_order_id = fields.Many2one('pos.order', string='Orden POS')
    reconciled = fields.Boolean(string='Ya Conciliado', related='move_line_id.reconciled')
    
    def action_reconcile_selected(self):
        """Concilia las líneas seleccionadas"""
        selected_lines = self.search([
            ('search_token', '=', self.search_token),
            ('selected', '=', True)
        ])
        
        if not selected_lines:
            raise UserError(_('Debe seleccionar al menos una línea para conciliar.'))
        
        # Obtener los apuntes contables reales
        move_lines = selected_lines.mapped('move_line_id').filtered(lambda l: l)
        
        if not move_lines:
            raise UserError(_('No se encontraron apuntes contables válidos para conciliar.'))
        
        # Verificar que haya al menos 2 líneas
        if len(move_lines) < 2:
            raise UserError(_('Debe seleccionar al menos 2 apuntes para conciliar.'))
        
        # Intentar conciliar
        try:
            move_lines.reconcile()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Éxito'),
                    'message': _('Se conciliaron %s apuntes correctamente.') % len(move_lines),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(_('Error al conciliar: %s') % str(e))


class PosOrderCreditNoteExpanded(models.TransientModel):
    _name = 'pos.order.credit.note.expanded'
    _description = 'Vista Expandida de NC'
    
    line_ids = fields.One2many('credit.note.line.view', 'search_token', string='Líneas')
    search_token = fields.Char(string='Token')
    
    def action_reconcile_selected(self):
        """Concilia las líneas seleccionadas"""
        return self.line_ids.action_reconcile_selected()