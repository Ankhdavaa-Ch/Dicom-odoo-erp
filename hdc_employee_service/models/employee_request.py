from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


REQUEST_TYPES = [
    ('outside_work', 'Гадуур ажиллах хүсэлт'),
    ('leave', 'Чөлөө'),
    ('attendance_correction', 'Ирц нөхөн бүртгүүлэх'),
    ('annual_leave', 'Ээлжийн амралтын хүсэлт'),
    ('overtime', 'Илүү цагийн хүсэлт'),
    ('sick', 'Өвчтэй'),
    ('training_leave', 'Сургалтын чөлөө'),
]


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    hdc_approver_user_id = fields.Many2one(
        'res.users',
        string='Нэгжийн удирдлага',
        domain=[('share', '=', False)],
        help='Ажилтны үйлчилгээний хүсэлтийг батлах тухайн нэгжийн удирдлага.',
    )


class HdcEmployeeRequest(models.Model):
    _name = 'hdc.employee.request'
    _description = 'Ажилтны хүсэлт'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    @api.model
    def _default_employee_id(self):
        employee = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.uid)], limit=1)
        return employee.id if employee else False

    name = fields.Char(string='Хүсэлтийн дугаар', default='Шинэ', readonly=True, copy=False, tracking=True)
    request_type = fields.Selection(REQUEST_TYPES, string='Хүсэлтийн төрөл', required=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Ажилтан', required=True, readonly=True, default=_default_employee_id, tracking=True)
    department_id = fields.Many2one('hr.department', string='Нэгж', related='employee_id.department_id', store=True, readonly=True)
    approver_user_id = fields.Many2one('res.users', string='Одоогийн батлагч', readonly=True, tracking=True)
    current_approval_level = fields.Selection([('department', 'Хэлтсийн захирал'), ('division', 'Газрын захирал'), ('executive', 'Гүйцэтгэх захирал')], string='Одоогийн батлах шат', readonly=True, tracking=True)
    final_approval_level = fields.Selection([('department', 'Хэлтсийн захирал'), ('division', 'Газрын захирал'), ('executive', 'Гүйцэтгэх захирал')], string='Эцсийн батлах шат', readonly=True, tracking=True)
    date_from = fields.Datetime(string='Эхлэх огноо, цаг', required=True, tracking=True)
    date_to = fields.Datetime(string='Дуусах огноо, цаг', required=True, tracking=True)
    duration_minutes = fields.Integer(string='Нийт минут', compute='_compute_duration', store=True)
    duration_display = fields.Char(string='Хугацаа', compute='_compute_duration_display')
    reason = fields.Text(string='Тайлбар / үндэслэл', required=True, tracking=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Хавсралт')
    state = fields.Selection([
        ('draft', 'Ноорог'),
        ('submitted', 'Нэгжийн удирдлагад'),
        ('approved', 'Батлагдсан'),
        ('rejected', 'Буцаасан'),
        ('cancelled', 'Цуцалсан'),
    ], string='Төлөв', default='draft', required=True, readonly=True, tracking=True)
    submitted_at = fields.Datetime(string='Илгээсэн огноо', readonly=True)
    approved_at = fields.Datetime(string='Баталсан огноо', readonly=True)
    rejected_at = fields.Datetime(string='Буцаасан огноо', readonly=True)
    decision_note = fields.Text(string='Шийдвэрийн тайлбар', tracking=True)

    @api.depends('date_from', 'date_to')
    def _compute_duration(self):
        for rec in self:
            rec.duration_minutes = max(int((rec.date_to - rec.date_from).total_seconds() / 60), 0) if rec.date_from and rec.date_to else 0

    @api.depends('duration_minutes')
    def _compute_duration_display(self):
        for rec in self:
            minutes = rec.duration_minutes or 0
            rec.duration_display = f'{minutes // 60:02d}:{minutes % 60:02d}'

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_to <= rec.date_from:
                raise ValidationError(_('Дуусах огноо, цаг нь эхлэх огноо, цагаас хойш байна.'))

    @api.model_create_multi
    def create(self, vals_list):
        employee = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.uid)], limit=1)
        if not employee:
            raise UserError(_('Таны системийн хэрэглэгч ажилтны бүртгэлтэй холбогдоогүй байна.'))
        for vals in vals_list:
            vals['employee_id'] = employee.id
            if vals.get('name', 'Шинэ') == 'Шинэ':
                vals['name'] = self.env['ir.sequence'].next_by_code('hdc.employee.request') or 'Шинэ'
        return super().create(vals_list)

    def _employee_user(self):
        self.ensure_one()
        return self.employee_id.user_id

    def _notify_employee(self, summary, note):
        for rec in self:
            employee_user = rec._employee_user()
            if not employee_user:
                continue
            rec.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=employee_user.id,
                summary=summary,
                note=note,
            )

    def _approval_level_for_request(self):
        self.ensure_one()
        if self.request_type == 'annual_leave':
            return 'executive'
        if self.request_type == 'leave':
            return 'department' if self.duration_minutes < 24 * 60 else 'division'
        return 'department'

    def _approver_for_level(self, level):
        self.ensure_one()
        department = self.department_id
        if not department:
            return self.env['res.users']
        if level == 'department':
            return department.hdc_approver_user_id
        if level == 'division':
            parent = department.parent_id
            while parent and (parent.hdc_unit_type or '') not in ('department', 'management'):
                parent = parent.parent_id
            return parent.hdc_approver_user_id if parent else self.env['res.users']
        current = department
        while current:
            if (current.name or '').strip().lower() == 'гүйцэтгэх захирал':
                return current.hdc_approver_user_id or current.manager_id.user_id
            current = current.parent_id
        executive = self.env['hr.department'].sudo().search([('name', '=', 'Гүйцэтгэх захирал'), ('active', '=', True)], limit=1)
        return executive.hdc_approver_user_id or executive.manager_id.user_id

    def _next_level(self, level):
        return {'department': 'division', 'division': 'executive'}.get(level)

    def _schedule_approval_activity(self):
        for rec in self:
            if rec.approver_user_id:
                rec.activity_schedule('mail.mail_activity_data_todo', user_id=rec.approver_user_id.id, summary=_('Ажилтны хүсэлт батлах'), note=_('%s ажилтны %s хүсэлт таны батлах шатанд ирлээ.') % (rec.employee_id.name, dict(REQUEST_TYPES).get(rec.request_type)))

    def action_submit(self):
        for rec in self:
            if rec.employee_id.user_id != self.env.user:
                raise UserError(_('Зөвхөн өөрийн хүсэлтийг илгээх боломжтой.'))
            if rec.state not in ('draft', 'rejected'):
                raise UserError(_('Зөвхөн ноорог эсвэл буцаасан хүсэлтийг илгээх боломжтой.'))
            first_level = 'department'
            final_level = rec._approval_level_for_request()
            approver = rec._approver_for_level(first_level)
            if not approver:
                raise UserError(_('Таны хэлтсийн батлагч тохируулагдаагүй байна.'))
            if approver == self.env.user:
                raise UserError(_('Өөрийн хүсэлтийг өөрөө батлах боломжгүй. Дээд шатны батлагч тохируулна уу.'))

            # Close the employee's previous decision notification before resubmitting.
            employee_user = rec._employee_user()
            if employee_user:
                rec.activity_ids.filtered(lambda a: a.user_id == employee_user).action_done()

            rec.write({
                'state': 'submitted',
                'approver_user_id': approver.id,
                'current_approval_level': first_level,
                'final_approval_level': final_level,
                'submitted_at': fields.Datetime.now(),
                'approved_at': False,
                'rejected_at': False,
                'decision_note': False,
            })
            rec._schedule_approval_activity()
            rec.message_post(body=_('Хүсэлт %s руу илгээгдлээ.') % approver.name)

    def _check_approver(self):
        for rec in self:
            if rec.approver_user_id != self.env.user and not self.env.user.has_group('base.group_system'):
                raise UserError(_('Энэ хүсэлтийг шийдвэрлэх эрх танд байхгүй байна.'))

    def _close_approver_activities(self):
        for rec in self:
            activities = rec.activity_ids.filtered(
                lambda a: a.user_id == rec.approver_user_id
                and a.activity_type_id == self.env.ref('mail.mail_activity_data_todo')
            )
            activities.action_done()

    def action_approve(self):
        self._check_approver()
        for rec in self:
            if rec.state != 'submitted':
                raise UserError(_('Зөвхөн удирдлагад илгээсэн хүсэлтийг батална.'))
            old_approver = rec.approver_user_id
            old_level = rec.current_approval_level
            rec._close_approver_activities()
            if old_level == rec.final_approval_level:
                rec.write({'state': 'approved', 'approved_at': fields.Datetime.now(), 'approver_user_id': False})
                rec.message_post(body=_('%s баталж, хүсэлт эцэслэн батлагдлаа.') % old_approver.name)
                rec._notify_employee(_('Таны хүсэлт батлагдлаа'), _('%s хүсэлт тань эцэслэн батлагдлаа.') % dict(REQUEST_TYPES).get(rec.request_type))
                continue
            next_level = rec._next_level(old_level)
            next_approver = rec._approver_for_level(next_level)
            if not next_approver:
                raise UserError(_('Дараагийн шатны батлагч тохируулагдаагүй байна.'))
            rec.write({'current_approval_level': next_level, 'approver_user_id': next_approver.id})
            rec.message_post(body=_('%s батлав. Хүсэлт дараагийн шатны %s руу шилжлээ.') % (old_approver.name, next_approver.name))
            rec._schedule_approval_activity()

    def action_reject(self):
        self._check_approver()
        for rec in self:
            if rec.state != 'submitted':
                raise UserError(_('Зөвхөн удирдлагад илгээсэн хүсэлтийг буцаана.'))
            if not rec.decision_note:
                raise UserError(_('Буцаах шалтгааныг "Шийдвэрийн тайлбар" хэсэгт бичнэ үү.'))
            rec.write({'state': 'rejected', 'rejected_at': fields.Datetime.now()})
            rec._close_approver_activities()
            rec.message_post(body=_('Хүсэлт буцаагдлаа. Шалтгаан: %s') % rec.decision_note)
            rec._notify_employee(
                _('Таны хүсэлт буцаагдлаа'),
                _('%s хүсэлт буцаагдлаа. Шалтгаан: %s') % (dict(REQUEST_TYPES).get(rec.request_type), rec.decision_note),
            )

    def action_reset_to_draft(self):
        for rec in self:
            if rec.employee_id.user_id != self.env.user:
                raise UserError(_('Зөвхөн өөрийн хүсэлтийг засварлах боломжтой.'))
            if rec.state != 'rejected':
                raise UserError(_('Зөвхөн буцаасан хүсэлтийг засварлаж болно.'))
            employee_user = rec._employee_user()
            if employee_user:
                rec.activity_ids.filtered(lambda a: a.user_id == employee_user).action_done()
            rec.write({
                'state': 'draft',
                'approver_user_id': False,
                'current_approval_level': False,
                'final_approval_level': False,
                'decision_note': False,
            })
            rec.message_post(body=_('Хүсэлтийг засварлахаар ноорог төлөвт шилжүүллээ.'))

    def action_cancel(self):
        for rec in self:
            if rec.employee_id.user_id != self.env.user or rec.state not in ('draft', 'submitted'):
                raise UserError(_('Энэ хүсэлтийг цуцлах боломжгүй.'))
            rec._close_approver_activities()
            rec.write({'state': 'cancelled'})
