from odoo import api, fields, models


class HdcHrStructureNode(models.Model):
    _name = 'hdc.hr.structure.node'
    _description = 'Байгууллагын бүтцийн нэгж'
    _order = 'sequence, id'
    _parent_name = 'parent_id'
    _parent_store = True

    name = fields.Char(
        string='Нэр',
        required=True,
    )

    code = fields.Char(
        string='Код',
    )

    sequence = fields.Integer(
        string='Дараалал',
        default=10,
    )

    structure_id = fields.Many2one(
        'hdc.hr.structure',
        string='Бүтцийн хувилбар',
        required=True,
        ondelete='cascade',
        index=True,
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
        string='Төрөл',
        default='unit',
        required=True,
    )

    parent_id = fields.Many2one(
        'hdc.hr.structure.node',
        string='Харьяалах дээд нэгж',
        ondelete='cascade',
        index=True,
        domain="[('structure_id', '=', structure_id)]",
    )

    child_ids = fields.One2many(
        'hdc.hr.structure.node',
        'parent_id',
        string='Харьяа нэгжүүд',
    )

    parent_path = fields.Char(
        index=True,
    )

    department_id = fields.Many2one(
        'hr.department',
        string='Odoo Department',
        ondelete='set null',
        index=True,
    )

    job_id = fields.Many2one(
        'hr.job',
        string='Odoo Job Position',
        ondelete='set null',
    )

    manager_employee_id = fields.Many2one(
        'hr.employee',
        string='Удирдах ажилтан',
        ondelete='set null',
    )

    complete_name = fields.Char(
        string='Бүтэн нэр',
        compute='_compute_complete_name',
        store=True,
        recursive=True,
    )

    note = fields.Text(
        string='Тайлбар',
    )

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
            if record.parent_id:
                record.complete_name = '%s / %s' % (
                    record.parent_id.complete_name,
                    record.name,
                )
            else:
                record.complete_name = record.name or ''

    @api.onchange('department_id')
    def _onchange_department_id(self):
        """
        Department гараар сонгоход
        нэр, төрөл, удирдах ажилтныг автоматаар авна.
        """
        for record in self:
            if not record.department_id:
                continue

            department = record.department_id

            record.name = department.name

            if 'hdc_unit_type' in department._fields:
                record.node_type = self._convert_department_type(
                    department.hdc_unit_type
                )

            if 'manager_id' in department._fields:
                record.manager_employee_id = department.manager_id

            if 'code' in department._fields:
                record.code = department.code or False

            elif 'hdc_code' in department._fields:
                record.code = department.hdc_code or False

    @api.model
    def _convert_department_type(self, department_type):
        """
        hr.department.hdc_unit_type утгыг
        hdc.hr.structure.node.node_type утга руу хөрвүүлнэ.
        """

        mapping = {
            'management': 'management',
            'department': 'department',
            'division': 'division',
            'office': 'office',
            'unit': 'unit',
        }

        return mapping.get(
            department_type,
            'unit'
        )