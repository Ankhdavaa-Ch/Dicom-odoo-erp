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
        ('draft', 'Ноорог'),
        ('active', 'Идэвхтэй'),
        ('closed', 'Хаагдсан'),
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
            self.search([
                ('id', '!=', record.id),
                ('state', '=', 'active'),
            ]).write({'state': 'closed'})
            record.write({'state': 'active', 'active': True})

    def action_set_draft(self):
        self.write({'state': 'draft'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_generate_from_departments(self):
        """Make the selected structure an exact snapshot of active hr.department hierarchy."""
        Node = self.env['hdc.hr.structure.node']
        Department = self.env['hr.department']

        for structure in self:
            departments = Department.search(
                [('active', '=', True)],
                order='parent_path, id',
            )
            if not departments:
                raise UserError(_('Импортлох газар, нэгж олдсонгүй.'))

            department_ids = set(departments.ids)

            # Remove old/manual nodes which are not backed by a current department.
            # This removes stale roots such as old ХДК / Administration cards from the chart.
            stale_nodes = structure.node_ids.filtered(
                lambda n: not n.department_id or n.department_id.id not in department_ids
            )
            if stale_nodes:
                stale_nodes.with_context(skip_hdc_department_sync=True).unlink()

            node_by_department = {}

            # Create/update exactly one node for every active department.
            for department in departments:
                existing_node = Node.search([
                    ('structure_id', '=', structure.id),
                    ('department_id', '=', department.id),
                ], limit=1)

                mapping = {
                    'management': 'management',
                    'department': 'department',
                    'division': 'division',
                    'office': 'office',
                    'unit': 'unit',
                }
                node_type = mapping.get(department.hdc_unit_type, 'unit')
                if not department.parent_id:
                    node_type = 'organization'

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

                if existing_node:
                    existing_node.with_context(skip_hdc_department_sync=True).write(values)
                    node = existing_node
                else:
                    node = Node.with_context(skip_hdc_department_sync=True).create(values)

                node_by_department[department.id] = node

            # Rebuild parent-child links directly from hr.department.
            for department in departments:
                node = node_by_department[department.id]
                parent_node = (
                    node_by_department.get(department.parent_id.id)
                    if department.parent_id else False
                )
                node.with_context(skip_hdc_department_sync=True).write({
                    'parent_id': parent_node.id if parent_node else False,
                })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Амжилттай'),
                'message': _('Идэвхтэй hr.department мэдээллээс байгууллагын бүтэц бүрэн шинэчлэгдлээ.'),
                'type': 'success',
                'sticky': False,
            },
        }
