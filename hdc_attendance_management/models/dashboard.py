from datetime import datetime, timedelta, timezone
from collections import defaultdict
from odoo import api, models
from odoo.exceptions import AccessError

class AttendanceDashboard(models.Model):
    _inherit = 'hdc.attendance.daily'

    @api.model
    def management_dashboard(self, month=None):
        if not (self.env.user.has_group('hdc_attendance.group_hdc_attendance_manager') or self.env.user.has_group('base.group_system')):
            raise AccessError('Цаг бүртгэлийн удирдлагын эрх шаардлагатай.')
        today = datetime.now(timezone(timedelta(hours=8))).date()
        start = datetime.strptime(month, '%Y-%m').date() if month else today.replace(day=1)
        end = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        yesterday = today - timedelta(days=1)
        employees = self.env['hr.employee'].sudo().search([('company_id', 'in', self.env.companies.ids), ('active', '=', True)])
        daily = self.sudo().search([('employee_id', 'in', employees.ids), ('attendance_date', '>=', start), ('attendance_date', '<', end), ('attendance_date', '<=', today)])
        recent = self.sudo().search([('employee_id', 'in', employees.ids), ('attendance_date', 'in', [today, yesterday])])
        requests = self.env['hdc.employee.request'].sudo().search([
            ('employee_id', 'in', employees.ids), ('state', '=', 'approved'),
            ('date_from', '<', datetime.combine(end, datetime.min.time()) - timedelta(hours=8)),
            ('date_to', '>', datetime.combine(start, datetime.min.time()) - timedelta(hours=8)),
        ])
        rows = defaultdict(lambda: {'worked': 0, 'late': 0, 'early': 0, 'overtime': 0, 'planned': 0})
        # Provisional weekday baseline, matching the existing 480-minute rule.
        # Excludes future dates; holidays and individual calendars are not yet applied.
        days = sum((start + timedelta(days=i)).weekday() < 5
                   for i in range(max(0, (min(end, today + timedelta(days=1)) - start).days)))
        for employee in employees:
            rows[employee.department_id.name or 'Нэгжгүй']['planned'] += days * 8
        for r in daily:
            row = rows[r.department_id.name or 'Нэгжгүй']
            for key, field in [('worked','worked_minutes'), ('late','late_minutes'), ('early','early_leave_minutes'), ('overtime','overtime_minutes')]:
                row[key] += getattr(r, field) / 60
        return {'month': start.strftime('%Y-%m'), 'cards': [
            ['Идэвхтэй ажилтан', len(employees)],
            ['Ээлжийн амралттай /сонгосон сар/', len(requests.filtered(lambda r: r.request_type == 'annual_leave').mapped('employee_id'))],
            ['Өвчтэй /сонгосон сар/', len(requests.filtered(lambda r: r.request_type == 'sick').mapped('employee_id'))],
            ['Төхөөрөмжийн кодгүй ажилтан', len(employees.filtered(lambda e: not e.attendance_device_user_id))],
            ['Ирсэн цаг бүртгэгдээгүй /өнөөдөр/', len(employees - recent.filtered(lambda r: r.attendance_date == today and r.actual_check_in).mapped('employee_id'))],
            ['Орсон, гарсан цаг дутуу /өчигдөр/', len(recent.filtered(lambda r: r.attendance_date == yesterday and r.status == 'incomplete'))],
            ['Хоцролттой /өчигдөр/', len(recent.filtered(lambda r: r.attendance_date == yesterday and r.late_minutes > 0))],
            ['60 минутаас дээш нийт хоцролт /сар/', len([v for v in self._management_late_totals(daily).values() if v > 60])],
        ], 'rows': [{'name': k, **{f: round(v, 2) for f,v in row.items()}} for k,row in sorted(rows.items())]}

    def _management_late_totals(self, records):
        totals = defaultdict(int)
        for r in records:
            totals[r.employee_id.id] += r.late_minutes
        return totals
