from odoo import api, models


# Menu XML id -> detailed permission code.
# Parent module menus are handled from the role's base module level.
MENU_PERMISSION_MAP = {
    'hdc_erp_base.menu_hdc_erp_employee': 'hr.employees',
    'hdc_erp_base.menu_hdc_erp_department': 'hr.departments',
    'hdc_hr.menu_hdc_hr_job_position_list': 'hr.jobs',
    'hdc_hr.menu_hdc_hr_organization': 'hr.organization',
    'hdc_hr.menu_hdc_hr_structure_setup': 'hr.structure_setup',

    'hdc_attendance.menu_hdc_attendance_daily': 'attendance.daily',
    'hdc_attendance.menu_hdc_attendance_raw_log': 'attendance.raw',
    'hdc_attendance.menu_hdc_attendance_pull': 'attendance.pull',
    'hdc_attendance.menu_hdc_attendance_device': 'attendance.devices',

    'hdc_employee_service.menu_hdc_my_profile': 'service.profile',
    'hdc_employee_service.menu_hdc_my_attendance': 'service.attendance',
    'hdc_employee_service.menu_hdc_my_requests': 'service.requests',
    'hdc_employee_service.menu_hdc_requests_to_approve': 'service.unit_requests',

    'hdc_unit_management.menu_hdc_unit_dashboard': 'unit.dashboard',
    'hdc_unit_management.menu_hdc_unit_all_requests': 'unit.all_requests',
    'hdc_unit_management.menu_hdc_unit_pending_requests': 'unit.pending_requests',
}

MODULE_ROOT_MAP = {
    'hdc_erp_base.menu_hdc_erp_hr': 'hr',
    'hdc_erp_base.menu_hdc_erp_attendance': 'attendance',
    'hdc_employee_service.menu_hdc_employee_service_root': 'employee_service',
    'hdc_unit_management.menu_hdc_unit_management_root': 'unit_management',
}

MODULE_FIELD_MAP = {
    'hr': 'hdc_hr_access',
    'attendance': 'hdc_attendance_access',
    'employee_service': 'hdc_employee_service_access',
    'unit_management': 'hdc_unit_management_access',
}


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    def _visible_menu_ids(self, debug=False):
        visible = super()._visible_menu_ids(debug=debug)
        user = self.env.user

        # System administrators keep normal Odoo access.
        if user._is_admin() or not user.hdc_role_id:
            return visible

        role = user.hdc_role_id
        allowed_codes = user._hdc_allowed_permission_codes()
        blocked = set()

        for xmlid, module in MODULE_ROOT_MAP.items():
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            if menu and getattr(role, MODULE_FIELD_MAP[module], 'none') == 'none':
                blocked.add(menu.id)

        for xmlid, code in MENU_PERMISSION_MAP.items():
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            if menu and code not in allowed_codes:
                blocked.add(menu.id)

        # Never call ir.ui.menu.search() from _visible_menu_ids(): Odoo's
        # search_fetch() calls _visible_menu_ids() again and causes recursion.
        # The parent's visibility filtering is enough: load_menus only walks
        # children of menus that remain visible.
        if blocked:
            visible -= self.browse(list(blocked))

        return visible
