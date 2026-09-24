from odoo import api, fields, models
from odoo.exceptions import ValidationError


APPROVER_TYPES = [
    ('department', 'Хэлтсийн захирал'),
    ('division', 'Газрын захирал'),
    ('executive', 'Гүйцэтгэх захирал'),
    ('user', 'Тодорхой хэрэглэгч'),
]


class HdcApprovalWorkflow(models.Model):
    _name = 'hdc.approval.workflow'
    _description = 'Хүсэлтийн ажлын урсгал'
    _order = 'request_type, name'

    name = fields.Char(string='Ажлын урсгал', required=True)
    request_type = fields.Selection(selection=lambda self: self.env['hdc.employee.request']._fields['request_type'].selection, string='Хүсэлтийн төрөл', required=True)
    active = fields.Boolean(default=True)
    step_ids = fields.One2many('hdc.approval.workflow.step', 'workflow_id', string='Батлах шатууд')

    _sql_constraints = [
        ('request_type_unique', 'unique(request_type)', 'Нэг хүсэлтийн төрөлд нэг идэвхтэй ажлын урсгал ашиглана.'),
    ]


class HdcApprovalWorkflowStep(models.Model):
    _name = 'hdc.approval.workflow.step'
    _description = 'Хүсэлтийн ажлын урсгалын шат'
    _order = 'workflow_id, sequence, id'

    workflow_id = fields.Many2one('hdc.approval.workflow', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Дараалал', default=10, required=True)
    name = fields.Char(string='Шатны нэр', required=True)
    approver_type = fields.Selection(APPROVER_TYPES, string='Батлагч', required=True, default='department')
    approver_user_id = fields.Many2one('res.users', string='Тодорхой батлагч', domain=[('share', '=', False)])
    approve_finish = fields.Boolean(string='Баталбал дуусгах', help='Идэвхтэй бол энэ шат батлагдахад хүсэлт эцэслэн батлагдана.')
    reject_to_draft = fields.Boolean(string='Буцаавал ажилтанд', default=True)

    @api.constrains('approver_type', 'approver_user_id')
    def _check_specific_user(self):
        for rec in self:
            if rec.approver_type == 'user' and not rec.approver_user_id:
                raise ValidationError('Тодорхой хэрэглэгч төрлийн шатанд батлагч хэрэглэгч сонгоно уу.')
