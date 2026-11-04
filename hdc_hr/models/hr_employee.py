from odoo import api, models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.model_create_multi
    def create(self, vals_list):
        """Keep Odoo 18 employee creation safe when a custom/client view omits name.

        Odoo's resource preparation expects the key to exist in every create vals.
        We still reject a genuinely empty employee name with a clear message through
        the standard required-field validation instead of crashing with KeyError.
        """
        for vals in vals_list:
            vals.setdefault('name', False)
        return super().create(vals_list)

    employee_code = fields.Char(
        string='Ажилтны код'
    )

    family_name = fields.Char(
        string='Ургийн овог'
    )

    ethnicity = fields.Char(
        string='Яс үндэс'
    )

    birth_district = fields.Char(
        string='Төрсөн сум/дүүрэг'
    )

    family_member_count = fields.Integer(
        string='Ам бүлийн тоо'
    )

    private_district = fields.Char(
        string='Сум/дүүрэг'
    )

    private_khoroo = fields.Char(
        string='Хороо/баг'
    )

    family_ids = fields.One2many(
        'hr.employee.family',
        'employee_id',
        string='Гэр бүлийн мэдээлэл'
    )

    education_ids = fields.One2many(
        'hr.employee.education',
        'employee_id',
        string='Боловсрол'
    )

    qualification_ids = fields.One2many(
        'hr.employee.qualification',
        'employee_id',
        string='Мэргэшил'
    )

    employment_history_ids = fields.One2many(
        'hr.employee.employment.history',
        'employee_id',
        string='Хөдөлмөр эрхлэлт'
    )
    def action_create_internal_users_from_active_employees(self):
        """Create active internal users for all active employees with unique work emails.

        Explicit admin-triggered action; never runs during module installation.
        """
        from collections import Counter
        from odoo.exceptions import AccessError
        from odoo import _
        from odoo.exceptions import UserError

        if not self.env.user.has_group('base.group_system'):
            raise AccessError(_("Зөвхөн системийн админ хэрэглэгч үүсгэх боломжтой."))

        Employee = self.env['hr.employee'].sudo().with_context(active_test=False)
        User = self.env['res.users'].sudo().with_context(active_test=False)
        employees = Employee.search([('active', '=', True)])
        email_counts = Counter(
            (e.work_email or '').strip().lower()
            for e in employees if (e.work_email or '').strip()
        )
        internal_group = self.env.ref('base.group_user')
        created, existing, missing, duplicates, conflicts = [], [], [], [], []
        for employee in employees:
            email = (employee.work_email or '').strip()
            if not email:
                missing.append(employee.name)
                continue
            if email_counts[email.lower()] != 1:
                duplicates.append(employee.name)
                continue
            if employee.user_id:
                existing.append(employee.name)
                continue
            users = User.search([('login', '=ilike', email)])
            if users:
                # Do not attach an unrelated existing login to an employee.
                conflicts.append(employee.name)
                continue
            user = User.with_context(no_reset_password=True).create({
                'name': employee.name,
                'login': email,
                'email': email,
                'active': True,
                'groups_id': [(6, 0, [internal_group.id])],
                'company_id': employee.company_id.id or self.env.company.id,
                'company_ids': [(6, 0, [employee.company_id.id or self.env.company.id])],
            })
            employee.write({'user_id': user.id})
            created.append(employee.name)

        message = _(
            "Үүсгэсэн: %(created)s\\nӨмнө холбогдсон: %(existing)s\\n"
            "Имэйлгүй: %(missing)s\\nДавхардсан имэйл: %(duplicates)s\\n"
            "Өөр хэрэглэгчид бүртгэлтэй имэйл: %(conflicts)s\\n"
            "Шинэ хэрэглэгчид нууц үг олгоогүй. Нууц үг тохируулах урилгыг админ тусад нь илгээнэ."
        ) % {
            'created': len(created), 'existing': len(existing),
            'missing': len(missing), 'duplicates': len(duplicates),
            'conflicts': len(conflicts),
        }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'title': _('Системийн хэрэглэгч үүсгэлт'), 'message': message,
                       'type': 'success', 'sticky': True},
        }
