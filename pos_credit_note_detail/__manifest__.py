# -*- coding: utf-8 -*-
{
    'name': 'Detalle NC POS',
    'version': '17.0.2.0.0',
    'category': 'Point of Sale',
    'summary': 'Vista de apuntes contables filtrada para Notas de Crédito del POS',
    'description': """
        Vista dinámica que muestra los apuntes contables de la cuenta 211040020000
        (Notas de Crédito por Aplicar) con toda la funcionalidad nativa de Odoo.
        
        - Se actualiza en tiempo real
        - Permite conciliación
        - Agrupa por sesión de POS
        - Funciona exactamente como Apuntes Contables estándar
    """,
    'author': 'SAN MIGUEL, S.A.',

    'depends': [
        'base',
        'account',
        'point_of_sale',
    ],
    'data': [
        'views/pos_credit_note_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
