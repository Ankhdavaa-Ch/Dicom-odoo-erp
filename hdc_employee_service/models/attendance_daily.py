from datetime import date, datetime, time, timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


REQUEST_LABELS = {
    'outside_work': 'Гадуур ажиллах',
    'leave': 'Чөлөө',
    'attendance_correction': 'Ирц нөхөн бүртгүүлэх',
    'annual_leave': 'Ээлжийн амралт',
    'overtime': 'Илүү цаг',
    'sick': 'Өвчтэй',
    'training_leave': 'Сургалтын чөлөө',
}


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

        # Odoo stores Datetime values in UTC. Search a slightly wider UTC range so
        # requests near the Mongolia day boundary are included, then split them by
        # local calendar day below.
        utc_from = datetime.combine(start, time.min) - timedelta(hours=8)
        utc_to = datetime.combine(end + timedelta(days=1), time.min) - timedelta(hours=8)
        requests = self.env['hdc.employee.request'].sudo().search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'approved'),
            ('date_from', '<', utc_to),
            ('date_to', '>', utc_from),
        ], order='date_from')

        def hhmm(minutes):
            minutes = max(int(minutes or 0), 0)
            return f'{minutes // 60:02d}:{minutes % 60:02d}'

        def local_dt(value):
            return value + timedelta(hours=8) if value else False

        def local_hm(value):
            value = local_dt(value)
            return value.strftime('%H:%M') if value else ''

        requests_by_date = {}
        request_totals = {key: 0 for key in REQUEST_LABELS}
        for request in requests:
            local_from = local_dt(request.date_from)
            local_to = local_dt(request.date_to)
            current_day = max(local_from.date(), start)
            last_day = min(local_to.date(), end)
            while current_day <= last_day:
                day_start = datetime.combine(current_day, time.min)
                day_end = day_start + timedelta(days=1)
                overlap_start = max(local_from, day_start)
                overlap_end = min(local_to, day_end)
                minutes = max(int((overlap_end - overlap_start).total_seconds() / 60), 0)
                if minutes:
                    item = {
                        'id': request.id,
                        'type': request.request_type,
                        'label': REQUEST_LABELS.get(request.request_type, request.request_type),
                        'time': f'{overlap_start.strftime("%H:%M")} - {overlap_end.strftime("%H:%M")}',
                        'minutes': minutes,
                        'duration': hhmm(minutes),
                    }
                    requests_by_date.setdefault(current_day, []).append(item)
                    request_totals[request.request_type] = request_totals.get(request.request_type, 0) + minutes
                current_day += timedelta(days=1)

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
            day_requests = requests_by_date.get(cursor, [])
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
                    'requests': day_requests,
                })
            else:
                days.append({
                    'date': cursor.isoformat(), 'day': cursor.day, 'weekday': weekday,
                    'is_weekend': weekday >= 5, 'planned': '08:00 - 17:00' if weekday < 5 else '-',
                    'check_in': '', 'check_out': '', 'worked': '00:00', 'late': '00:00',
                    'early': '00:00', 'overtime': '00:00', 'status': 'empty',
                    'requests': day_requests,
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
                'outside_work': hhmm(request_totals['outside_work']),
                'leave': hhmm(request_totals['leave']),
                'attendance_correction': hhmm(request_totals['attendance_correction']),
                'annual_leave': hhmm(request_totals['annual_leave']),
                'sick': hhmm(request_totals['sick']),
                'training_leave': hhmm(request_totals['training_leave']),
                'request_overtime': hhmm(request_totals['overtime']),
            },
        }
