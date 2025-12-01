# tracker/__manifest__.py
# -*- coding: utf-8 -*-
{
    'name': 'Tracker - Seguimiento de Proyectos',
    'version': '17.0.1.0.5',
    'category': 'Project',
    'summary': 'Seguimiento de proyectos con control de tiempo y servicios',
    'description': """
        Módulo de seguimiento de proyectos que permite:
        - Control de servicios desde ventas y facturas
        - Asignación de empleados a tareas
        - Medición de tiempos por operación
        - Control por tiendas (cuentas analíticas)
        - KPIs de fecha prometida vs entregada
    """,
    'author': 'SAN MIGUEL MADERA, S.A.',
     
    'license': 'LGPL-3',
    'depends': [
        'base',
        'sale_management',
        'account',
        'mrp',
        'hr',
        'analytic',
    ],
     'data': [
        'security/tracker_security.xml',
        'security/ir.model.access.csv',
        'data/tracker_data.xml',
        'views/tracker_task_views.xml',
        'views/tracker_project_views.xml',
        'views/tracker_timesheet_views.xml',
        'views/tracker_employee_views.xml',
        'views/tracker_menus.xml',
        'views/tracker_reports.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}