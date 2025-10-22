

# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountMoveLine(models.Model):
    """
    Extensión del modelo account.move.line para agregar funcionalidad POS.
    
    Este módulo agrega un campo computado para obtener la sesión POS
    desde la orden de POS relacionada con el asiento contable.
    """
    _inherit = 'account.move.line'
    
    # Campo computado para obtener la sesión POS
    pos_session_id = fields.Many2one(
        'pos.session', 
        string='Sesión POS',
        compute='_compute_pos_session_id',
        store=True,
        readonly=True,
        help='Sesión de POS asociada a este apunte contable. '
             'Este campo permite agrupar las notas de crédito por sesión.'
    )
    
    @api.depends('move_id.pos_order_ids', 'move_id.pos_order_ids.session_id')
    def _compute_pos_session_id(self):
        """
        Calcula la sesión POS desde la orden de POS relacionada.
        
        La relación es: account.move.line → account.move → pos.order → pos.session
        """
        for line in self:
            # Buscar si este asiento está relacionado con una orden de POS
            if line.move_id.pos_order_ids:
                # Tomar la primera orden (normalmente solo hay una)
                line.pos_session_id = line.move_id.pos_order_ids[0].session_id
            else:
                line.pos_session_id = False