from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    attendance_device_user_id = fields.Char(
        string='Ирцийн төхөөрөмжийн ID',
        index=True,
        copy=False,
        help='ZKTeco төхөөрөмж дээрх ажилтны User ID',
    )

    attendance_device_id = fields.Many2one(
        'hdc.attendance.device',
        string='Үндсэн ирцийн төхөөрөмж',
        ondelete='set null',
    )
