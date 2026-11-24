from odoo import fields, models

class ScheduleType(models.Model):
    _name = 'hdc.attendance.schedule.type'
    _description = 'Хуваарийн төрөл'
    _order = 'code, id'
    code = fields.Char(string='Код', required=True)
    name = fields.Char(string='Хуваарийн төрөл', required=True)
    _sql_constraints = [('code_unique', 'unique(code)', 'Хуваарийн код давхардахгүй.')]

class AttendanceHoliday(models.Model):
    _name = 'hdc.attendance.holiday'
    _description = 'Баярын өдөр'
    _order = 'date, id'
    name = fields.Char(string='Баярын өдөр', required=True)
    date = fields.Date(string='Огноо', required=True)
    _sql_constraints = [('date_unique', 'unique(date)', 'Огноо давхардахгүй.')]
