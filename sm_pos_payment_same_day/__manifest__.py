# -*- coding: utf-8 -*-
{
    'name': 'POS - Cambio de Pagos Mismo Día',
    'version': '17.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Botón para cambiar pagos solo del mismo día con solicitud de aprobación',
    'description': """
        Agrega un botón adicional que permite cambiar métodos de pago
        únicamente para órdenes del mismo día.
        
        Si se seleccionan métodos de pago que requieren aprobación
        (Transferencia, Nota de crédito, Devolución), se crea una
        solicitud de aprobación automáticamente.
        
        Extiende los módulos pos_payment_change y pt_pos_payment_approval.
    """,
    'author': 'SAN MIGUEL MADERA, S.A.',
    'depends': [
        'pos_payment_change',        # Módulo original de cambio de pagos
        'pt_pos_payment_approval',   # Módulo de aprobaciones
    ],
    'data': [
        'views/pos_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}