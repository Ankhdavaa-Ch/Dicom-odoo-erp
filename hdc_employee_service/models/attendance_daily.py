from datetime import date, datetime, time, timedelta

from odoo import api, models
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

# These approved request types are treated as authorized working-time absence.
# Overtime is intentionally excluded because it must not reduce late/early time.
EXCUSED_REQUEST_TYPES = {
    'outside_work',
    'leave',
    'attendance_correction',
    'annual_leave',
    'sick',
    'training_leave',
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

        def merge_intervals(intervals):
            if not intervals:
                return []
            intervals = sorted(intervals, key=lambda item: item[0])
            merged = [list(intervals[0])]
            for interval_start, interval_end in intervals[1:]:
                if interval_start <= merged[-1][1]:
                    merged[-1][1] = max(merged[-1][1], interval_end)
                else:
                    merged.append([interval_start, interval_end])
            return [(item[0], item[1]) for item in merged]

        def overlap_minutes(intervals, range_start, range_end):
            if not range_start or not range_end or range_end <= range_start:
                return 0
            total = 0
            for interval_start, interval_end in merge_intervals(intervals):
                overlap_start = max(interval_start, range_start)
                overlap_end = min(interval_end, range_end)
                if overlap_end > overlap_start:
                    total += int((overlap_end - overlap_start).total_seconds() / 60)
            return total

        requests_by_date = {}
        excused_intervals_by_date = {}
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
                    if request.request_type in EXCUSED_REQUEST_TYPES:
                        excused_intervals_by_date.setdefault(current_day, []).append((overlap_start, overlap_end))
                current_day += timedelta(days=1)

        days = []
        totals = {
            'planned_minutes': 0,
            'worked_minutes': 0,
            'late_minutes': 0,
            'early_leave_minutes': 0,
            'overtime_minutes': 0,
            'excused_minutes': 0,
        }
        by_date = {record.attendance_date: record for record in records}
        cursor = start
        while cursor <= end:
            record = by_date.get(cursor)
            weekday = cursor.weekday()
            planned = 480 if weekday < 5 else 0
            totals['planned_minutes'] += planned
            day_requests = requests_by_date.get(cursor, [])
            excused_intervals = excused_intervals_by_date.get(cursor, [])

            adjusted_late = record.late_minutes if record else 0
            adjusted_early = record.early_leave_minutes if record else 0
            excused_late = 0
            excused_early = 0

            if record:
                actual_in_local = local_dt(record.actual_check_in)
                actual_out_local = local_dt(record.actual_check_out)
                planned_in_local = local_dt(record.planned_check_in)
                planned_out_local = local_dt(record.planned_check_out)

                # Late minutes are excused only when an approved request overlaps
                # the actual late interval before check-in.
                if record.late_minutes and planned_in_local and actual_in_local:
                    late_start = planned_in_local
                    late_end = actual_in_local
                    excused_late = min(record.late_minutes, overlap_minutes(excused_intervals, late_start, late_end))
                    adjusted_late = max(record.late_minutes - excused_late, 0)

                # Early-leave minutes are excused only when an approved request
                # overlaps the missing working interval after the employee leaves.
                if record.early_leave_minutes and actual_out_local and planned_out_local:
                    early_start = actual_out_local
                    early_end = planned_out_local
                    excused_early = min(record.early_leave_minutes, overlap_minutes(excused_intervals, early_start, early_end))
                    adjusted_early = max(record.early_leave_minutes - excused_early, 0)

                totals['worked_minutes'] += record.worked_minutes
                totals['late_minutes'] += adjusted_late
                totals['early_leave_minutes'] += adjusted_early
                totals['overtime_minutes'] += record.overtime_minutes
                totals['excused_minutes'] += excused_late + excused_early

                if adjusted_late > 0 and adjusted_early > 0:
                    adjusted_status = 'late_early'
                elif adjusted_late > 0:
                    adjusted_status = 'late'
                elif adjusted_early > 0:
                    adjusted_status = 'early_leave'
                elif record.overtime_minutes > 0:
                    adjusted_status = 'overtime'
                elif record.actual_check_in and not record.actual_check_out:
                    adjusted_status = 'incomplete'
                else:
                    adjusted_status = 'present'

                days.append({
                    'date': cursor.isoformat(),
                    'day': cursor.day,
                    'weekday': weekday,
                    'is_weekend': weekday >= 5,
                    'planned': '08:00 - 17:00' if weekday < 5 else '-',
                    'check_in': local_hm(record.actual_check_in),
                    'check_out': local_hm(record.actual_check_out),
                    'worked': hhmm(record.worked_minutes),
                    'late': hhmm(adjusted_late),
                    'early': hhmm(adjusted_early),
                    'raw_late': hhmm(record.late_minutes),
                    'raw_early': hhmm(record.early_leave_minutes),
                    'excused_late': hhmm(excused_late),
                    'excused_early': hhmm(excused_early),
                    'overtime': hhmm(record.overtime_minutes),
                    'status': adjusted_status,
                    'requests': day_requests,
                })
            else:
                # A full/partial approved request is still displayed on a day with
                # no attendance punches. Absence handling can be expanded later.
                days.append({
                    'date': cursor.isoformat(), 'day': cursor.day, 'weekday': weekday,
                    'is_weekend': weekday >= 5, 'planned': '08:00 - 17:00' if weekday < 5 else '-',
                    'check_in': '', 'check_out': '', 'worked': '00:00', 'late': '00:00',
                    'early': '00:00', 'raw_late': '00:00', 'raw_early': '00:00',
                    'excused_late': '00:00', 'excused_early': '00:00', 'overtime': '00:00',
                    'status': 'empty', 'requests': day_requests,
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
                'excused': hhmm(totals['excused_minutes']),
                'outside_work': hhmm(request_totals['outside_work']),
                'leave': hhmm(request_totals['leave']),
                'attendance_correction': hhmm(request_totals['attendance_correction']),
                'annual_leave': hhmm(request_totals['annual_leave']),
                'sick': hhmm(request_totals['sick']),
                'training_leave': hhmm(request_totals['training_leave']),
                'request_overtime': hhmm(request_totals['overtime']),
            },
        }
