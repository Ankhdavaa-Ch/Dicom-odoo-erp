{
    'name': 'HDC Employee Service',
    'version': '18.0.1.1.0',
    'summary': 'Ажилтны өөртөө үйлчлэх хэсэг',
    'category': 'Human Resources',
    'author': 'HDC',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'hr', 'hdc_hr', 'hdc_attendance', 'hdc_erp_base'],
    'data': [
        'security/employee_service_security.xml',
        'views/my_profile_views.xml',
        'views/employee_service_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hdc_employee_service/static/src/js/my_attendance.js',
            'hdc_employee_service/static/src/xml/my_attendance.xml',
            'hdc_employee_service/static/src/scss/my_attendance.scss',
        ],
    },
    'installable': True,
    'application': False,
}
