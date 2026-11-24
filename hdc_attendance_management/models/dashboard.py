from datetime import datetime, timedelta, timezone
from collections import defaultdict
from odoo import api, models
from dateutil.relativedelta import relativedelta
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
        rows = defaultdict(lambda: {'worked': 0, 'late': 0, 'early': 0, 'overtime': 0, 'planned': 0, 'outside': 0, 'sick': 0, 'leave': 0, 'annual': 0, 'absent': 0})
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
        # Split approved requests by local working day, excluding lunch and
        # weekends. Merge overlapping intervals of the same type.
        kinds = {'outside_work': 'outside', 'sick': 'sick',
                 'leave': 'leave', 'annual_leave': 'annual'}
        intervals = defaultdict(list)
        offset = timedelta(hours=8)
        for req in requests:
            kind = kinds.get(req.request_type)
            if not kind:
                continue
            a, b = req.date_from + offset, req.date_to + offset
            day = max(start, a.date())
            last = min(end - timedelta(days=1), today, b.date())
            while day <= last:
                if day.weekday() < 5:
                    midnight = datetime.combine(day, datetime.min.time())
                    for lo, hi in [(8, 12), (13, 17)]:
                        left = max(a, midnight + timedelta(hours=lo))
                        right = min(b, midnight + timedelta(hours=hi))
                        if right > left:
                            intervals[(req.employee_id.id, day, kind)].append((left, right))
                day += timedelta(days=1)

        def hours(spans):
            merged = []
            for a, b in sorted(spans):
                if merged and a <= merged[-1][1]:
                    merged[-1][1] = max(b, merged[-1][1])
                else:
                    merged.append([a, b])
            return sum((b-a).total_seconds()/3600 for a,b in merged)

        by_employee = {e.id: e for e in employees}
        daily_by_key = {(r.employee_id.id, r.attendance_date): r for r in daily}
        excused = defaultdict(list)
        for (eid, day, kind), spans in intervals.items():
            record = daily_by_key.get((eid, day))
            department = record.department_id if record else by_employee[eid].department_id
            rows[department.name or 'Нэгжгүй'][kind] += hours(spans)
            excused[(eid, day)].extend(spans)
        # Only explicit processed absent records are counted, not missing
        # device data. Do not count today's unfinished attendance as absence.
        for r in daily:
            if r.status == 'absent' and r.attendance_date < today and r.attendance_date.weekday() < 5:
                rows[r.department_id.name or 'Нэгжгүй']['absent'] += max(0, 8-hours(excused[(r.employee_id.id, r.attendance_date)]))
        return {'month': start.strftime('%Y-%m'), 'cards': [
            ['Шинэ ажилтан сүүлийн 1 сараар', len(employees.filtered(lambda e: e.create_date and today - relativedelta(months=1) <= (e.create_date + timedelta(hours=8)).date() <= today))],
            ['Энэ сард ээлжийн амралттай байгаа ажилтан', len(requests.filtered(lambda r: r.request_type == 'annual_leave').mapped('employee_id'))],
            ['Энэ сард ХАЧ болон Ж/Амралттай ажилтан', len(requests.filtered(lambda r: r.request_type == 'sick').mapped('employee_id'))],
            ['Цагаа бүртгүүлдэггүй ажилтнууд', len(employees.filtered(lambda e: not e.attendance_device_user_id))],
            ['Цагаа бүртгүүлээгүй ажилтан /өнөөдрөөр/', len(employees - recent.filtered(lambda r: r.attendance_date == today and r.actual_check_in).mapped('employee_id'))],
            ['Орсон, гарсан цаг дутуу ажилтан /өчигдрөөр/', len(recent.filtered(lambda r: r.attendance_date == yesterday and r.status == 'incomplete'))],
            ['Хоцролттой ажилтан /өчигдрөөр/', len(recent.filtered(lambda r: r.attendance_date == yesterday and r.late_minutes > 0))],
            ['60 минутаас дээш хоцролттой байгаа ажилтан /сараар/', len([v for v in self._management_late_totals(daily).values() if v > 60])],
        ], 'rows': [{'name': k, **{f: round(v, 2) for f,v in row.items()}} for k,row in sorted(rows.items())]}

    def _management_late_totals(self, records):
        totals = defaultdict(int)
        for r in records:
            totals[r.employee_id.id] += r.late_minutes
        return totals
