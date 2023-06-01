
from odoo import models, fields, api, _
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
import re
from odoo.exceptions import UserError, ValidationError


class SupervisorioCiclos(models.Model):
    _name = 'steril_supervisorio.ciclos'
    _description = 'Ciclos do supervisorio'

  

    name = fields.Char(
        string='Codigo Ciclo',
        
       
    )
    state = fields.Selection(string='Status', selection=[('iniciado', 'Iniciado'),
                                                         ('em_andamento', 'Em andamento'),
                                                         ('finalizado', 'Finalizado')], 
                                                         default='iniciado'
                                                         )
    data_inicio =  fields.Datetime()
    data_fim =  fields.Datetime()
    duration = fields.Float("Duração", compute = "_compute_duration")
    file = fields.Binary()
    
    supervisor = fields.Many2one(
         string='Supervisor',
         comodel_name='hr.employee',
        
    )
    
    operator = fields.Many2one(
        string='Operador',
        comodel_name='hr.employee',
        
    )

    equipment = fields.Many2one(
        string='Equipamento',
        comodel_name='engc.equipment'
        
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

   
    def verificar_conversao_tempo(self,string):
        try:
            tempo = datetime.strptime(string, '%H:%M:%S')
            return True
        except ValueError:
            return False
        
    def verificar_conversao_float(self,string):
        try:
            valor = float(string)
            return isinstance(valor, float)
        except ValueError:
            return False
    def concatenar_lista(self,lista):
        primeiro_item = lista.pop(0)
        restante_itens = ''.join(lista)
        return restante_itens
        
    def ler_arquivo_dados(self):
        dados = {}
        path = "/var/lib/odoo/filestore/odoo-steriliza/ciclos/"
        file = "TESTE_20230509_161354.txt"
        nome_arquivo = path + file
        with open(nome_arquivo, 'r') as arquivo:
            linhas = arquivo.readlines()
            

            for linha in linhas:
                #colunas = linha.strip().split('\s+')
                colunas = re.split('\s+', linha)
                colunas = [valor for valor in colunas if valor]
                print(colunas)
                if len(colunas) > 1:
                    if (self.verificar_conversao_tempo(colunas[0])):
                        print(colunas)
                        hora = colunas[0]
                        fase = colunas[1]
                        valores = [float(valor) for valor in colunas[2:]]

                        if hora not in dados:
                            dados[hora] = {}

                        dados[hora][fase] = valores

        return dados

    def action_get_file(self):
        
        self.ler_arquivo_dados()
