# -*- coding: utf-8 -*-
{
    'name': 'POS - Cambio de Pagos con Restricción',
    'version': '17.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Agrega acción para cambiar pagos solo del mismo día',
    'description': """
        Módulo que extiende la funcionalidad de cambio de pagos en POS
        agregando una segunda acción que valida que la orden sea del mismo día.
    """,
    'author': 'SAN MIGUEL MADERA, S.A.',
    'depends': [
        'point_of_sale',
    ],
    'data': [
        'views/pos_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}