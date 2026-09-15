from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

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
