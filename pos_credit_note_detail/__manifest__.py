# -*- coding: utf-8 -*-
{
    'name': 'Detalle de Notas de Crédito POS',
    'version': '17.0.1.0.2',
    'category': 'Point of Sale',
    'summary': 'Visualiza el detalle individual de notas de crédito agrupadas por sesión de POS',
    'description': """
        Este módulo permite visualizar el detalle de las notas de crédito del POS
        que se agrupan por sesión en el libro mayor, mostrando cada nota de crédito
        individual con su información completa para facilitar la conciliación.
    """,
    'author': 'Tu Empresa',
    'website': 'https://www.tuempresa.com',
    'depends': [
        'base',
        'account',
        'point_of_sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_credit_note_detail_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
