{
    'name': 'Цаг бүртгэлийн удирдлага',
    'version': '18.0.1.0.0',
    'depends': ['hdc_attendance', 'hdc_employee_service', 'web'],
    'data': ['views/menu.xml'],
    'assets': {'web.assets_backend': [
        'hdc_attendance_management/static/src/dashboard.js',
        'hdc_attendance_management/static/src/dashboard.xml',
    ]},
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}
