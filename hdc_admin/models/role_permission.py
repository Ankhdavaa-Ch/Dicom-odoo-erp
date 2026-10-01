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

    def _normalize_tree(self):
        # A selected child always selects its parent; clearing a parent clears children.
        for rec in self:
            if rec.allowed and rec.parent_id and not rec.parent_id.allowed:
                rec.parent_id.with_context(skip_hdc_permission_sync=True).write({'allowed': True})
            elif not rec.allowed and rec.child_ids.filtered('allowed'):
                rec.child_ids.with_context(skip_hdc_permission_sync=True).write({'allowed': False})

    def _refresh_role_users(self):
        roles = self.mapped('role_id')
        users = self.env['res.users'].sudo().search([('hdc_role_id', 'in', roles.ids)])
        if users:
            users._apply_hdc_role()
        # Menu visibility is cached by Odoo; clear it so the saved rights are effective immediately.
        self.env['ir.ui.menu'].clear_caches()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.context.get('skip_hdc_permission_sync'):
            records._normalize_tree()
            records._refresh_role_users()
        return records

    def write(self, vals):
        result = super().write(vals)
        if not self.env.context.get('skip_hdc_permission_sync') and 'allowed' in vals:
            self._normalize_tree()
            self._refresh_role_users()
        return result

    def unlink(self):
        roles = self.mapped('role_id')
        result = super().unlink()
        users = self.env['res.users'].sudo().search([('hdc_role_id', 'in', roles.ids)])
        if users:
            users._apply_hdc_role()
        self.env['ir.ui.menu'].clear_caches()
        return result
