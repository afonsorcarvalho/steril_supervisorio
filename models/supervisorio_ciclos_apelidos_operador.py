from odoo import models, fields

class SupervisorioCiclosApelidosOperador(models.Model):
    _name = 'steril_supervisorio.ciclos.apelidos.operador'
    _description = 'Faz a relacao entre o login dos equipamentos e o funcionario no odoo'

    name =  fields.Char(string='Apelido')
    operador = fields.Many2one(string='Operador', comodel_name='hr.employee', ondelete='restrict')
    active = fields.Boolean(default=True)


    _sql_constraints = [
        ('name_unique', 'unique(name)', 'O apelido deve ser único!'),
    ]