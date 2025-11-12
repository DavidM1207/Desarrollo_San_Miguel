# -*- coding: utf-8 -*-
{
    'name': 'POS - Cambio de Pagos Mismo Día',
    'version': '17.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Botón para cambiar pagos solo del mismo día con solicitud de aprobación',
    'author': 'SAN MIGUEL MADERA, S.A.',
    'depends': [
        'pos_payment_change',
        'pt_pos_payment_approval',
    ],
    'data': [
        'views/pos_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}