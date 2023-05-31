
from odoo import models, fields, api, _
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT

from odoo.exceptions import UserError, ValidationError


class SupervisorioCiclos(models.Model):
    _name = 'steril_supervisorio.ciclos'
    _description = 'Ciclos do supervisorio'

    _rec_name = 'name'
    _order = 'name ASC'

    name = fields.Char(
        string='Codigo',
        required=True,
        default=lambda self: _('New'),
        copy=False
    )
    data_inicio =  fields.Datetime()
    data_fim =  fields.Datetime()
    duration = fields.Float("Duração", compute = "_compute_duration")
    file = fields.Binary()
    
    supervisor = fields.Many2one(
        string='supervisor',
        comodel_name='hr.employee',
        ondelete='restrict',
    )
    
    operator = fields.Many2one(
        string='operador',
        comodel_name='hr.employee',
        ondelete='restrict',
    )

    equipment = fields.Many2one(
        string='Equipamento',
        comodel_name='eng_os.equipment',
        ondelete='restrict',
    )

    @api.depends('data_inicio', 'data_fim')
    def _compute_duration(self):
        for record in self:
            if record.data_inicio and record.data_fim:
                # Calcula a diferença de tempo
                start_datetime = fields.Datetime.from_string(record.data_inicio)
                end_datetime = fields.Datetime.from_string(record.data_fim)
                duration = (end_datetime - start_datetime).total_seconds() / 3600  # Resultado em horas
                record.duration = duration
            else:
                record.duration = 0.0
                
    def ler_arquivo_txt(self, caminho_arquivo):
        with open(caminho_arquivo, 'r') as arquivo:
            linhas = arquivo.readlines()
            for linha in linhas:
                dados = linha.strip().split(' ')
                if len(dados) == 3:
                    hora = float(dados[0])
                    numero1 = float(dados[1])
                    numero2 = float(dados[2])
                    self.env['meu.modelo'].create({
                        'hora': hora,
                        'numero1': numero1,
                        'numero2': numero2,
                    })