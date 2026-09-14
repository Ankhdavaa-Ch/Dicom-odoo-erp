from odoo import models, fields


class HrEmployeeEmploymentHistory(models.Model):
    _name = 'hr.employee.employment.history'
    _description = 'Ажилтны хөдөлмөр эрхлэлтийн түүх'
    _order = 'date_from desc'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Ажилтан',
        required=True,
        ondelete='cascade'
    )

    date_from = fields.Date(
        string='Эхэлсэн огноо',
        required=True
    )

    date_to = fields.Date(
        string='Дууссан огноо'
    )

    organization = fields.Char(
        string='Байгууллага',
        required=True
    )

    department = fields.Char(
        string='Салбар нэгж'
    )

    job_title = fields.Char(
        string='Албан тушаал'
    )

    leave_reason = fields.Char(
        string='Гарсан шалтгаан'
    )

    years_worked = fields.Char(
        string='Ажилласан хугацаа'
    )

    is_current = fields.Boolean(
        string='Одоо ажиллаж байгаа'
    )