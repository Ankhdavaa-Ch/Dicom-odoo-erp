from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HdcHrStructureNode(models.Model):
    _name = 'hdc.hr.structure.node'
    _description = 'Байгууллагын бүтцийн нэгж'
    _order = 'sequence, id'
    _parent_name = 'parent_id'
    _parent_store = True

    name = fields.Char(string='Нэр', required=True)
    code = fields.Char(string='Код')
    sequence = fields.Integer(string='Дараалал', default=10)

    structure_id = fields.Many2one(
        'hdc.hr.structure', string='Бүтцийн хувилбар',
        required=True, ondelete='cascade', index=True,
    )
    node_type = fields.Selection(
        [
            ('organization', 'Байгууллага'),
            ('management', 'Удирдлага'),
            ('department', 'Газар'),
            ('division', 'Хэлтэс'),
            ('office', 'Алба'),
            ('unit', 'Нэгж'),
        ],
        string='Төрөл', default='unit', required=True,
    )
    parent_id = fields.Many2one(
        'hdc.hr.structure.node', string='Харьяалах дээд нэгж',
        ondelete='cascade', index=True,
        domain="[('structure_id', '=', structure_id)]",
    )
    child_ids = fields.One2many(
        'hdc.hr.structure.node', 'parent_id', string='Харьяа нэгжүүд',
    )
    parent_path = fields.Char(index=True)

    department_id = fields.Many2one(
        'hr.department', string='Odoo Department',
        ondelete='set null', index=True,
    )
    job_id = fields.Many2one(
        'hr.job', string='Odoo Job Position', ondelete='set null',
    )
    manager_employee_id = fields.Many2one(
        'hr.employee', string='Удирдах ажилтан', ondelete='set null',
    )
    complete_name = fields.Char(
        string='Бүтэн нэр', compute='_compute_complete_name',
        store=True, recursive=True,
    )
    note = fields.Text(string='Тайлбар')

    _sql_constraints = [
        (
            'structure_department_unique',
            'unique(structure_id, department_id)',
            'Энэ газар/нэгж тухайн бүтцийн хувилбарт аль хэдийн бүртгэлтэй байна.'
        ),
    ]

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for record in self:
            record.complete_name = (
                '%s / %s' % (record.parent_id.complete_name, record.name)
                if record.parent_id else (record.name or '')
            )

    @api.onchange('department_id')
    def _onchange_department_id(self):
        for record in self:
            if not record.department_id:
                continue
            department = record.department_id
            record.name = department.name
            record.node_type = (
                self._convert_department_type(department.hdc_unit_type)
                if department.hdc_unit_type else
                ('organization' if not department.parent_id else 'unit')
            )
            record.manager_employee_id = department.manager_id
            record.code = (
                department.code if 'code' in department._fields
                else department.hdc_code if 'hdc_code' in department._fields
                else False
            )

    @api.model
    def _convert_department_type(self, department_type):
        return {
            'management': 'management',
            'department': 'department',
            'division': 'division',
            'office': 'office',
            'unit': 'unit',
        }.get(department_type, 'unit')

    def write(self, vals):
        """Active structure node edits update hr.department as the single source of truth."""
        result = super().write(vals)
        if self.env.context.get('skip_hdc_department_sync'):
            return result

        for record in self:
            if record.structure_id.state != 'active' or not record.department_id:
                continue

            department_vals = {}
            if 'name' in vals:
                department_vals['name'] = record.name
            if 'node_type' in vals and record.node_type != 'organization':
                reverse_type = {
                    'management': 'management',
                    'department': 'department',
                    'division': 'division',
                    'office': 'office',
                    'unit': 'unit',
                }
                department_vals['hdc_unit_type'] = reverse_type.get(record.node_type, 'unit')
            if 'manager_employee_id' in vals:
                department_vals['manager_id'] = record.manager_employee_id.id or False
            if 'parent_id' in vals:
                department_vals['parent_id'] = (
                    record.parent_id.department_id.id
                    if record.parent_id and record.parent_id.department_id
                    else False
                )

            if department_vals:
                record.department_id.with_context(
                    skip_hdc_structure_sync=True
                ).write(department_vals)
        return result

    @api.constrains('parent_id', 'structure_id')
    def _check_parent_structure(self):
        for record in self:
            if record.parent_id and record.parent_id.structure_id != record.structure_id:
                raise ValidationError('Харьяалах дээд нэгж ижил бүтцийн хувилбарт байх ёстой.')
