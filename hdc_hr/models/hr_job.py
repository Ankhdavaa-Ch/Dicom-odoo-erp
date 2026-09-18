from odoo import fields, models


class HrJob(models.Model):
    _inherit = 'hr.job'

    hdc_department_name = fields.Char(
        string='Department',
        related='department_id.name',
        readonly=True,
    )
