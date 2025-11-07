{
    'name': 'Fill Rate Report',
    'version': '17.0.1.0.0',
    'category': 'Inventory',
    'depends': ['employee_purchase_requisition'],
    'data': [
        'security/ir.model.access.csv',
        'views/fill_rate_views.xml',
    ],
    'installable': True,
    'application': False,
}
