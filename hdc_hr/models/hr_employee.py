from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    employee_code = fields.Char(
        string='Ажилтны код'
    )

    family_name = fields.Char(
        string='Ургийн овог'
    )

    ethnicity = fields.Char(
        string='Яс үндэс'
    )

    birth_district = fields.Char(
        string='Төрсөн сум/дүүрэг'
    )

    family_member_count = fields.Integer(
        string='Ам бүлийн тоо'
    )

    private_district = fields.Char(
        string='Сум/дүүрэг'
    )

    private_khoroo = fields.Char(
        string='Хороо/баг'
    )

    family_ids = fields.One2many(
        'hr.employee.family',
        'employee_id',
        string='Гэр бүлийн мэдээлэл'
    )

    education_ids = fields.One2many(
        'hr.employee.education',
        'employee_id',
        string='Боловсрол'
    )

    qualification_ids = fields.One2many(
        'hr.employee.qualification',
        'employee_id',
        string='Мэргэшил'
    )

    employment_history_ids = fields.One2many(
        'hr.employee.employment.history',
        'employee_id',
        string='Хөдөлмөр эрхлэлт'
    )