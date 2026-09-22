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
        """Rebuild chart from the DICOM organization root and its descendants only."""
        Node = self.env['hdc.hr.structure.node']
        Department = self.env['hr.department']

        for structure in self:
            root = Department.search([
                ('active', '=', True),
                ('name', '=', 'Хадгаламжийн даатгалын үндэсний хороо'),
            ], limit=1)

            if not root:
                raise UserError(_('Үндсэн нэгж "Хадгаламжийн даатгалын үндэсний хороо" олдсонгүй.'))

            departments = Department.search([
                ('active', '=', True),
                ('id', 'child_of', root.id),
            ], order='parent_path, id')

            if not departments:
                raise UserError(_('Байгууллагын бүтцэд оруулах нэгж олдсонгүй.'))

            department_ids = set(departments.ids)

            # The chart is an exact snapshot of the selected root tree.
            # Remove Administration, ХДК and any other node outside that tree.
            stale_nodes = structure.node_ids.filtered(
                lambda n: not n.department_id or n.department_id.id not in department_ids
            )
            if stale_nodes:
                stale_nodes.with_context(skip_hdc_department_sync=True).unlink()

            node_by_department = {}
            mapping = {
                'management': 'management',
                'department': 'department',
                'division': 'division',
                'office': 'office',
                'unit': 'unit',
            }

            for department in departments:
                node = Node.search([
                    ('structure_id', '=', structure.id),
                    ('department_id', '=', department.id),
                ], limit=1)

                node_type = 'organization' if department.id == root.id else mapping.get(department.hdc_unit_type, 'unit')
                # Existing imported data may not have unit types yet. Infer the obvious
                # organization levels from their names so the chart is readable.
                if department.id != root.id and (not department.hdc_unit_type or node_type == 'unit'):
                    name = (department.name or '').strip().lower()
                    if name == 'гүйцэтгэх захирал':
                        node_type = 'management'
                    elif name.endswith(' газар'):
                        node_type = 'department'
                    elif name.endswith(' хэлтэс'):
                        node_type = 'division'
                    elif name.endswith(' алба'):
                        node_type = 'office'

                values = {
                    'name': department.name,
                    'structure_id': structure.id,
                    'department_id': department.id,
                    'node_type': node_type,
                    'manager_employee_id': department.manager_id.id if department.manager_id else False,
                }
                if 'code' in department._fields:
                    values['code'] = department.code or False
                elif 'hdc_code' in department._fields:
                    values['code'] = department.hdc_code or False

                if node:
                    node.with_context(skip_hdc_department_sync=True).write(values)
                else:
                    node = Node.with_context(skip_hdc_department_sync=True).create(values)
                node_by_department[department.id] = node

            # DICOM chart rule: these three units report directly to the Executive Director.
            executive = departments.filtered(
                lambda d: (d.name or '').strip().lower() == 'гүйцэтгэх захирал'
            )[:1]
            direct_reports = {
                'ерөнхий эдийн засагч': 'management',
                'ажлын алба': 'office',
                'санхүү бүртгэлийн алба': 'office',
            }

            if executive:
                for department in departments:
                    normalized_name = (department.name or '').strip().lower()
                    if normalized_name in direct_reports and department.parent_id != executive:
                        department.with_context(skip_hdc_structure_sync=True).write({
                            'parent_id': executive.id,
                            'hdc_unit_type': direct_reports[normalized_name],
                        })

            for department in departments:
                node = node_by_department[department.id]
                normalized_name = (department.name or '').strip().lower()
                is_direct_report = bool(executive and normalized_name in direct_reports)

                if is_direct_report:
                    parent_node = node_by_department.get(executive.id)
                else:
                    parent_node = (
                        node_by_department.get(department.parent_id.id)
                        if department.id != root.id and department.parent_id else False
                    )

                node.with_context(skip_hdc_department_sync=True).write({
                    'parent_id': parent_node.id if parent_node else False,
                    'node_type': direct_reports.get(normalized_name, node.node_type),
                })

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
