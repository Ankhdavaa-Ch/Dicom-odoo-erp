from datetime import timedelta
from odoo import api, fields, models
from odoo.exceptions import ValidationError

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
    date = fields.Date(string='Эхлэх огноо', required=True)
    date_end = fields.Date(string='Дуусах огноо')
    _sql_constraints = [('date_unique', 'unique(date)', 'Огноо давхардахгүй.')]

    @api.constrains('date', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_end and rec.date_end < rec.date:
                raise ValidationError('Дуусах огноо эхлэх огнооноос өмнө байж болохгүй.')

    @api.model
    def _holiday_days(self, start, end):
        result = {}
        for rec in self.sudo().search([('date', '<=', end), '|', ('date_end', '>=', start), '&', ('date_end', '=', False), ('date', '>=', start)]):
            day = max(start, rec.date)
            while day <= min(end, rec.date_end or rec.date):
                result[day] = rec.name
                day += timedelta(days=1)
        return result

    @api.model
    def seed_public_holidays(self, rows):
        if not self.env.is_superuser():
            raise ValidationError('Зөвхөн системийн шинэчлэлтээр ажиллуулна.')
        for name, start, end in rows:
            if not self.search_count([('date', '=', start)]):
                self.create({'name': name, 'date': start, 'date_end': end})
