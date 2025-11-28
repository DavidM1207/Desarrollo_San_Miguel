# -*- coding: utf-8 -*-
{
    'name': 'POS - Cambio de Pagos Mismo Día',
    'version': '17.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Botón para cambiar pagos solo del mismo día con solicitud de aprobación',
    'description': """
        Agrega un botón adicional que permite cambiar métodos de pago
        únicamente para órdenes del mismo día.
        
        Características:
        - Validación de fecha (solo órdenes del mismo día)
        - Wizard de solicitud de aprobación para métodos específicos
        - Replica funcionalidad del wizard del POS en el backend
        - Compatible con el módulo de aprobaciones existente
        
        Cuando se seleccionan métodos de pago que requieren aprobación
        (configurados con is_valid_for_payment_approval_request = True),
        se abre un wizard para:
        - Buscar o crear documento de pago
        - Ingresar cantidad del comprobante
        - Especificar cantidad a utilizar
        - Adjuntar comprobante
        
        El botón original "Cambiar pagos" mantiene su funcionalidad normal.
    """,
    'author': 'SAN MIGUEL MADERA, S.A.',
    
    'depends': [
        'pos_payment_change',        # Módulo original de cambio de pagos
        'pt_pos_payment_approval',   # Módulo de aprobaciones
    ],
    'data': [
       
        
        # Vistas (orden importante: wizards primero)
        'views/pos_payment_approval_create_wizard_views.xml',
        'views/pos_order_views.xml',
    ],
     'assets': {
        'point_of_sale._assets_pos': [
            'sm_pos_payment_same_day/static/src/app/request_wizard_override.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}