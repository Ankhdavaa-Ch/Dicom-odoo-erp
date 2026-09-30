from odoo import api, fields, models


ACCESS_LEVELS = [
    ('none', 'Эрхгүй'),
    ('read', 'Харах'),
    ('work', 'Ажиллах'),
    ('manage', 'Удирдах'),
]


class ResGroups(models.Model):
    _inherit = 'res.groups'

    hdc_is_system_role = fields.Boolean(string='ХДК системийн дүр', default=False, index=True)
    hdc_hr_access = fields.Selection(ACCESS_LEVELS, string='Хүний нөөц', default='none', required=True)
    hdc_attendance_access = fields.Selection(ACCESS_LEVELS, string='Ирц', default='none', required=True)
    hdc_employee_service_access = fields.Selection(ACCESS_LEVELS, string='Ажилтны үйлчилгээ', default='none', required=True)
    hdc_unit_management_access = fields.Selection(ACCESS_LEVELS, string='Нэгжийн удирдлага', default='none', required=True)
    hdc_permission_ids = fields.One2many(
        'hdc.role.permission', 'role_id', string='Нарийвчилсан эрх'
    )

    def _hdc_permission_catalog(self):
        return [
            ('hr', 'hr.employees', 'Ажилтнууд', 'menu', 10, None),
            ('hr', 'hr.employees.read', 'Харах', 'action', 11, 'hr.employees'),
            ('hr', 'hr.employees.create', 'Шинэ ажилтан', 'action', 12, 'hr.employees'),
            ('hr', 'hr.employees.write', 'Засах', 'action', 13, 'hr.employees'),
            ('hr', 'hr.departments', 'Газар / хэлтэс', 'menu', 20, None),
            ('hr', 'hr.jobs', 'Албан тушаал', 'menu', 30, None),
            ('hr', 'hr.organization', 'Байгууллагын бүтэц', 'menu', 40, None),
            ('hr', 'hr.structure_setup', 'Бүтцийн тохиргоо', 'menu', 50, None),

            ('attendance', 'attendance.daily', 'Өдрийн ирц', 'menu', 10, None),
            ('attendance', 'attendance.daily.read', 'Харах', 'action', 11, 'attendance.daily'),
            ('attendance', 'attendance.daily.work', 'Ирц боловсруулах', 'action', 12, 'attendance.daily'),
            ('attendance', 'attendance.raw', 'Ирцийн бүртгэл', 'menu', 20, None),
            ('attendance', 'attendance.raw.read', 'Харах', 'action', 21, 'attendance.raw'),
            ('attendance', 'attendance.pull', 'Ирц татах', 'action', 30, None),
            ('attendance', 'attendance.devices', 'Төхөөрөмжүүд', 'menu', 40, None),

            ('employee_service', 'service.profile', 'Миний анкет', 'menu', 10, None),
            ('employee_service', 'service.attendance', 'Миний ирц', 'menu', 20, None),
            ('employee_service', 'service.requests', 'Миний хүсэлтүүд', 'menu', 30, None),
            ('employee_service', 'service.requests.read', 'Харах', 'action', 31, 'service.requests'),
            ('employee_service', 'service.requests.create', 'Шинэ хүсэлт', 'action', 32, 'service.requests'),
            ('employee_service', 'service.requests.write', 'Засах', 'action', 33, 'service.requests'),
            ('employee_service', 'service.requests.submit', 'Илгээх', 'action', 34, 'service.requests'),
            ('employee_service', 'service.unit_requests', 'Нэгжийн хүсэлтүүд', 'menu', 40, None),
            ('employee_service', 'service.unit_requests.approve', 'Батлах', 'action', 41, 'service.unit_requests'),
            ('employee_service', 'service.unit_requests.reject', 'Буцаах', 'action', 42, 'service.unit_requests'),

            ('unit_management', 'unit.dashboard', 'Хяналтын самбар', 'menu', 10, None),
            ('unit_management', 'unit.all_requests', 'Нийт хүсэлтүүд', 'menu', 20, None),
            ('unit_management', 'unit.pending_requests', 'Батлах хүсэлтүүд', 'menu', 30, None),
            ('unit_management', 'unit.pending_requests.approve', 'Батлах', 'action', 31, 'unit.pending_requests'),
            ('unit_management', 'unit.pending_requests.reject', 'Буцаах', 'action', 32, 'unit.pending_requests'),
            ('unit_management', 'unit.employees', 'Нэгжийн ажилтнууд', 'menu', 40, None),
            ('unit_management', 'unit.attendance', 'Ирцийн хяналт', 'menu', 50, None),
        ]

    def action_generate_hdc_permissions(self):
        Permission = self.env['hdc.role.permission'].sudo()
        for role in self:
            existing = {p.code: p for p in role.hdc_permission_ids}
            created = {}
            for module, code, name, ptype, sequence, parent_code in role._hdc_permission_catalog():
                parent = existing.get(parent_code) or created.get(parent_code)
                values = {
                    'role_id': role.id, 'module': module, 'code': code,
                    'name': name, 'permission_type': ptype, 'sequence': sequence,
                    'parent_id': parent.id if parent else False,
                }
                if code in existing:
                    existing[code].write(values)
                    created[code] = existing[code]
                else:
                    created[code] = Permission.create(values)
        return True

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
            'hdc_unit_management.group_hdc_unit_manager',
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
        unit_manager = self.env.ref('hdc_unit_management.group_hdc_unit_manager', raise_if_not_found=False)
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

            if role.hdc_unit_management_access != 'none' and unit_manager:
                implied |= unit_manager

            role.with_context(skip_hdc_role_sync=True).implied_ids = [(6, 0, implied.ids)]

            # Existing users with this role must receive changed module rights
            # immediately (not only newly assigned users).
            users = self.env['res.users'].sudo().search([('hdc_role_id', '=', role.id)])
            if users:
                users._apply_hdc_role()

    @api.model_create_multi
    def create(self, vals_list):
        groups = super().create(vals_list)
        groups._sync_hdc_module_permissions()
        return groups

    def write(self, vals):
        result = super().write(vals)
        security_fields = {'hdc_hr_access', 'hdc_attendance_access', 'hdc_employee_service_access', 'hdc_unit_management_access'}
        if not self.env.context.get('skip_hdc_role_sync') and security_fields.intersection(vals):
            self._sync_hdc_module_permissions()
        return result
