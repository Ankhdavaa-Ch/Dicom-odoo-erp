from datetime import timedelta, timezone

from odoo import fields, models
from odoo.exceptions import UserError

try:
    from zk import ZK
except ImportError:
    ZK = None


# =============================================================
# TIMEZONE
# =============================================================

MONGOLIA_TZ = timezone(
    timedelta(hours=8)
)

UTC_TZ = timezone.utc


# =============================================================
# PYZK SAFE TIMESTAMP PATCH
# =============================================================

def patch_pyzk_safe_decode():
    """
    Horus төхөөрөмж дээр зарим attendance record-ийн timestamp
    эвдэрсэн байвал pyzk-ийн get_attendance() бүхэлдээ тасардаг.

    Энэ patch нь:
        ValueError
        OverflowError

    гарсан timestamp-ийг None болгож алгасах боломж олгоно.
    """

    if ZK is None:
        return

    original_decode = ZK._ZK__decode_time

    # Давхар patch хийхээс хамгаална
    if getattr(
        original_decode,
        '_hdc_safe_decode',
        False
    ):
        return

    def safe_decode(self, value):

        try:
            return original_decode(
                self,
                value
            )

        except (
            ValueError,
            OverflowError,
        ):
            return None

    safe_decode._hdc_safe_decode = True

    ZK._ZK__decode_time = safe_decode


# =============================================================
# WIZARD
# =============================================================

