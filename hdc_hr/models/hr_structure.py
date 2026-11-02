from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class HdcHrStructure(models.Model):
    _name = 'hdc.hr.structure'
    _description = 'Байгууллагын бүтцийн хувилбар'
    _order = 'date_from desc, id desc'

    name = fields.Char(string='Бүтцийн нэр', required=True)
    code = fields.Char(string='Код')
    date_from = fields.Date(string='Эхлэх огноо', required=True)
    date_to = fields.Date(string='Дуусах огноо')
    state = fields.Selection([
        ('draft', 'Ноорог'), ('active', 'Идэвхтэй'), ('closed', 'Хаагдсан'),
    ], string='Төлөв', default='draft', required=True)
    active = fields.Boolean(string='Active', default=True)
    note = fields.Text(string='Тайлбар')
    node_ids = fields.One2many('hdc.hr.structure.node', 'structure_id', string='Бүтцийн нэгжүүд')
    node_count = fields.Integer(string='Нэгжийн тоо', compute='_compute_node_count')

    @api.depends('node_ids')
    def _compute_node_count(self):
        for record in self:
            record.node_count = len(record.node_ids)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from and record.date_to and record.date_to < record.date_from:
                raise ValidationError('Дуусах огноо эхлэх огнооноос өмнө байж болохгүй.')

    def action_activate(self):
        for record in self:
            self.search([('id', '!=', record.id), ('state', '=', 'active')]).write({'state': 'closed'})
            record.write({'state': 'active', 'active': True})

    def action_set_draft(self):
        self.write({'state': 'draft'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_generate_from_departments(self):
        """Build the approved DICOM chart, including position-only nodes."""
        Node = self.env['hdc.hr.structure.node']
        Department = self.env['hr.department']
        Job = self.env['hr.job']

        def normalized(value):
            return ' '.join((value or '').replace(',', ' ').lower().split())

        root_name = 'Хадгаламжийн даатгалын үндэсний хороо'
        for structure in self:
            roots = Department.search([('name', '=', root_name)])
            if len(roots) != 1:
                raise UserError(_('Үндэсний хорооны нэгж олдсонгүй эсвэл давхардсан байна.'))
            root = roots[0]
            departments = Department.search([('id', 'child_of', root.id)])
            names = {}
            for dep in departments:
                key = normalized(dep.name)
                if key in names:
                    raise UserError(_('Давхардсан нэгж: %s') % dep.name)
                names[key] = dep

            # Department hierarchy stays untouched: the CEO is a position, not a department.
            specs = [
                ('root', root_name, 'organization', None, root_name),
                ('secretary', 'Үндэсний хорооны нарийн бичгийн дарга', 'management', 'root', None),
                ('audit', 'Дотоод аудитын алба', 'office', 'root', 'Дотоод аудитын алба'),
                ('ceo', 'Гүйцэтгэх захирал', 'management', 'root', None),
                ('economist', 'Ерөнхий эдийн засагч', 'management', 'ceo', None),
                ('work', 'Ажлын алба', 'office', 'ceo', 'Ажлын алба'),
                ('finance', 'Санхүү бүртгэлийн алба', 'office', 'ceo', 'Санхүү бүртгэлийн алба'),
                ('claims_area', 'Нөхөн төлбөр, хөрөнгийн удирдлагын газар', 'department', 'ceo', 'Нөхөн төлбөр, хөрөнгийн удирдлагын газар'),
                ('claims', 'Нөхөн төлбөр, бүтцийн өөрчлөлтийн хэлтэс', 'division', 'claims_area', 'Нөхөн төлбөр, бүтцийн өөрчлөлтийн хэлтэс'),
                ('assets', 'Хөрөнгийн удирдлагын хэлтэс', 'division', 'claims_area', 'Хөрөнгийн удирдлагын хэлтэс'),
                ('risk_area', 'Эрсдэлийн удирдлага, хяналт шалгалтын газар', 'department', 'ceo', 'Эрсдэлийн удирдлага, хяналт шалгалтын газар'),
                ('inspection', 'Хяналт шалгалтын хэлтэс', 'division', 'risk_area', 'Хяналт шалгалтын хэлтэс'),
                ('risk', 'Эрсдэлийн удирдлагын хэлтэс', 'division', 'risk_area', 'Эрсдэлийн удирдлагын хэлтэс'),
                ('admin_area', 'Захиргаа, удирдлагын газар', 'department', 'ceo', 'Захиргаа, удирдлагын газар'),
                ('office', 'Тамгын хэлтэс', 'division', 'admin_area', 'Тамгын хэлтэс'),
                ('legal', 'Хуулийн хэлтэс', 'division', 'admin_area', 'Хуулийн хэлтэс'),
                ('external', 'Гадаад харилцааны хэлтэс', 'division', 'admin_area', 'Гадаад харилцааны хэлтэс'),
                ('it_area', 'Мэдээллийн технологийн газар', 'department', 'ceo', 'Мэдээллийн технологийн газар'),
                ('it', 'Мэдээллийн технологийн хэлтэс', 'division', 'it_area', 'Мэдээллийн технологийн хэлтэс'),
                ('security', 'Мэдээллийн аюулгүй байдлын ажилтан', 'management', 'it_area', None),
            ]
            missing = [name for _, name, _, _, dep_name in specs
                       if dep_name and normalized(dep_name) not in names]
            if missing:
                raise UserError(_('Бүтцийн нэгж олдсонгүй: %s') % ', '.join(missing))

            # Update existing nodes by department or stable code, without
            # changing the hr.department tree or any imported employee.
            existing = structure.node_ids
            nodes = {}
            for seq, (key, name, node_type, parent_key, dep_name) in enumerate(specs, 1):
                dep = names.get(normalized(dep_name)) if dep_name else False
                node = (existing.filtered(lambda n: n.department_id == dep)[:1]
                        if dep else existing.filtered(lambda n: n.code == 'chart_' + key)[:1])
                if not node and not dep:
                    node = existing.filtered(lambda n: not n.department_id and normalized(n.name) == normalized(name))[:1]
                values = {
                    'name': name,
                    'code': 'chart_' + key,
                    'sequence': seq * 10,
                    'node_type': node_type,
                    'structure_id': structure.id,
                    'department_id': dep.id if dep else False,
                    'manager_employee_id': dep.manager_id.id if dep and dep.manager_id else False,
                }
                if not dep:
                    matches = Job.search([('name', '=', name)])
                    if len(matches) == 1:
                        values['job_id'] = matches.id
                if node:
                    node.with_context(skip_hdc_department_sync=True).write(values)
                else:
                    node = Node.with_context(skip_hdc_department_sync=True).create(values)
                nodes[key] = node

            for key, name, node_type, parent_key, dep_name in specs:
                nodes[key].with_context(skip_hdc_department_sync=True).write({
                    'parent_id': nodes[parent_key].id if parent_key else False,
                })

            # Remove only nodes that are not part of the approved chart.
            stale = structure.node_ids - Node.browse([n.id for n in nodes.values()])
            if stale:
                stale.with_context(skip_hdc_department_sync=True).unlink()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Амжилттай'),
                'message': _('Хадгаламжийн даатгалын үндэсний хорооны бүтэц бүрэн шинэчлэгдлээ.'),
                'type': 'success',
                'sticky': False,
            },
        }
