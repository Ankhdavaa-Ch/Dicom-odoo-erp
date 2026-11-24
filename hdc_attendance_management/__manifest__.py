{
    'name': 'Цаг бүртгэлийн удирдлага',
    'version': '18.0.1.3.0',
    'depends': ['hdc_erp_base', 'hdc_attendance', 'hdc_employee_service', 'web'],
    'data': ['security/ir.model.access.csv', 'data/schedule_types.xml', 'views/reference.xml', 'views/menu.xml'],
    'assets': {'web.assets_backend': [
        'hdc_attendance_management/static/src/dashboard.js',
        'hdc_attendance_management/static/src/dashboard.xml',
    ]},
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}
