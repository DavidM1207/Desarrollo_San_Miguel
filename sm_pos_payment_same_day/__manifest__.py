# -*- coding: utf-8 -*-
{
    'name': 'POS - Cambio de Pagos Mismo Día',
    'version': '17.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Botón para cambiar pagos solo del mismo día',
    'description': """
        Agrega un botón adicional que permite cambiar métodos de pago
        únicamente para órdenes del mismo día.
        
        Extiende el módulo pos_payment_change existente.
    """,
    'author': 'SAN MIGUEL MADERA, S.A.',
    'depends': [
        'pos_payment_change',  # Módulo original tercerisado
    ],
    'data': [
        'views/pos_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}