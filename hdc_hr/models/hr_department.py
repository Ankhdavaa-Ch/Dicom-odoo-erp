from odoo import models, fields, api


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    hdc_unit_type = fields.Selection(
        [
            ('management', 'Удирдлага'),
            ('department', 'Газар'),
            ('division', 'Хэлтэс'),
            ('office', 'Алба'),
            ('unit', 'Нэгж'),
        ],
        string='Нэгжийн төрөл'
    )

    @api.depends('name')
    @api.depends_context('hdc_short_name')
    def _compute_display_name(self):
        if self.env.context.get('hdc_short_name'):
            for department in self:
                department.display_name = department.name
        else:
            super()._compute_display_name()