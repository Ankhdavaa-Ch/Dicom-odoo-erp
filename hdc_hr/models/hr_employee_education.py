from odoo import models, fields


class HrEmployeeEducation(models.Model):
    _name = 'hr.employee.education'
    _description = 'Ажилтны боловсрол'
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
        string='Төгссөн огноо'
    )

    school_name = fields.Char(
        string='Сургуулийн нэр',
        required=True
    )

    degree = fields.Char(
        string='Боловсролын зэрэг'
    )

    profession = fields.Char(
        string='Эзэмшсэн мэргэжил'
    )

    country_id = fields.Many2one(
        'res.country',
        string='Улс'
    )

    grade = fields.Char(
        string='Дүн'
    )

    diploma_number = fields.Char(
        string='Дипломын дугаар'
    )