class HdcAttendancePullWizard(
    models.TransientModel
):

    _name = 'hdc.attendance.pull.wizard'
    _description = 'Ирц төхөөрөмжөөс татах'

    # =========================================================
    # FIELDS
    # =========================================================

    device_id = fields.Many2one(
        'hdc.attendance.device',
        string='Төхөөрөмж',
        required=True,
    )

    date_from = fields.Date(
        string='Эхлэх огноо',
        required=True,
        default=fields.Date.context_today,
    )

    date_to = fields.Date(
        string='Дуусах огноо',
        required=True,
        default=fields.Date.context_today,
    )

    # =========================================================
    # DEVICE LOCAL TIME -> UTC
    # =========================================================

    def _device_local_to_utc(
        self,
        local_datetime,
    ):
        """
        Horus дээрх цаг:
            2026-09-09 08:30:00

        Монголын UTC+8 local time гэж үзнэ.

        PostgreSQL / Odoo-д:
            UTC naive datetime

        хадгална.
        """

        if not local_datetime:
            return False

        # Хэрэв ямар нэг timezone аль хэдийн байвал
        if local_datetime.tzinfo:

            local_datetime = (
                local_datetime.astimezone(
                    MONGOLIA_TZ
                )
            )

        else:

            local_datetime = (
                local_datetime.replace(
                    tzinfo=MONGOLIA_TZ
                )
            )

        utc_datetime = (
            local_datetime.astimezone(
                UTC_TZ
            )
        )

        return utc_datetime.replace(
            tzinfo=None
        )

    # =========================================================
    # PULL ATTENDANCE
    # =========================================================

    def action_pull_logs(self):

        self.ensure_one()

        # -----------------------------------------------------
        # pyzk installed?
        # -----------------------------------------------------

        if ZK is None:

            raise UserError(
                'pyzk package суулгагдаагүй байна.\n\n'
                'PowerShell дээр:\n'
                'pip install pyzk'
            )

        # -----------------------------------------------------
        # Date validation
        # -----------------------------------------------------

        if (
            not self.date_from
            or not self.date_to
        ):

            raise UserError(
                'Эхлэх болон дуусах '
                'огноог сонгоно уу.'
            )

        if self.date_from > self.date_to:

            raise UserError(
                'Эхлэх огноо дуусах '
                'огнооноос хойш байж болохгүй.'
            )

        # -----------------------------------------------------
        # Device validation
        # -----------------------------------------------------

        device = self.device_id

        if not device:

            raise UserError(
                'Төхөөрөмж сонгоно уу.'
            )

        if not device.ip_address:

            raise UserError(
                'Төхөөрөмжийн IP Address '
                'тохируулаагүй байна.'
            )

        # -----------------------------------------------------
        # Raw Log model
        # -----------------------------------------------------

        RawLog = self.env[
            'hdc.attendance.raw.log'
        ].sudo()

        conn = None

        try:

            # =================================================
            # PATCH PYZK
            # =================================================

            patch_pyzk_safe_decode()

            # =================================================
            # CONNECT HORUS
            # =================================================

            zk = ZK(
                device.ip_address,
                port=device.port or 4370,
                timeout=20,
                password=device.comm_key or 0,
                force_udp=False,
                ommit_ping=False,
            )

            conn = zk.connect()

            # =================================================
            # READ DEVICE ATTENDANCE
            # =================================================

            attendance_logs = (
                conn.get_attendance()
                or []
            )

            # =================================================
            # COUNTERS
            # =================================================

            total_device_count = len(
                attendance_logs
            )

            selected_count = 0

            created_count = 0

            skipped_count = 0

            unmatched_count = 0

            invalid_time_count = 0

            # =================================================
            # PROCESS LOGS
            # =================================================

            for attendance in attendance_logs:

                # ---------------------------------------------
                # Timestamp
                # ---------------------------------------------

                punch_datetime = getattr(
                    attendance,
                    'timestamp',
                    False,
                )

                # Safe decode дээр None болсон record
                if not punch_datetime:

                    invalid_time_count += 1

                    continue

                # ---------------------------------------------
                # Date filtering
                # ---------------------------------------------

                punch_date = (
                    punch_datetime.date()
                )

                if (
                    punch_date
                    < self.date_from
                ):
                    continue

                if (
                    punch_date
                    > self.date_to
                ):
                    continue

                selected_count += 1

                # ---------------------------------------------
                # Device User ID
                # ---------------------------------------------

                device_user_id = str(
                    getattr(
                        attendance,
                        'user_id',
                        '',
                    )
                ).strip()

                if not device_user_id:

                    continue

                # ---------------------------------------------
                # Mongolia Local -> UTC
                # ---------------------------------------------

                utc_datetime = (
                    self._device_local_to_utc(
                        punch_datetime
                    )
                )

                if not utc_datetime:

                    invalid_time_count += 1

                    continue

                # ---------------------------------------------
                # Duplicate check
                # ---------------------------------------------

                existing = RawLog.search(
                    [
                        (
                            'device_id',
                            '=',
                            device.id,
                        ),
                        (
                            'device_user_id',
                            '=',
                            device_user_id,
                        ),
                        (
                            'punch_time',
                            '=',
                            utc_datetime,
                        ),
                    ],
                    limit=1,
                )

                if existing:

                    skipped_count += 1

                    # Employee mapping нь өмнө нь хоосон
                    # байсан бол дахин match хийж болно
                    if not existing.employee_id:

                        employee = (
                            RawLog.match_employee(
                                device_user_id,
                                device=device,
                            )
                        )

                        if employee:

                            existing.write({
                                'employee_id':
                                    employee.id,
                            })

                    continue

                # ---------------------------------------------
                # Employee mapping
                # ---------------------------------------------

                employee = (
                    RawLog.match_employee(
                        device_user_id,
                        device=device,
                    )
                )

                if not employee:

                    unmatched_count += 1

                # ---------------------------------------------
                # Raw values
                # ---------------------------------------------

                punch_state = str(
                    getattr(
                        attendance,
                        'status',
                        '',
                    )
                )

                verify_type = str(
                    getattr(
                        attendance,
                        'punch',
                        '',
                    )
                )

                raw_text = str(
                    attendance
                )

                # ---------------------------------------------
                # Unique hash
                # ---------------------------------------------

                hash_source = (
                    '%s|%s|%s|%s'
                    % (
                        device_user_id,
                        punch_datetime,
                        punch_state,
                        verify_type,
                    )
                )

                raw_hash = (
                    RawLog._make_hash(
                        device.serial_number,
                        hash_source,
                    )
                )

                # ---------------------------------------------
                # Extra duplicate hash protection
                # ---------------------------------------------

                existing_hash = RawLog.search(
                    [
                        (
                            'device_id',
                            '=',
                            device.id,
                        ),
                        (
                            'raw_hash',
                            '=',
                            raw_hash,
                        ),
                    ],
                    limit=1,
                )

                if existing_hash:

                    skipped_count += 1

                    continue

                # ---------------------------------------------
                # Create Raw Log
                # ---------------------------------------------

                RawLog.create({

                    'device_id':
                        device.id,

                    'device_serial':
                        device.serial_number
                        or '',

                    'device_user_id':
                        device_user_id,

                    'employee_id': (
                        employee.id
                        if employee
                        else False
                    ),

                    'punch_time':
                        utc_datetime,

                    'punch_state':
                        punch_state,

                    'verify_type':
                        verify_type,

                    'table_name':
                        'ATTLOG',

                    'source_ip':
                        device.ip_address,

                    'request_method':
                        'PULL',

                    'request_path':
                        'ZKTeco TCP/4370',

                    'query_string': (
                        'date_from=%s&date_to=%s'
                        % (
                            self.date_from,
                            self.date_to,
                        )
                    ),

                    'raw_data':
                        raw_text,

                    'raw_hash':
                        raw_hash,

                    'received_at':
                        fields.Datetime.now(),

                    'processed':
                        False,
                })

                created_count += 1

            # =================================================
            # DAILY ATTENDANCE PROCESS
            # =================================================

            if created_count:

                self.env[
                    'hdc.attendance.daily'
                ].sudo().process_raw_logs()

            # =================================================
            # RESULT MESSAGE
            # =================================================

            message = (
                'Ирц татаж дууслаа.\n\n'
                f'Төхөөрөмж дээрх нийт log: '
                f'{total_device_count}\n'
                f'Сонгосон хугацаанд: '
                f'{selected_count}\n'
                f'Шинээр татсан: '
                f'{created_count}\n'
                f'Өмнө байсан: '
                f'{skipped_count}\n'
                f'Ажилтантай холбогдоогүй: '
                f'{unmatched_count}\n'
                f'Алдаатай timestamp: '
                f'{invalid_time_count}'
            )

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title':
                        'Ирц таталт амжилттай',

                    'message':
                        message,

                    'type':
                        'success',

                    'sticky':
                        True,

                    'next': {
                        'type':
                            'ir.actions.act_window_close',
                    },
                },
            }

        # =====================================================
        # ERROR
        # =====================================================

        except Exception as error:

            raise UserError(
                'Төхөөрөмжөөс ирц татах үед '
                'алдаа гарлаа:\n\n%s'
                % str(error)
            )

        # =====================================================
        # DISCONNECT
        # =====================================================

        finally:

            if conn:

                try:

                    conn.disconnect()

                except Exception:

                    pass