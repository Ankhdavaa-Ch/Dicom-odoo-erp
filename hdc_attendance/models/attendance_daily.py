from datetime import datetime, time, timedelta, timezone

from odoo import api, fields, models, _


# =============================================================
# TIMEZONE
# =============================================================

MONGOLIA_TZ = timezone(
    timedelta(hours=8)
)

UTC_TZ = timezone.utc


class HdcAttendanceDaily(models.Model):

    _name = 'hdc.attendance.daily'
    _description = 'Өдрийн ирц'
    _order = 'attendance_date desc, employee_id'

    # =========================================================
    # FLEXIBLE WORK RULE
    # =========================================================

    FLEX_START = time(8, 0)
    FLEX_END = time(9, 30)

    CHECKOUT_START = time(17, 0)
    CHECKOUT_END = time(18, 30)

    BREAK_MINUTES = 60
    REQUIRED_MINUTES = 480

    # =========================================================
    # EMPLOYEE
    # =========================================================

    employee_id = fields.Many2one(
        'hr.employee',
        string='Ажилтан',
        required=True,
        ondelete='cascade',
        index=True,
    )

    attendance_date = fields.Date(
        string='Огноо',
        required=True,
        index=True,
    )

    department_id = fields.Many2one(
        'hr.department',
        string='Газар / хэлтэс',
        readonly=True,
    )

    job_id = fields.Many2one(
        'hr.job',
        string='Албан тушаал',
        readonly=True,
    )

    # =========================================================
    # TIME
    # =========================================================

    planned_check_in = fields.Datetime(
        string='Хоцролтын босго',
        readonly=True,
    )

    planned_check_out = fields.Datetime(
        string='Тарах ёстой цаг',
        readonly=True,
    )

    actual_check_in = fields.Datetime(
        string='Ирсэн цаг',
        readonly=True,
    )

    actual_check_out = fields.Datetime(
        string='Гарсан цаг',
        readonly=True,
    )

    # =========================================================
    # CALCULATED
    # =========================================================

    worked_minutes = fields.Integer(
        string='Ажилласан минут',
        compute='_compute_attendance_values',
        store=True,
    )

    late_minutes = fields.Integer(
        string='Хоцорсон минут',
        compute='_compute_attendance_values',
        store=True,
    )

    early_leave_minutes = fields.Integer(
        string='Дутуу ажилласан минут',
        compute='_compute_attendance_values',
        store=True,
    )

    overtime_minutes = fields.Integer(
        string='Илүү ажилласан минут',
        compute='_compute_attendance_values',
        store=True,
    )

    status = fields.Selection(
        [
            ('present', 'Хэвийн'),
            ('late', 'Хоцорсон'),
            ('early_leave', 'Дутуу ажилласан'),
            (
                'late_early',
                'Хоцорсон / Дутуу'
            ),
            ('overtime', 'Илүү ажилласан'),
            (
                'incomplete',
                'Гаралт бүртгэгдээгүй'
            ),
            ('absent', 'Тасалсан'),
        ],
        string='Төлөв',
        compute='_compute_attendance_values',
        store=True,
    )

    raw_log_ids = fields.Many2many(
        'hdc.attendance.raw.log',
        string='Raw Logs',
        readonly=True,
    )

    # =========================================================
    # UNIQUE
    # =========================================================

    _sql_constraints = [
        (
            'employee_date_unique',
            'unique(employee_id, attendance_date)',
            'Нэг ажилтны нэг өдрийн ирц давхардаж болохгүй.',
        ),
    ]

    # =========================================================
    # MONGOLIA LOCAL DATETIME -> UTC
    # =========================================================

    @api.model
    def _local_datetime_to_utc(
        self,
        date_value,
        time_value,
    ):

        local_dt = datetime.combine(
            date_value,
            time_value,
        )

        local_dt = local_dt.replace(
            tzinfo=MONGOLIA_TZ
        )

        utc_dt = local_dt.astimezone(
            UTC_TZ
        )

        return utc_dt.replace(
            tzinfo=None
        )

    # =========================================================
    # UTC -> MONGOLIA LOCAL DATE
    # =========================================================

    @api.model
    def _utc_to_local_date(
        self,
        utc_datetime,
    ):

        if not utc_datetime:
            return False

        utc_dt = utc_datetime.replace(
            tzinfo=UTC_TZ
        )

        local_dt = utc_dt.astimezone(
            MONGOLIA_TZ
        )

        return local_dt.date()

    # =========================================================
    # CALCULATION
    # =========================================================

    @api.depends(
        'planned_check_in',
        'planned_check_out',
        'actual_check_in',
        'actual_check_out',
    )
    def _compute_attendance_values(self):

        for record in self:

            record.worked_minutes = 0
            record.late_minutes = 0
            record.early_leave_minutes = 0
            record.overtime_minutes = 0
            record.status = 'absent'

            if not record.actual_check_in:
                continue

            # -------------------------------------------------
            # Late
            # -------------------------------------------------

            if (
                record.planned_check_in
                and record.actual_check_in
                > record.planned_check_in
            ):

                record.late_minutes = max(
                    int(
                        (
                            record.actual_check_in
                            - record.planned_check_in
                        ).total_seconds()
                        / 60
                    ),
                    0,
                )

            # -------------------------------------------------
            # No checkout
            # -------------------------------------------------

            if not record.actual_check_out:

                record.status = 'incomplete'

                continue

            # -------------------------------------------------
            # Worked minutes
            # -------------------------------------------------

            total_minutes = int(
                (
                    record.actual_check_out
                    - record.actual_check_in
                ).total_seconds()
                / 60
            )

            record.worked_minutes = max(
                total_minutes
                - self.BREAK_MINUTES,
                0,
            )

            # -------------------------------------------------
            # Under 8 hours
            # -------------------------------------------------

            if (
                record.worked_minutes
                < self.REQUIRED_MINUTES
            ):

                record.early_leave_minutes = (
                    self.REQUIRED_MINUTES
                    - record.worked_minutes
                )

            # -------------------------------------------------
            # Over 8 hours
            # -------------------------------------------------

            elif (
                record.worked_minutes
                > self.REQUIRED_MINUTES
            ):

                record.overtime_minutes = (
                    record.worked_minutes
                    - self.REQUIRED_MINUTES
                )

            # -------------------------------------------------
            # Status
            # -------------------------------------------------

            if (
                record.late_minutes > 0
                and record.early_leave_minutes > 0
            ):

                record.status = 'late_early'

            elif record.late_minutes > 0:

                record.status = 'late'

            elif record.early_leave_minutes > 0:

                record.status = 'early_leave'

            elif record.overtime_minutes > 0:

                record.status = 'overtime'

            else:

                record.status = 'present'

    # =========================================================
    # FLEXIBLE SCHEDULE
    # =========================================================

    @api.model
    def _get_flexible_schedule(
        self,
        attendance_date,
        actual_check_in,
    ):

        date_value = fields.Date.to_date(
            attendance_date
        )

        # 08:00 UTC equivalent
        flex_start = (
            self._local_datetime_to_utc(
                date_value,
                self.FLEX_START,
            )
        )

        # 09:30 UTC equivalent
        flex_end = (
            self._local_datetime_to_utc(
                date_value,
                self.FLEX_END,
            )
        )

        # 17:00
        checkout_start = (
            self._local_datetime_to_utc(
                date_value,
                self.CHECKOUT_START,
            )
        )

        # 18:30
        checkout_end = (
            self._local_datetime_to_utc(
                date_value,
                self.CHECKOUT_END,
            )
        )

        # -----------------------------------------------------
        # 08:00-аас өмнө
        # -----------------------------------------------------

        if actual_check_in < flex_start:

            expected_check_out = (
                checkout_start
            )

        # -----------------------------------------------------
        # 08:00 - 09:30
        # -----------------------------------------------------

        elif actual_check_in <= flex_end:

            expected_check_out = (
                actual_check_in
                + timedelta(
                    minutes=(
                        self.REQUIRED_MINUTES
                        + self.BREAK_MINUTES
                    )
                )
            )

        # -----------------------------------------------------
        # 09:30-с хойш
        # -----------------------------------------------------

        else:

            expected_check_out = (
                checkout_end
            )

        if (
            expected_check_out
            < checkout_start
        ):
            expected_check_out = (
                checkout_start
            )

        if (
            expected_check_out
            > checkout_end
        ):
            expected_check_out = (
                checkout_end
            )

        # planned_check_in гэдэг нь
        # хоцролтын босго = 09:30
        return (
            flex_end,
            expected_check_out,
        )

    # =========================================================
    # BUTTON
    # =========================================================

    def action_process_raw_logs(self):

        self.process_raw_logs()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Амжилттай'),
                'message': _(
                    'Ирц амжилттай боловсруулагдлаа.'
                ),
                'type': 'success',
                'sticky': False,
            },
        }

    # =========================================================
    # RAW LOG -> DAILY
    # =========================================================

    @api.model
    def process_raw_logs(self):

        RawLog = self.env[
            'hdc.attendance.raw.log'
        ].sudo()

        logs = RawLog.search(
            [
                (
                    'employee_id',
                    '!=',
                    False,
                ),
                (
                    'punch_time',
                    '!=',
                    False,
                ),
                (
                    'processed',
                    '=',
                    False,
                ),
            ],
            order='employee_id, punch_time',
        )

        if not logs:
            return True

        grouped = {}

        # -----------------------------------------------------
        # Employee + Mongolia local date
        # -----------------------------------------------------

        for log in logs:

            local_date = (
                self._utc_to_local_date(
                    log.punch_time
                )
            )

            key = (
                log.employee_id.id,
                local_date,
            )

            if key not in grouped:

                grouped[key] = self.env[
                    'hdc.attendance.raw.log'
                ]

            grouped[key] |= log

        # -----------------------------------------------------
        # Process
        # -----------------------------------------------------

        for (
            employee_id,
            attendance_date,
        ), new_logs in grouped.items():

            employee = self.env[
                'hr.employee'
            ].browse(
                employee_id
            )

            daily = self.search(
                [
                    (
                        'employee_id',
                        '=',
                        employee.id,
                    ),
                    (
                        'attendance_date',
                        '=',
                        attendance_date,
                    ),
                ],
                limit=1,
            )

            all_logs = new_logs

            if daily:

                all_logs |= (
                    daily.raw_log_ids
                )

            all_logs = all_logs.filtered(
                lambda log:
                    log.punch_time
                    and log.employee_id.id
                    == employee.id
            )

            sorted_logs = all_logs.sorted(
                key=lambda log:
                    log.punch_time
            )

            if not sorted_logs:
                continue

            first_log = sorted_logs[0]

            last_log = sorted_logs[-1]

            actual_check_in = (
                first_log.punch_time
            )

            actual_check_out = (
                last_log.punch_time
                if len(sorted_logs) > 1
                else False
            )

            (
                planned_check_in,
                planned_check_out,
            ) = self._get_flexible_schedule(
                attendance_date,
                actual_check_in,
            )

            values = {

                'employee_id':
                    employee.id,

                'attendance_date':
                    attendance_date,

                'department_id': (
                    employee.department_id.id
                    if employee.department_id
                    else False
                ),

                'job_id': (
                    employee.job_id.id
                    if employee.job_id
                    else False
                ),

                'planned_check_in':
                    planned_check_in,

                'planned_check_out':
                    planned_check_out,

                'actual_check_in':
                    actual_check_in,

                'actual_check_out':
                    actual_check_out,

                'raw_log_ids': [
                    (
                        6,
                        0,
                        sorted_logs.ids,
                    )
                ],
            }

            if daily:

                daily.write(
                    values
                )

            else:

                self.create(
                    values
                )

            new_logs.write({
                'processed': True,
            })

        return True