from odoo import models, fields

class Supervisorio(models.Model):
    _name = 'steril_supervisorio.supervisorio'
    _description = 'Descrição do Meu Modelo'

    name = fields.Char(string='Nome', required=True)
    campo_outro = fields.Integer(string='Campo Outro')
