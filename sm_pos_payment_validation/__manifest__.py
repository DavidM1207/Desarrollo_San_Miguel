# -*- coding: utf-8 -*-
{
    'name': 'POS Payment Method Validation',
    'version': '17.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Validación y control de cambios en métodos de pago del POS',
    'description': """
        Control de Métodos de Pago en POS
        ==================================
        * Requiere aprobación de gerente para cambiar método de pago
        * Alerta al seleccionar método de pago en efectivo
        * Registro de cambios de método de pago
        * Permisos específicos para aprobación
    """,
    'author': 'SAN MIGUEL MADERA, S.A.',
    'depends': ['point_of_sale'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
    ],
    'assets': {
    'point_of_sale._assets_pos': [
        'pos_payment_validation/static/src/js/models.js',
        'pos_payment_validation/static/src/js/payment_screen.js',
        'pos_payment_validation/static/src/xml/payment_screen.xml',
        'pos_payment_validation/static/src/scss/payment_screen.scss',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}