{
    'name': 'HDC ERP',
    'version': '18.0.1.0.0',
    'summary': 'ХДК ERP системийн үндсэн цэс',
    'category': 'Administration',
    'author': 'HDC',
    'license': 'LGPL-3',

    'depends': [
        'base',
        'web',
        'hr',

        'hdc_hr',
        'hdc_attendance',
    ],

    'data': [
        'views/erp_menu.xml',
    ],

    'installable': True,
    'application': True,
}