from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError


class HdcUserPasswordWizard(models.TransientModel):
    _name = 'hdc.user.password.wizard'
    _description = 'Хэрэглэгчийн нууц үг тохируулах'

    user_id = fields.Many2one(
        'res.users',
        string='Хэрэглэгч',
        required=True,
        readonly=True,
    )
    login = fields.Char(
        string='Нэвтрэх нэр',
        related='user_id.login',
        readonly=True,
    )
    password = fields.Char(
        string='Шинэ нууц үг',
        required=True,
    )
    password_confirm = fields.Char(
        string='Нууц үг давтах',
        required=True,
    )

    def action_set_password(self):
        self.ensure_one()
        if not self.env.user.has_group('base.group_system'):
            raise UserError(_('Зөвхөн системийн админ хэрэглэгчийн нууц үг тохируулах эрхтэй.'))

        if self.password != self.password_confirm:
            raise ValidationError(_('Нууц үг болон давтан оруулсан нууц үг таарахгүй байна.'))

        if len(self.password or '') < 8:
            raise ValidationError(_('Нууц үг хамгийн багадаа 8 тэмдэгттэй байна.'))

        # Use Odoo's standard res.users password write mechanism.
        # Odoo hashes the password; this module never stores plaintext passwords.
        self.user_id.sudo().write({'password': self.password})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Амжилттай'),
                'message': _('%s хэрэглэгчийн нууц үг шинэчлэгдлээ.') % self.user_id.login,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
