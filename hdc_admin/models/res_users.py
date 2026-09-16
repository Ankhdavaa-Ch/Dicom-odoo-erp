from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    hdc_employee_id = fields.Many2one(
        'hr.employee',
        string='Ажилтан',
        domain="[('user_id', 'in', [False, id])]",
        help='Системийн хэрэглэгчтэй холбох ажилтан.',
    )

    hdc_role_id = fields.Many2one(
        'res.groups',
        string='Системийн дүр',
        domain="[('category_id', '=', hdc_role_category_id)]",
        help='Ажилтны байгууллагын үндсэн системийн дүр. Нэг хэрэглэгч нэг үндсэн дүртэй байна.',
    )
    hdc_role_category_id = fields.Many2one(
        'ir.module.category',
        compute='_compute_hdc_role_category_id',
    )

    hdc_hr_access = fields.Selection(
        [('none', 'Эрхгүй'), ('read', 'Харах'), ('work', 'Ажиллах'), ('manage', 'Удирдах')],
        string='Хүний нөөц',
        default='none',
        required=True,
    )
    hdc_attendance_access = fields.Selection(
        [('none', 'Эрхгүй'), ('read', 'Харах'), ('work', 'Ажиллах'), ('manage', 'Удирдах')],
        string='Ирц',
        default='none',
        required=True,
    )

    @api.depends_context('uid')
    def _compute_hdc_role_category_id(self):
        category = self.env.ref('hdc_admin.module_category_hdc_roles', raise_if_not_found=False)
        for user in self:
            user.hdc_role_category_id = category

    def _hdc_system_role_groups(self):
        xmlids = [
            'hdc_admin.group_hdc_ceo',
            'hdc_admin.group_hdc_department_director',
            'hdc_admin.group_hdc_section_director',
            'hdc_admin.group_hdc_senior_specialist',
            'hdc_admin.group_hdc_specialist',
            'hdc_admin.group_hdc_finance',
            'hdc_admin.group_hdc_system_admin',
        ]
        groups = self.env['res.groups']
        for xmlid in xmlids:
            group = self.env.ref(xmlid, raise_if_not_found=False)
            if group:
                groups |= group
        return groups

    def _hdc_module_groups(self):
        xmlids = [
            'hr.group_hr_user',
            'hr.group_hr_manager',
            'hdc_attendance.group_hdc_attendance_user',
            'hdc_attendance.group_hdc_attendance_manager',
        ]
        groups = self.env['res.groups']
        for xmlid in xmlids:
            group = self.env.ref(xmlid, raise_if_not_found=False)
            if group:
                groups |= group
        return groups

    def _apply_hdc_security(self):
        system_roles = self._hdc_system_role_groups()
        module_groups = self._hdc_module_groups()
        hr_user = self.env.ref('hr.group_hr_user', raise_if_not_found=False)
        hr_manager = self.env.ref('hr.group_hr_manager', raise_if_not_found=False)
        attendance_user = self.env.ref('hdc_attendance.group_hdc_attendance_user', raise_if_not_found=False)
        attendance_manager = self.env.ref('hdc_attendance.group_hdc_attendance_manager', raise_if_not_found=False)

        for user in self:
            groups = user.groups_id - system_roles - module_groups
            groups |= self.env.ref('base.group_user')

            if user.hdc_role_id:
                groups |= user.hdc_role_id

            if user.hdc_hr_access in ('read', 'work') and hr_user:
                groups |= hr_user
            elif user.hdc_hr_access == 'manage' and hr_manager:
                groups |= hr_manager

            if user.hdc_attendance_access in ('read', 'work') and attendance_user:
                groups |= attendance_user
            elif user.hdc_attendance_access == 'manage' and attendance_manager:
                groups |= attendance_manager

            user.with_context(skip_hdc_security=True).groups_id = [(6, 0, groups.ids)]

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
        users._apply_hdc_security()
        return users

    def write(self, vals):
        if self.env.context.get('skip_hdc_security'):
            return super().write(vals)

        old_employees = {user.id: user.hdc_employee_id for user in self}
        result = super().write(vals)

        if 'hdc_employee_id' in vals:
            for user in self:
                old_employee = old_employees.get(user.id)
                if old_employee and old_employee != user.hdc_employee_id and old_employee.user_id == user:
                    old_employee.sudo().user_id = False
                if user.hdc_employee_id and user.hdc_employee_id.user_id != user:
                    user.hdc_employee_id.sudo().user_id = user.id

        security_fields = {'hdc_role_id', 'hdc_hr_access', 'hdc_attendance_access'}
        if security_fields.intersection(vals):
            self._apply_hdc_security()

        return result
