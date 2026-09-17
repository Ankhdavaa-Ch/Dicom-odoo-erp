from datetime import date, datetime, timedelta

from odoo import api, models
from odoo.exceptions import UserError


class HdcAttendanceDaily(models.Model):
    _inherit = 'hdc.attendance.daily'

    @api.model
    def get_my_attendance_dashboard(self, date_from, date_to):
        employee = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.uid)], limit=1)
        if not employee:
            raise UserError('Таны системийн хэрэглэгч ажилтны бүртгэлтэй холбогдоогүй байна.')

        start = date.fromisoformat(date_from)
        end = date.fromisoformat(date_to)
        records = self.sudo().search([
            ('employee_id', '=', employee.id),
            ('attendance_date', '>=', start),
            ('attendance_date', '<=', end),
        ], order='attendance_date')

        def hhmm(minutes):
            minutes = max(int(minutes or 0), 0)
            return f'{minutes // 60:02d}:{minutes % 60:02d}'

        def local_hm(value):
            if not value:
                return ''
            local_value = value + timedelta(hours=8)
            return local_value.strftime('%H:%M')

        days = []
        totals = {
            'planned_minutes': 0,
            'worked_minutes': 0,
            'late_minutes': 0,
            'early_leave_minutes': 0,
            'overtime_minutes': 0,
        }
        by_date = {record.attendance_date: record for record in records}
        cursor = start
        while cursor <= end:
            record = by_date.get(cursor)
            weekday = cursor.weekday()
            planned = 480 if weekday < 5 else 0
            totals['planned_minutes'] += planned
            if record:
                totals['worked_minutes'] += record.worked_minutes
                totals['late_minutes'] += record.late_minutes
                totals['early_leave_minutes'] += record.early_leave_minutes
                totals['overtime_minutes'] += record.overtime_minutes
                days.append({
                    'date': cursor.isoformat(),
                    'day': cursor.day,
                    'weekday': weekday,
                    'is_weekend': weekday >= 5,
                    'planned': '08:00 - 17:00' if weekday < 5 else '-',
                    'check_in': local_hm(record.actual_check_in),
                    'check_out': local_hm(record.actual_check_out),
                    'worked': hhmm(record.worked_minutes),
                    'late': hhmm(record.late_minutes),
                    'early': hhmm(record.early_leave_minutes),
                    'overtime': hhmm(record.overtime_minutes),
                    'status': record.status,
                })
            else:
                days.append({
                    'date': cursor.isoformat(), 'day': cursor.day, 'weekday': weekday,
                    'is_weekend': weekday >= 5, 'planned': '08:00 - 17:00' if weekday < 5 else '-',
                    'check_in': '', 'check_out': '', 'worked': '00:00', 'late': '00:00',
                    'early': '00:00', 'overtime': '00:00', 'status': 'empty',
                })
            cursor += timedelta(days=1)

        return {
            'employee': {
                'id': employee.id,
                'name': employee.name,
                'department': employee.department_id.name or '',
                'job': employee.job_id.name or '',
            },
            'days': days,
            'totals': {
                'planned': hhmm(totals['planned_minutes']),
                'worked': hhmm(totals['worked_minutes']),
                'late': hhmm(totals['late_minutes']),
                'early': hhmm(totals['early_leave_minutes']),
                'overtime': hhmm(totals['overtime_minutes']),
            },
        }
