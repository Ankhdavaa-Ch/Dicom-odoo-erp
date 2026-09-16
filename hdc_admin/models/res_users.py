from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    hdc_employee_id = fields.Many2one(
        'hr.employee',
        string='Ажилтан',
        domain="[('user_id', 'in', [False, id])]",
        help='Системийн хэрэглэгчтэй холбох ажилтан.',
    )

    hdc_role_ids = fields.Many2many(
        'res.groups',
        string='Системийн дүр',
        compute='_compute_hdc_role_ids',
        inverse='_inverse_hdc_role_ids',
        help='ХДК ERP системийн хэрэглэгчид олгосон дүрүүд.',
    )

    def _hdc_role_groups(self):
        xmlids = [
            'hdc_admin.group_hdc_basic_user',
            'hdc_admin.group_hdc_hr_user',
            'hdc_admin.group_hdc_hr_manager',
            'hdc_admin.group_hdc_attendance_user',
            'hdc_admin.group_hdc_attendance_manager',
            'hdc_admin.group_hdc_system_admin',
        ]
        groups = self.env['res.groups']
        for xmlid in xmlids:
            group = self.env.ref(xmlid, raise_if_not_found=False)
            if group:
                groups |= group
        return groups

    @api.depends('groups_id')
    def _compute_hdc_role_ids(self):
        role_groups = self._hdc_role_groups()
        for user in self:
            user.hdc_role_ids = user.groups_id & role_groups

    def _inverse_hdc_role_ids(self):
        role_groups = self._hdc_role_groups()
        for user in self:
            selected_roles = user.hdc_role_ids & role_groups
            other_groups = user.groups_id - role_groups
            user.groups_id = [(6, 0, (other_groups | selected_roles).ids)]

    @api.onchange('hdc_employee_id')
    def _onchange_hdc_employee_id(self):
        for user in self:
            if user.hdc_employee_id:
                user.name = user.hdc_employee_id.name
                if user.hdc_employee_id.work_email:
                    user.email = user.hdc_employee_id.work_email
                if user.hdc_employee_id.work_phone:
                    user.phone = user.hdc_employee_id.work_phone

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        for user in users:
            if user.hdc_employee_id and user.hdc_employee_id.user_id != user:
                user.hdc_employee_id.sudo().user_id = user.id
        return users

    def write(self, vals):
        old_employees = {user.id: user.hdc_employee_id for user in self}
        result = super().write(vals)
        if 'hdc_employee_id' in vals:
            for user in self:
                old_employee = old_employees.get(user.id)
                if old_employee and old_employee != user.hdc_employee_id and old_employee.user_id == user:
                    old_employee.sudo().user_id = False
                if user.hdc_employee_id and user.hdc_employee_id.user_id != user:
                    user.hdc_employee_id.sudo().user_id = user.id
        return result
