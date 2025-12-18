# -*- coding: utf-8 -*-
{
    'name': 'POS - Resaltar Cliente, NIT y Orden',
    'version': '17.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Pone en negrilla el Cliente, NIT y Número de Orden en el recibo del POS',
    'description': """
        Recibo POS - Resaltar Información Clave
        ==========================================
        
        Este módulo personaliza el recibo del Punto de Venta para:
        * Poner el nombre del cliente en negrilla
        * Poner el NIT en negrilla
        * Poner el número de orden en negrilla
        
        Mejora la visibilidad de información importante en el ticket impreso.
    """,
    'author': 'SAN MIGUEL MADERA, S.A.',
    'depends': ['point_of_sale'],
    'data': [
       
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_receipt_bold_fields/static/src/css/pos_receipt_bold.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}