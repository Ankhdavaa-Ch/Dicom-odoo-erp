{
    'name': 'HDC Attendance',
    'version': '18.0.1.0.0',
    'summary': 'ХДК цаг бүртгэл болон ZKTeco ADMS integration',
    'category': 'Human Resources/Attendances',
    'author': 'HDC',
    'license': 'LGPL-3',

    'depends': [
        'hr',
        'mail',
        'hdc_hr',
    ],

    'data': [
        'security/attendance_security.xml',
        'security/ir.model.access.csv',

        'views/hr_employee_views.xml',
        'wizard/attendance_pull_wizard_views.xml',
        'views/attendance_device_views.xml',
        'views/attendance_raw_log_views.xml',

        # ЭНЭ МӨР ЗААВАЛ БАЙНА
        'views/attendance_daily_views.xml',

        # MENU ХАМГИЙН СҮҮЛД
        'views/attendance_menu.xml',

        
    ],

    'installable': True,
    'application': False,
}