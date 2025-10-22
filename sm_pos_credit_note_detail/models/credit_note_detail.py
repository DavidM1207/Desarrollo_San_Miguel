from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CreditNoteDetail(models.Model):
    _name = 'credit.note.detail'
    _description = 'Detalle de Notas de Crédito'
    _order = 'date desc, id desc'
    _rec_name = 'reference'

    reference = fields.Char(
        string='Referencia',
        required=True,
        help='Referencia de la nota de crédito'
    )
    
    date = fields.Date(
        string='Fecha',
        required=True,
        default=fields.Date.context_today
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=True
    )
    
    account_move_line_id = fields.Many2one(
        'account.move.line',
        string='Apunte Contable',
        required=True,
        domain=[('is_credit_note_line', '=', True)]
    )
    
    move_id = fields.Many2one(
        'account.move',
        string='Asiento Contable',
        related='account_move_line_id.move_id',
        store=True
    )
    
    amount = fields.Monetary(
        string='Importe',
        related='account_move_line_id.credit',
        store=True,
        currency_field='company_currency_id'
    )
    
    balance = fields.Monetary(
        string='Saldo',
        compute='_compute_balance',
        store=True,
        currency_field='company_currency_id'
    )
    
    reconciled = fields.Boolean(
        string='Conciliado',
        related='account_move_line_id.reconciled',
        store=True
    )
    
    full_reconcile_id = fields.Many2one(
        'account.full.reconcile',
        string='Conciliación Completa',
        related='account_move_line_id.full_reconcile_id'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        related='account_move_line_id.company_id',
        store=True
    )
    
    company_currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        string='Moneda de la Compañía'
    )
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('posted', 'Publicado'),
        ('cancel', 'Cancelado')
    ], string='Estado', related='move_id.state', store=True)
    
    notes = fields.Text(string='Notas')
    
    @api.depends('account_move_line_id', 'account_move_line_id.amount_residual')
    def _compute_balance(self):
        for record in self:
            if record.account_move_line_id:
                record.balance = abs(record.account_move_line_id.amount_residual)
            else:
                record.balance = 0.0
    
    @api.model
    def create(self, vals):
        # Validar que el apunte contable sea de nota de crédito
        if 'account_move_line_id' in vals:
            move_line = self.env['account.move.line'].browse(vals['account_move_line_id'])
            if not move_line.is_credit_note_line:
                raise UserError(_('El apunte contable seleccionado no corresponde a una nota de crédito por aplicar.'))
        return super(CreditNoteDetail, self).create(vals)
    
    def action_reconcile(self):
        """Abre el asistente de conciliación para este apunte"""
        self.ensure_one()
        return {
            'name': _('Conciliar Nota de Crédito'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'tree,form',
            'domain': [('id', '=', self.account_move_line_id.id)],
            'context': {
                'search_default_unreconciled': 1,
                'default_account_id': self.account_move_line_id.account_id.id,
            }
        }
    
    def action_view_move(self):
        """Abre el asiento contable relacionado"""
        self.ensure_one()
        return {
            'name': _('Asiento Contable'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.move_id.id,
            'target': 'current',
        }
    
    @api.model
    def action_sync_credit_notes(self):
        """Sincroniza las notas de crédito desde los apuntes contables"""
        # Buscar apuntes de notas de crédito que no estén en el modelo
        move_lines = self.env['account.move.line'].search([
            ('is_credit_note_line', '=', True),
            ('credit', '>', 0),
            ('move_id.state', '=', 'posted')
        ])
        
        existing_lines = self.search([]).mapped('account_move_line_id')
        new_lines = move_lines - existing_lines
        
        created_count = 0
        for line in new_lines:
            self.create({
                'reference': line.move_id.ref or line.move_id.name,
                'date': line.date,
                'partner_id': line.partner_id.id,
                'account_move_line_id': line.id,
            })
            created_count += 1
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Sincronización completada'),
                'message': _('Se sincronizaron %s notas de crédito.') % created_count,
                'type': 'success',
                'sticky': False,
            }
        }