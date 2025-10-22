{
    'name': 'Detalle Notas de Crédito',
    'version': '17.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Visualización detallada de notas de crédito por aplicar',
    'description': """
        Módulo para visualizar y gestionar notas de crédito individuales
        - Vista detallada de apuntes contables de notas de crédito
        - Conciliación individual de notas de crédito
        - Seguimiento de aplicación de notas de crédito
    """,
    'author': 'SAN MIGUEL, S.A.',
    
    'depends': [
        'base',
        'account',
        'point_of_sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/credit_note_detail_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}