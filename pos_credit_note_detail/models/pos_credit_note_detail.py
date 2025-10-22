# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PosCreditNoteDetail(models.Model):
    _name = 'pos.credit.note.detail'
    _description = 'Detalle de Notas de Crédito POS'
    _order = 'date desc, id desc'
    _auto = False

    date = fields.Date(string='Fecha', readonly=True)
    journal_id = fields.Many2one('account.journal', string='Diario', readonly=True)
    move_id = fields.Many2one('account.move', string='Nota de Crédito', readonly=True)
    move_name = fields.Char(string='Número de Nota', readonly=True)
    name = fields.Char(string='Etiqueta', readonly=True)
    debit = fields.Monetary(string='Débito', readonly=True, currency_field='company_currency_id')
    credit = fields.Monetary(string='Crédito', readonly=True, currency_field='company_currency_id')
    balance = fields.Monetary(string='Balance', readonly=True, currency_field='company_currency_id')
    matching_number = fields.Char(string='Emparejamiento', readonly=True)
    analytic_distribution = fields.Json(string='Distribución Analítica', readonly=True)
    analytic_precision = fields.Integer(string='Precisión Analítica', readonly=True, default=2)
    account_id = fields.Many2one('account.account', string='Cuenta', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Empresa', readonly=True)
    company_id = fields.Many2one('res.company', string='Compañía', readonly=True)
    company_currency_id = fields.Many2one('res.currency', string='Moneda', readonly=True)
    pos_order_id = fields.Many2one('pos.order', string='Orden POS', readonly=True)
    pos_session_id = fields.Many2one('pos.session', string='Sesión POS', readonly=True)
    
    def init(self):
        """
        Crea una vista SQL que desglosa las líneas de apuntes contables
        de la cuenta de Notas de Crédito por Aplicar (211040020000)
        """
        # Primero eliminar cualquier tabla o vista existente
        self._cr.execute("""
            DROP TABLE IF EXISTS pos_credit_note_detail CASCADE;
            DROP VIEW IF EXISTS pos_credit_note_detail CASCADE;
        """)
        
        # Ahora crear la vista SQL
        self._cr.execute("""
            CREATE OR REPLACE VIEW pos_credit_note_detail AS (
                SELECT 
                    aml.id as id,
                    aml.date as date,
                    aml.journal_id as journal_id,
                    aml.move_id as move_id,
                    am.name as move_name,
                    aml.name as name,
                    aml.debit as debit,
                    aml.credit as credit,
                    aml.balance as balance,
                    aml.matching_number as matching_number,
                    aml.analytic_distribution as analytic_distribution,
                    2 as analytic_precision,
                    aml.account_id as account_id,
                    aml.partner_id as partner_id,
                    aml.company_id as company_id,
                    aml.company_currency_id as company_currency_id,
                    po.id as pos_order_id,
                    po.session_id as pos_session_id
                FROM 
                    account_move_line aml
                    INNER JOIN account_move am ON aml.move_id = am.id
                    INNER JOIN account_account aa ON aml.account_id = aa.id
                    LEFT JOIN pos_order po ON am.id = po.account_move
                WHERE 
                    aa.code = '211040020000'
                    AND aml.parent_state = 'posted'
                ORDER BY 
                    aml.date DESC, aml.id DESC
            )
        """)

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, access_rights_uid=None):
        """
        Sobrescribe el método de búsqueda para permitir búsquedas personalizadas
        """
        return super(PosCreditNoteDetail, self)._search(
            domain, offset=offset, limit=limit, order=order,
            access_rights_uid=access_rights_uid
        )

    def action_view_journal_entry(self):
        """
        Acción para abrir el asiento contable relacionado
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Asiento Contable',
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_pos_order(self):
        """
        Acción para abrir la orden POS relacionada
        """
        self.ensure_one()
        if self.pos_order_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Orden POS',
                'res_model': 'pos.order',
                'res_id': self.pos_order_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return False

    def action_reconcile(self):
        """
        Acción para abrir el asistente de conciliación
        """
        self.ensure_one()
        move_line = self.env['account.move.line'].browse(self.id)
        if move_line.exists():
            return move_line.action_reconcile()
        return False
