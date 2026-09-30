from odoo import api, fields, models


MODULES = [
    ('hr', 'Хүний нөөц'),
    ('attendance', 'Ирц'),
    ('employee_service', 'Ажилтны үйлчилгээ'),
    ('unit_management', 'Нэгжийн удирдлага'),
]


class HdcRolePermission(models.Model):
    _name = 'hdc.role.permission'
    _description = 'ХДК системийн дүрийн нарийвчилсан эрх'
    _order = 'module, sequence, id'

    role_id = fields.Many2one('res.groups', string='Системийн дүр', required=True, ondelete='cascade', index=True)
    module = fields.Selection(MODULES, string='Модуль', required=True, index=True)
    sequence = fields.Integer(default=10)
    parent_id = fields.Many2one('hdc.role.permission', string='Эцэг эрх', ondelete='cascade', index=True)
    child_ids = fields.One2many('hdc.role.permission', 'parent_id', string='Дэд эрхүүд')
    name = fields.Char(string='Цэс / үйлдэл', required=True)
    code = fields.Char(string='Код', required=True)
    permission_type = fields.Selection([
        ('menu', 'Цэс'),
        ('action', 'Үйлдэл'),
    ], string='Төрөл', default='menu', required=True)
    allowed = fields.Boolean(string='Олгосон эрх', default=False)

    _sql_constraints = [
        ('role_code_unique', 'unique(role_id, code)', 'Энэ эрх тухайн системийн дүр дээр давхар бүртгэгдсэн байна.'),
    ]

    @api.onchange('allowed')
    def _onchange_allowed(self):
        for rec in self:
            if rec.allowed and rec.parent_id:
                rec.parent_id.allowed = True
            if not rec.allowed:
                rec.child_ids.allowed = False
