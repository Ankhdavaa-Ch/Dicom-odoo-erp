{
    'name': 'HDC Admin',
    'version': '18.0.1.0.0',
    'summary': 'ХДК ERP системийн админ удирдлага ба нэвтрэлтийн лог',
    'category': 'Administration',
    'author': 'HDC',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'hdc_erp_base'],
    'data': [
        'security/ir.model.access.csv',
        'views/admin_views.xml',
        'views/admin_menu.xml',
    ],
    'installable': True,
    'application': False,
}
