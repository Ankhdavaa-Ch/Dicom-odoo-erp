from odoo import models, fields


class HrEmployeeQualification(models.Model):
    _name = 'hr.employee.qualification'
    _description = 'Ажилтны мэргэшил'
    _order = 'date_from desc'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Ажилтан',
        required=True,
        ondelete='cascade'
    )

    date_from = fields.Date(
        string='Эхэлсэн огноо'
    )

    date_to = fields.Date(
        string='Дууссан огноо'
    )

    organization = fields.Char(
        string='Хаана'
    )

    direction = fields.Char(
        string='Чиглэл'
    )

    certificate_number = fields.Char(
        string='Сертификатын дугаар'
    )

    country_id = fields.Many2one(
        'res.country',
        string='Улс'
    )