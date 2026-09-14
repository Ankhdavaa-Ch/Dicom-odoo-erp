import logging
from datetime import datetime, timezone, timedelta

from odoo import fields, http
from odoo.http import request


_logger = logging.getLogger(__name__)


# =============================================================
# TIMEZONE
# Mongolia = UTC+8
# =============================================================

MONGOLIA_TZ = timezone(
    timedelta(hours=8)
)

UTC_TZ = timezone.utc


class HdcZkAdmsController(http.Controller):

    # =========================================================
    # HELPERS
    # =========================================================

    def _get_serial(self):
        return (
            request.httprequest.args.get('SN')
            or request.httprequest.args.get('sn')
            or ''
        ).strip()

    def _get_source_ip(self):
        forwarded = request.httprequest.headers.get(
            'X-Forwarded-For'
        )

        if forwarded:
            return forwarded.split(',')[0].strip()

        return request.httprequest.remote_addr

    def _get_query_string(self):
        query = request.httprequest.query_string

        if isinstance(query, bytes):
            return query.decode(
                'utf-8',
                errors='ignore',
            )

        return str(query or '')

    # =========================================================
    # HORUS LOCAL TIME -> UTC
    # =========================================================

    def _device_local_to_utc(self, value):
        """
        Horus TL1:
            2026-09-08 08:30:00

        Энэ нь Монголын local time.

        PostgreSQL/Odoo-д:
            2026-09-08 00:30:00

        гэж UTC хадгална.
        """

        if not value:
            return False

        try:
            local_dt = datetime.strptime(
                value.strip(),
                '%Y-%m-%d %H:%M:%S',
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

        except (ValueError, TypeError):

            _logger.warning(
                'Invalid ZKTeco punch time: %s',
                value,
            )

            return False

    # =========================================================
    # DEVICE
    # =========================================================

    def _get_or_create_device(
        self,
        serial_number,
    ):

        Device = request.env[
            'hdc.attendance.device'
        ].sudo()

        if not serial_number:
            return False

        device = Device.search(
            [
                (
                    'serial_number',
                    '=',
                    serial_number,
                )
            ],
            limit=1,
        )

        values = {
            'last_ip': self._get_source_ip(),
            'last_seen': fields.Datetime.now(),
        }

        if not device:

            values.update({
                'name': 'ZKTeco %s' % serial_number,
                'serial_number': serial_number,
                'device_model': 'ZKTeco Horus TL1',
                'protocol': 'adms',
            })

            device = Device.create(
                values
            )

            _logger.info(
                'New ZKTeco device created '
                'SN=%s IP=%s',
                serial_number,
                self._get_source_ip(),
            )

        else:

            device.write(
                values
            )

        return device

    # =========================================================
    # RAW REQUEST
    # =========================================================

    def _save_raw_request(
        self,
        device,
        serial_number,
        raw_data,
        table_name=None,
    ):

        if not device:
            return False

        RawLog = request.env[
            'hdc.attendance.raw.log'
        ].sudo()

        raw_hash = RawLog._make_hash(
            serial_number,
            raw_data,
        )

        existing = RawLog.search(
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

        if existing:
            return existing

        return RawLog.create({

            'device_id':
                device.id,

            'device_serial':
                serial_number,

            'table_name':
                table_name,

            'source_ip':
                self._get_source_ip(),

            'request_method':
                request.httprequest.method,

            'request_path':
                request.httprequest.path,

            'query_string':
                self._get_query_string(),

            'raw_data':
                raw_data,

            'raw_hash':
                raw_hash,

            'received_at':
                fields.Datetime.now(),

            'processed':
                False,
        })

    # =========================================================
    # ATTLOG
    # =========================================================

    def _parse_attlog_line(
        self,
        device,
        serial_number,
        line,
    ):

        line = (
            line or ''
        ).strip()

        if not line:
            return False

        parts = line.split(
            '\t'
        )

        if len(parts) < 2:

            _logger.warning(
                'Invalid ATTLOG line: %s',
                line,
            )

            return False

        # -----------------------------------------------------
        # Device User ID
        # -----------------------------------------------------

        device_user_id = (
            parts[0].strip()
        )

        # -----------------------------------------------------
        # Punch time
        # -----------------------------------------------------

        punch_time_text = (
            parts[1].strip()
        )

        punch_time = (
            self._device_local_to_utc(
                punch_time_text
            )
        )

        # -----------------------------------------------------
        # Punch State
        # -----------------------------------------------------

        punch_state = (
            parts[2].strip()
            if len(parts) > 2
            else False
        )

        # -----------------------------------------------------
        # Verify Type
        # -----------------------------------------------------

        verify_type = (
            parts[3].strip()
            if len(parts) > 3
            else False
        )

        RawLog = request.env[
            'hdc.attendance.raw.log'
        ].sudo()

        # -----------------------------------------------------
        # Employee match
        # -----------------------------------------------------

        employee = RawLog.match_employee(
            device_user_id,
            device=device,
        )

        # -----------------------------------------------------
        # Duplicate protection
        # -----------------------------------------------------

        raw_hash = RawLog._make_hash(
            serial_number,
            line,
        )

        existing = RawLog.search(
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

        if existing:

            # Өмнө match хийгдээгүй байсан бол
            # дахин employee холбоно.
            if (
                employee
                and not existing.employee_id
            ):

                existing.write({
                    'employee_id':
                        employee.id,
                })

            return existing

        # -----------------------------------------------------
        # Create raw log
        # -----------------------------------------------------

        log = RawLog.create({

            'device_id':
                device.id,

            'device_serial':
                serial_number,

            'device_user_id':
                device_user_id,

            'employee_id': (
                employee.id
                if employee
                else False
            ),

            'punch_time':
                punch_time,

            'punch_state':
                punch_state,

            'verify_type':
                verify_type,

            'table_name':
                'ATTLOG',

            'source_ip':
                self._get_source_ip(),

            'request_method':
                request.httprequest.method,

            'request_path':
                request.httprequest.path,

            'query_string':
                self._get_query_string(),

            'raw_data':
                line,

            'raw_hash':
                raw_hash,

            'received_at':
                fields.Datetime.now(),

            'processed':
                False,
        })

        _logger.info(
            'ATTLOG created '
            'SN=%s USER=%s '
            'DEVICE_TIME=%s '
            'UTC=%s '
            'EMPLOYEE=%s',
            serial_number,
            device_user_id,
            punch_time_text,
            punch_time,
            (
                employee.name
                if employee
                else 'NOT MATCHED'
            ),
        )

        return log

    # =========================================================
    # /iclock/cdata
    # =========================================================

    @http.route(
        '/iclock/cdata',
        type='http',
        auth='public',
        methods=['GET', 'POST'],
        csrf=False,
        save_session=False,
    )
    def iclock_cdata(
        self,
        **kwargs
    ):

        serial_number = (
            self._get_serial()
        )

        device = (
            self._get_or_create_device(
                serial_number
            )
        )

        # =====================================================
        # GET
        # =====================================================

        if (
            request.httprequest.method
            == 'GET'
        ):

            _logger.info(
                'ADMS GET '
                'SN=%s IP=%s',
                serial_number,
                self._get_source_ip(),
            )

            response = (
                'GET OPTION FROM: %s\n'
                'Stamp=9999\n'
                'OpStamp=9999\n'
                'PhotoStamp=9999\n'
                'ErrorDelay=60\n'
                'Delay=10\n'
                'TransTimes=00:00;14:05\n'
                'TransInterval=1\n'
                'TransFlag=1111000000\n'
                'Realtime=1\n'
                'Encrypt=0\n'
            ) % serial_number

            return request.make_response(
                response,
                headers=[
                    (
                        'Content-Type',
                        'text/plain',
                    ),
                ],
            )

        # =====================================================
        # POST
        # =====================================================

        raw_data = (
            request.httprequest
            .get_data()
            .decode(
                'utf-8',
                errors='ignore',
            )
        )

        table_name = (
            request.httprequest.args.get(
                'table'
            )
            or request.httprequest.args.get(
                'Table'
            )
            or ''
        ).upper()

        _logger.info(
            'ADMS POST '
            'SN=%s TABLE=%s '
            'IP=%s BODY=%s',
            serial_number,
            table_name,
            self._get_source_ip(),
            raw_data[:500],
        )

        if not device:

            return request.make_response(
                'OK',
                headers=[
                    (
                        'Content-Type',
                        'text/plain',
                    ),
                ],
            )

        # =====================================================
        # ATTLOG
        # =====================================================

        if table_name == 'ATTLOG':

            for line in (
                raw_data.splitlines()
            ):

                line = (
                    line.strip()
                )

                if not line:
                    continue

                try:

                    self._parse_attlog_line(
                        device,
                        serial_number,
                        line,
                    )

                except Exception:

                    _logger.exception(
                        'ATTLOG parse error: %s',
                        line,
                    )

        # =====================================================
        # OTHER ADMS DATA
        # =====================================================

        else:

            self._save_raw_request(
                device,
                serial_number,
                raw_data,
                table_name=table_name,
            )

        device.sudo().write({

            'last_seen':
                fields.Datetime.now(),

            'last_ip':
                self._get_source_ip(),
        })

        return request.make_response(
            'OK',
            headers=[
                (
                    'Content-Type',
                    'text/plain',
                ),
            ],
        )

    # =========================================================
    # /iclock/getrequest
    # =========================================================

    @http.route(
        '/iclock/getrequest',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False,
        save_session=False,
    )
    def iclock_getrequest(
        self,
        **kwargs
    ):

        serial_number = (
            self._get_serial()
        )

        self._get_or_create_device(
            serial_number
        )

        _logger.info(
            'ADMS GETREQUEST SN=%s',
            serial_number,
        )

        return request.make_response(
            'OK',
            headers=[
                (
                    'Content-Type',
                    'text/plain',
                ),
            ],
        )

    # =========================================================
    # /iclock/devicecmd
    # =========================================================

    @http.route(
        '/iclock/devicecmd',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def iclock_devicecmd(
        self,
        **kwargs
    ):

        serial_number = (
            self._get_serial()
        )

        raw_data = (
            request.httprequest
            .get_data()
            .decode(
                'utf-8',
                errors='ignore',
            )
        )

        device = (
            self._get_or_create_device(
                serial_number
            )
        )

        if device:

            self._save_raw_request(
                device,
                serial_number,
                raw_data,
                table_name='DEVICECMD',
            )

        return request.make_response(
            'OK',
            headers=[
                (
                    'Content-Type',
                    'text/plain',
                ),
            ],
        )