from odoo import fields, models


class HdcLoginLog(models.Model):
    _name = 'hdc.login.log'
    _description = 'HDC System Login Log'
    _order = 'login_at desc, id desc'

    user_id = fields.Many2one('res.users', string='Хэрэглэгч', required=True, index=True, ondelete='cascade')
    login = fields.Char(string='Нэвтрэх нэр', required=True, index=True)
    login_at = fields.Datetime(string='Нэвтэрсэн огноо', required=True, default=fields.Datetime.now, index=True)
    ip_address = fields.Char(string='IP хаяг')
    user_agent = fields.Char(string='Browser / төхөөрөмж')
