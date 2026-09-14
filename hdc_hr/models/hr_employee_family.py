from odoo import models, fields


class HrEmployeeFamily(models.Model):
    _name = 'hr.employee.family'
    _description = 'Ажилтны гэр бүлийн мэдээлэл'
    _order = 'birthday desc'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Ажилтан',
        required=True,
        ondelete='cascade'
    )

    name = fields.Char(
        string='Овог нэр',
        required=True
    )

    relationship = fields.Selection([
        ('spouse', 'Эхнэр / Нөхөр'),
        ('father', 'Эцэг'),
        ('mother', 'Эх'),
        ('son', 'Хүү'),
        ('daughter', 'Охин'),
        ('brother', 'Ах / Дүү эрэгтэй'),
        ('sister', 'Эгч / Дүү эмэгтэй'),
        ('other', 'Бусад'),
    ], string='Хэн болох')

    birthday = fields.Date(
        string='Төрсөн огноо'
    )

    organization = fields.Char(
        string='Ажилладаг байгууллага'
    )

    job_title = fields.Char(
        string='Албан тушаал'
    )

    phone = fields.Char(
        string='Утас'
    )