from odoo import fields, models, _


class HdcAttendanceDevice(models.Model):
    _name = 'hdc.attendance.device'
    _description = 'Ирцийн төхөөрөмж'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    # =========================================================
    # BASIC INFORMATION
    # =========================================================

    name = fields.Char(
        string='Төхөөрөмжийн нэр',
        required=True,
        tracking=True,
    )

    serial_number = fields.Char(
        string='Serial Number',
        required=True,
        index=True,
        tracking=True,
    )

    device_model = fields.Char(
        string='Загвар',
        default='ZKTeco Horus TL1',
    )

    location = fields.Char(
        string='Байршил',
    )

    active = fields.Boolean(
        string='Идэвхтэй',
        default=True,
    )

    note = fields.Text(
        string='Тайлбар',
    )

    # =========================================================
    # CONNECTION
    # =========================================================

    protocol = fields.Selection(
        [
            ('adms', 'ADMS / Push'),
            ('tcp', 'TCP/IP'),
        ],
        string='Холболтын төрөл',
        default='adms',
        required=True,
    )

    ip_address = fields.Char(
        string='IP Address',
        default='10.10.20.110',
    )

    port = fields.Integer(
        string='Port',
        default=4370,
    )

    comm_key = fields.Integer(
        string='Comm Key',
        default=0,
    )

    # =========================================================
    # STATUS
    # =========================================================

    last_seen = fields.Datetime(
        string='Сүүлд холбогдсон',
        readonly=True,
    )

    last_ip = fields.Char(
        string='Сүүлд холбогдсон IP',
        readonly=True,
    )

    log_count = fields.Integer(
        string='Raw log',
        compute='_compute_log_count',
    )

    # =========================================================
    # SQL CONSTRAINT
    # =========================================================

    _sql_constraints = [
        (
            'serial_number_unique',
            'unique(serial_number)',
            'Төхөөрөмжийн Serial Number давхардаж болохгүй.'
        ),
    ]

    # =========================================================
    # LOG COUNT
    # =========================================================

    def _compute_log_count(self):
        RawLog = self.env['hdc.attendance.raw.log']

        for device in self:
            device.log_count = RawLog.search_count([
                ('device_id', '=', device.id)
            ])

    # =========================================================
    # VIEW RAW LOGS
    # =========================================================

    def action_view_raw_logs(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Raw Logs'),
            'res_model': 'hdc.attendance.raw.log',
            'view_mode': 'list,form',
            'domain': [
                ('device_id', '=', self.id)
            ],
            'context': {
                'default_device_id': self.id,
            },
        }

    # =========================================================
    # OPEN PULL WIZARD
    # =========================================================

    def action_open_pull_wizard(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Ирц төхөөрөмжөөс татах'),
            'res_model': 'hdc.attendance.pull.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_device_id': self.id,
            },
        }