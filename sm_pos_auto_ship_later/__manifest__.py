# -*- coding: utf-8 -*-
{
    'name': 'POS Auto Ship Later',
    'version': '17.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Activar automáticamente "Enviar Después" en POS con fecha actual',
    'description': """
        Este módulo modifica el comportamiento del Punto de Venta para:
        - Activar automáticamente la opción "Enviar Después" al confirmar ventas
        - Establecer automáticamente la fecha actual como fecha de envío
        - Garantizar que siempre se generen 2 movimientos de inventario (picking y despacho)
    """,
    'author': 'SAN MIGUEL, S.A.',
    'depends': ['base','point_of_sale', 'stock'],
    'data': [
        'views/pos_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_auto_ship_later/static/src/js/pos_auto_ship_later.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
