
# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountMoveLine(models.Model):
    """
    Extensión del modelo account.move.line para agregar funcionalidad POS.
    
    Este módulo NO crea un modelo nuevo ni vistas SQL.
    Solo agrega un campo relacionado para facilitar la agrupación por sesión POS.
    
    La magia está en el XML donde usamos el modelo nativo 'account.move.line'
    con un dominio filtrado. Esto permite:
    - Actualización en tiempo real
    - Conciliación nativa
    - Todas las funciones estándar de apuntes contables
    """
    _inherit = 'account.move.line'
    
    # Campo relacionado para poder agrupar por sesión POS
    pos_session_id = fields.Many2one(
        'pos.session', 
        string='Sesión POS',
        related='move_id.pos_session_id',  # Obtiene la sesión del asiento contable
        store=True,  # Se guarda en BD para búsquedas rápidas
        readonly=True,  # No se puede editar directamente
        help='Sesión de POS asociada a este apunte contable. '
             'Este campo permite agrupar las notas de crédito por sesión.'
    )
    
    # NOTA: No necesitamos agregar más campos porque:
    # 1. Usamos TODOS los campos nativos de account.move.line
    # 2. La vista XML filtra por dominio, no crea registros nuevos
    # 3. Toda la lógica de negocio (conciliación, etc.) es nativa de Odoo