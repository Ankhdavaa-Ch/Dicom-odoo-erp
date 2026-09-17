{
    'name': 'HDC Employee Service',
    'version': '18.0.1.2.0',
    'summary': 'Ажилтны өөртөө үйлчлэх хэсэг',
    'category': 'Human Resources',
    'author': 'HDC',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'hr', 'mail', 'hdc_hr', 'hdc_attendance', 'hdc_erp_base'],
    'data': [
        'security/employee_service_security.xml',
        'security/ir.model.access.csv',
        'security/employee_request_rules.xml',
        'data/employee_request_sequence.xml',
        'views/my_profile_views.xml',
        'views/hr_department_views.xml',
        'views/employee_request_views.xml',
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
