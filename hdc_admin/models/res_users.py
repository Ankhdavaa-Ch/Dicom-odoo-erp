from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    _inherit = 'res.users'

    hdc_employee_id = fields.Many2one(
        'hr.employee',
        string='Ажилтан',
        domain="[('user_id', 'in', [False, id])]",
        help='Системийн хэрэглэгчтэй холбох ажилтан.',
    )

    # Upgrade compatibility only: an older installed view still references this field.
    hdc_role_ids = fields.Many2many(
        'res.groups',
        string='Хуучин системийн дүр',
        compute='_compute_legacy_hdc_role_ids',
    )

    hdc_role_id = fields.Many2one(
        'res.groups',
        string='Системийн дүр',
        domain="[('hdc_is_system_role', '=', True)]",
        help='Хэрэглэгчид олгосон үндсэн системийн дүр. Модулийн эрхүүд тухайн дүрээс автоматаар өвлөгдөнө.',
    )
    hdc_role_category_id = fields.Many2one(
        'ir.module.category',
        compute='_compute_hdc_role_category_id',
    )
    @api.depends('hdc_role_id')
    def _compute_legacy_hdc_role_ids(self):
        for user in self:
            user.hdc_role_ids = user.hdc_role_id

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

    def _hdc_role_implied_groups(self, role):
        """Return all module groups inherited by a system role, recursively."""
        result = self.env['res.groups']
        pending = role.implied_ids
        while pending:
            group = pending[0]
            pending -= group
            if group in result:
                continue
            result |= group
            pending |= group.implied_ids - result
        return result

    def _hdc_managed_module_groups(self):
        """Groups controlled exclusively by the HDC system-role matrix."""
        xmlids = [
            'hr.group_hr_user',
            'hr.group_hr_manager',
            'hdc_attendance.group_hdc_attendance_user',
            'hdc_attendance.group_hdc_attendance_manager',
            'hdc_employee_service.group_hdc_employee_service_user',
            'hdc_unit_management.group_hdc_unit_manager',
        ]
        groups = self.env['res.groups']
        for xmlid in xmlids:
            group = self.env.ref(xmlid, raise_if_not_found=False)
            if group:
                groups |= group
        return groups

    def _hdc_permission_allowed(self, code):
        self.ensure_one()
        role = self.hdc_role_id
        if not role:
            return False
        permission = role.hdc_permission_ids.filtered(lambda p: p.code == code)[:1]
        if not permission or not permission.allowed:
            return False
        module_field = {
            'hr': 'hdc_hr_access',
            'attendance': 'hdc_attendance_access',
            'employee_service': 'hdc_employee_service_access',
            'unit_management': 'hdc_unit_management_access',
        }.get(permission.module)
        return bool(module_field and getattr(role, module_field, 'none') != 'none')

    def _hdc_allowed_permission_codes(self):
        self.ensure_one()
        role = self.hdc_role_id
        if not role:
            return set()
        levels = {
            'hr': role.hdc_hr_access,
            'attendance': role.hdc_attendance_access,
            'employee_service': role.hdc_employee_service_access,
            'unit_management': role.hdc_unit_management_access,
        }
        return {
            p.code for p in role.hdc_permission_ids
            if p.allowed and levels.get(p.module, 'none') != 'none'
        }

    def _apply_hdc_role(self):
        system_roles = self._hdc_system_role_groups()
        managed_module_groups = self._hdc_managed_module_groups()
        for user in self:
            # IMPORTANT: system-role groups themselves imply module groups.
            # Therefore copying role.implied_ids back onto the user makes stale
            # module permissions survive even after a module is changed to None.
            # Keep only non-HDC direct groups, then add the selected role. Odoo
            # resolves the role's CURRENT implied_ids dynamically.
            groups = user.groups_id - system_roles - managed_module_groups
            groups |= self.env.ref('base.group_user')
            if user.hdc_role_id:
                groups |= user.hdc_role_id
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
        prepared_vals_list = []
        for vals in vals_list:
            vals = dict(vals)
            employee_id = vals.get('hdc_employee_id')
            if employee_id:
                employee = self.env['hr.employee'].sudo().browse(employee_id).exists()
                if not employee:
                    raise ValidationError('Сонгосон ажилтны бүртгэл олдсонгүй.')
                # res.users creates a linked res.partner first. The partner requires a name,
                # so always populate the user name server-side from the linked employee.
                vals['name'] = employee.name
                if not vals.get('email') and employee.work_email:
                    vals['email'] = employee.work_email
                if not vals.get('phone') and employee.work_phone:
                    vals['phone'] = employee.work_phone
            if not vals.get('name'):
                raise ValidationError('Системийн хэрэглэгч үүсгэхийн өмнө ажилтан сонгоно уу.')
            prepared_vals_list.append(vals)

        users = super().create(prepared_vals_list)
        for user in users:
            if user.hdc_employee_id and user.hdc_employee_id.user_id != user:
                user.hdc_employee_id.sudo().user_id = user.id
        users._apply_hdc_role()
        return users

    def write(self, vals):
        if self.env.context.get('skip_hdc_security'):
            return super().write(vals)

        old_employees = {user.id: user.hdc_employee_id for user in self}
        vals = dict(vals)
        if 'hdc_employee_id' in vals and vals.get('hdc_employee_id'):
            employee = self.env['hr.employee'].sudo().browse(vals['hdc_employee_id']).exists()
            if not employee:
                raise ValidationError('Сонгосон ажилтны бүртгэл олдсонгүй.')
            vals['name'] = employee.name

        result = super().write(vals)

        if 'hdc_employee_id' in vals:
            for user in self:
                old_employee = old_employees.get(user.id)
                if old_employee and old_employee != user.hdc_employee_id and old_employee.user_id == user:
                    old_employee.sudo().user_id = False
                if user.hdc_employee_id and user.hdc_employee_id.user_id != user:
                    user.hdc_employee_id.sudo().user_id = user.id

        if 'hdc_role_id' in vals:
            self._apply_hdc_role()

        return result
