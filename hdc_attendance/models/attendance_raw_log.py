import hashlib

from odoo import api, fields, models


class HdcAttendanceRawLog(models.Model):
    _name = 'hdc.attendance.raw.log'
    _description = 'Ирцийн төхөөрөмжийн Raw Log'
    _order = 'received_at desc, id desc'

    # =========================================================
    # DEVICE
    # =========================================================

    device_id = fields.Many2one(
        'hdc.attendance.device',
        string='Төхөөрөмж',
        required=True,
        ondelete='cascade',
        index=True,
    )

    device_serial = fields.Char(
        string='Device Serial',
        index=True,
    )

    # =========================================================
    # EMPLOYEE
    # =========================================================

    device_user_id = fields.Char(
        string='Device User ID',
        index=True,
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Ажилтан',
        ondelete='set null',
        index=True,
    )

    # =========================================================
    # ATTENDANCE
    # =========================================================

    punch_time = fields.Datetime(
        string='Бүртгэсэн цаг',
        index=True,
    )

    punch_state = fields.Char(
        string='Punch State',
    )

    verify_type = fields.Char(
        string='Verify Type',
    )

    # =========================================================
    # ADMS / HTTP
    # =========================================================

    table_name = fields.Char(
        string='ADMS Table',
    )

    source_ip = fields.Char(
        string='Source IP',
    )

    request_method = fields.Char(
        string='HTTP Method',
    )

    request_path = fields.Char(
        string='Request Path',
    )

    query_string = fields.Text(
        string='Query String',
    )

    raw_data = fields.Text(
        string='Raw Data',
    )

    raw_hash = fields.Char(
        string='Raw Hash',
        index=True,
    )

    # =========================================================
    # PROCESSING
    # =========================================================

    received_at = fields.Datetime(
        string='Хүлээн авсан',
        default=fields.Datetime.now,
        required=True,
        index=True,
    )

    processed = fields.Boolean(
        string='Боловсруулсан',
        default=False,
        index=True,
    )

    processing_error = fields.Text(
        string='Боловсруулалтын алдаа',
    )

    # =========================================================
    # NORMALIZE DEVICE USER ID
    # =========================================================

    @api.model
    def _normalize_device_user_id(
        self,
        device_user_id,
    ):
        if device_user_id is None:
            return False

        value = str(device_user_id).strip()

        return value or False

    # =========================================================
    # DUPLICATE HASH
    # =========================================================

    @api.model
    def _make_hash(
        self,
        serial,
        raw_data,
    ):
        source = '%s|%s' % (
            (serial or '').strip(),
            raw_data or '',
        )

        return hashlib.sha256(
            source.encode('utf-8')
        ).hexdigest()

    # =========================================================
    # EMPLOYEE MATCHING
    # =========================================================

    @api.model
    def match_employee(
        self,
        device_user_id,
        device=False,
    ):
        device_user_id = (
            self._normalize_device_user_id(
                device_user_id
            )
        )

        if not device_user_id:
            return False

        Employee = self.env[
            'hr.employee'
        ].sudo()

        # -----------------------------------------------------
        # Device + Device User ID
        # -----------------------------------------------------

        if device:
            employees = Employee.search(
                [
                    (
                        'attendance_device_user_id',
                        '=',
                        device_user_id,
                    ),
                    (
                        'attendance_device_id',
                        '=',
                        device.id,
                    ),
                ],
                limit=2,
            )

            if len(employees) == 1:
                return employees

        # -----------------------------------------------------
        # Fallback: зөвхөн Device User ID
        # -----------------------------------------------------

        employees = Employee.search(
            [
                (
                    'attendance_device_user_id',
                    '=',
                    device_user_id,
                ),
            ],
            limit=2,
        )

        if len(employees) == 1:
            return employees

        return False

    # =========================================================
    # MANUAL EMPLOYEE MATCH
    # =========================================================

    def action_match_employee(self):

        for record in self:

            employee = self.match_employee(
                record.device_user_id,
                record.device_id,
            )

            if not employee:
                continue

            # Ижил Device User ID-тай,
            # employee хоосон бүх log-ийг холбоно
            logs = self.search(
                [
                    (
                        'device_user_id',
                        '=',
                        record.device_user_id,
                    ),
                    (
                        'employee_id',
                        '=',
                        False,
                    ),
                ]
            )

            logs.write({
                'employee_id': employee.id,
                'processed': False,
            })

        return True