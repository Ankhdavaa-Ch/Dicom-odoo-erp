from odoo import api, fields, models


ACCESS_LEVELS = [
    ('none', 'Эрхгүй'),
    ('read', 'Харах'),
    ('work', 'Ажиллах'),
    ('manage', 'Удирдах'),
]


class ResGroups(models.Model):
    _inherit = 'res.groups'

    hdc_hr_access = fields.Selection(ACCESS_LEVELS, string='Хүний нөөц', default='none', required=True)
    hdc_attendance_access = fields.Selection(ACCESS_LEVELS, string='Ирц', default='none', required=True)
    hdc_employee_service_access = fields.Selection(ACCESS_LEVELS, string='Ажилтны үйлчилгээ', default='none', required=True)

    def _is_hdc_system_role(self):
        category = self.env.ref('hdc_admin.module_category_hdc_roles', raise_if_not_found=False)
        return bool(category and self.category_id == category)

    def _hdc_module_groups(self):
        groups = self.env['res.groups']
        for xmlid in [
            'hr.group_hr_user',
            'hr.group_hr_manager',
            'hdc_attendance.group_hdc_attendance_user',
            'hdc_attendance.group_hdc_attendance_manager',
            'hdc_employee_service.group_hdc_employee_service_user',
        ]:
            group = self.env.ref(xmlid, raise_if_not_found=False)
            if group:
                groups |= group
        return groups

    def _sync_hdc_module_permissions(self):
        hr_user = self.env.ref('hr.group_hr_user', raise_if_not_found=False)
        hr_manager = self.env.ref('hr.group_hr_manager', raise_if_not_found=False)
        attendance_user = self.env.ref('hdc_attendance.group_hdc_attendance_user', raise_if_not_found=False)
        attendance_manager = self.env.ref('hdc_attendance.group_hdc_attendance_manager', raise_if_not_found=False)
        employee_service_user = self.env.ref('hdc_employee_service.group_hdc_employee_service_user', raise_if_not_found=False)
        module_groups = self._hdc_module_groups()

        for role in self:
            if not role._is_hdc_system_role():
                continue

            implied = role.implied_ids - module_groups

            if role.hdc_hr_access in ('read', 'work') and hr_user:
                implied |= hr_user
            elif role.hdc_hr_access == 'manage' and hr_manager:
                implied |= hr_manager

            if role.hdc_attendance_access in ('read', 'work') and attendance_user:
                implied |= attendance_user
            elif role.hdc_attendance_access == 'manage' and attendance_manager:
                implied |= attendance_manager

            if role.hdc_employee_service_access != 'none' and employee_service_user:
                implied |= employee_service_user

            role.with_context(skip_hdc_role_sync=True).implied_ids = [(6, 0, implied.ids)]

    @api.model_create_multi
    def create(self, vals_list):
        groups = super().create(vals_list)
        groups._sync_hdc_module_permissions()
        return groups

    def write(self, vals):
        result = super().write(vals)
        security_fields = {'hdc_hr_access', 'hdc_attendance_access', 'hdc_employee_service_access'}
        if not self.env.context.get('skip_hdc_role_sync') and security_fields.intersection(vals):
            self._sync_hdc_module_permissions()
        return result
