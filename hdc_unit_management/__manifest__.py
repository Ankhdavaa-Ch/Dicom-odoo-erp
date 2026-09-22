{
    'name': 'HDC Unit Management',
    'version': '18.0.1.0.0',
    'summary': 'Нэгжийн удирдлагын хяналтын самбар',
    'category': 'Human Resources',
    'author': 'HDC',
    'license': 'LGPL-3',
    'depends': ['web', 'hr', 'hdc_employee_service', 'hdc_attendance', 'hdc_erp_base'],
    'data': [
        'security/unit_management_security.xml',
        'views/unit_management_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hdc_unit_management/static/src/js/dashboard.js',
            'hdc_unit_management/static/src/xml/dashboard.xml',
            'hdc_unit_management/static/src/scss/dashboard.scss',
        ],
    },
    'installable': True,
    'application': False,
}
