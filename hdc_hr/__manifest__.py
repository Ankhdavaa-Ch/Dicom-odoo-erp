{
    'name': 'HDC Human Resources',
    'version': '18.0.1.0.0',
    'summary': 'ХДК-ийн хүний нөөцийн нэмэлт модуль',
    'category': 'Human Resources',
    'author': 'HDC',
    'license': 'LGPL-3',
    'depends': ['hr', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_employee_views.xml',
        'views/hr_structure_views.xml',
        'views/hr_structure_node_views.xml',
        'views/hr_job_views.xml',
        'views/hr_structure_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hdc_hr/static/src/scss/organization_chart.scss',
        ],
    },
    'installable': True,
    'application': True,
}