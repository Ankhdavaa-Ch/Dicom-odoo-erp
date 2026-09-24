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

    'assets': {
        'web.assets_backend': [
            'hdc_erp_base/static/src/js/form_navigation.js',
            'hdc_erp_base/static/src/xml/form_buttons.xml',
        ],
    },

    'installable': True,
    'application': True,
}