from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    attendance_device_user_id = fields.Char(
        string='Ирцийн төхөөрөмжийн ID',
        index=True,
        copy=False,
        help='ZKTeco төхөөрөмж дээрх ажилтны User ID',
    )

    attendance_device_id = fields.Many2one(
        'hdc.attendance.device',
        string='Үндсэн ирцийн төхөөрөмж',
        ondelete='set null',
    )

    def write(self, vals):
        result = super().write(vals)
        if 'attendance_device_user_id' in vals or 'attendance_device_id' in vals:
            RawLog = self.env['hdc.attendance.raw.log'].sudo()
            changed = False
            for employee in self:
                code = (employee.attendance_device_user_id or '').strip()
                if not code:
                    continue
                domain = [('device_user_id', '=', code)]
                if employee.attendance_device_id:
                    domain.append(('device_id', '=', employee.attendance_device_id.id))
                # Never auto-assign when multiple employees share a code.
                matches = self.sudo().search([
                    ('attendance_device_user_id', '=', code),
                ])
                if len(matches) != 1:
                    continue
                logs = RawLog.search(domain + [('employee_id', '=', False)])
                if logs:
                    logs.write({'employee_id': employee.id, 'processed': False})
                    changed = True
            if changed:
                self.env['hdc.attendance.daily'].sudo().process_raw_logs()
        return result
