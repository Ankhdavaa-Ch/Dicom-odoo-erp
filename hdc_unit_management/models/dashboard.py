from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HdcEmployeeRequest(models.Model):
    _inherit = 'hdc.employee.request'

    @api.model
    def get_unit_dashboard(self):
        employee = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.uid)], limit=1)
        if not employee or not employee.department_id:
            raise UserError(_('Таны хэрэглэгч ажилтан болон нэгжтэй холбогдоогүй байна.'))

        department = employee.department_id
        managed_departments = self.env['hr.department'].sudo().search([
            ('id', 'child_of', department.id),
            ('active', '=', True),
        ])
        department_ids = managed_departments.ids

        requests = self.sudo().search([
            ('department_id', 'in', department_ids),
            ('state', '!=', 'draft'),
        ], order='create_date desc')

        pending = requests.filtered(
            lambda r: r.state == 'submitted' and r.approver_user_id.id == self.env.uid
        )

        today = fields.Date.context_today(self)
        annual_leave = requests.filtered(
            lambda r: r.request_type == 'annual_leave'
            and r.state == 'approved'
            and fields.Datetime.to_datetime(r.date_from).date() <= today
            and fields.Datetime.to_datetime(r.date_to).date() >= today
        )

        late_records = self.env['hdc.attendance.daily'].sudo().search([
            ('department_id', 'in', department_ids),
            ('attendance_date', '=', today),
            ('status', 'in', ['late', 'late_early']),
        ])

        recent = []
        for req in requests[:10]:
            recent.append({
                'id': req.id,
                'name': req.name,
                'employee': req.employee_id.name or '',
                'department': req.department_id.name or '',
                'request_type': dict(req._fields['request_type'].selection).get(req.request_type, req.request_type),
                'state': dict(req._fields['state'].selection).get(req.state, req.state),
                'current_level': dict(req._fields['current_approval_level'].selection).get(req.current_approval_level, '') if req.current_approval_level else '',
                'approver': req.approver_user_id.name or '',
            })

        return {
            'department_name': department.name,
            'total_request_ids': requests.ids,
            'pending_request_ids': pending.ids,
            'annual_leave_request_ids': annual_leave.ids,
            'late_attendance_ids': late_records.ids,
            'counts': {
                'annual_leave': len(annual_leave),
                'pending': len(pending),
                'late': len(late_records),
            },
            'recent_requests': recent,
        }
