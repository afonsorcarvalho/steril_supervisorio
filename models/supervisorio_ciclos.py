
from odoo import models, fields, api, _
from datetime import date, datetime,timedelta
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
        
    def ler_arquivo_dados(self,file):
        dados = []
        segmentos = []
        path = "/var/lib/odoo/filestore/odoo-steriliza/ciclos/ETO03/4354/"
       # file = "TESTE_20230509_161354.txt"
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
                        if(self.verificar_conversao_float(colunas[1])):
                            dados.append(colunas)
                        else:
                            dados.append([colunas[0],' '.join(colunas[1:])])
                            segmentos.append([colunas[0],' '.join(colunas[1:])])

        return [dados,segmentos]
    
    def calcular_diferenca_tempo(self,lista):
        diferenca_tempo = []
        for i in range(1, len(lista)):
            hora1 = datetime.strptime(lista[i-1][0], '%H:%M:%S')
            hora2 = datetime.strptime(lista[i][0], '%H:%M:%S')
            diferenca = hora2 - hora1

            # Extrair horas, minutos e segundos da diferença
            horas = diferenca.seconds // 3600
            minutos = (diferenca.seconds // 60) % 60
            segundos = diferenca.seconds % 60

            diferenca_tempo.append((horas, minutos, segundos))
        return diferenca_tempo
    
    def get_tempo_duracao_segmentos(self,segmentos):
        fases = ['LEAK-TEST',
                  'ACONDICIONAMENTO',
                  'UMIDIFICACAO',
                  'ESTERILIZACAO',
                  'LAVAGEM',
                  'AERACAO',
                  'CICLO FINALIZADO']
        dados_fases = []
        for linha in segmentos:
            if linha[1] in fases:
                dados_fases.append(linha)
        tempos_duracao = []
        size_fases = len(fases)
        print(dados_fases)
           
    def calcular_soma_tempo(self, diferencas_tempo):
        soma_tempo = timedelta()  # Inicializa a soma como zero

        for diferenca in diferencas_tempo:
            horas, minutos, segundos = diferenca
            delta = timedelta(hours=horas, minutes=minutos, seconds=segundos)
            soma_tempo += delta
        # Extrair horas, minutos e segundos da soma total
        horas_soma = soma_tempo.seconds // 3600
        minutos_soma = (soma_tempo.seconds // 60) % 60
        segundos_soma = soma_tempo.seconds % 60
        return (horas_soma, minutos_soma, segundos_soma)

            
            
                
    def action_get_file(self):
        fases = ['LEAK-TEST',
                  'ACONDICIONAMENTO',
                  'UMIDIFICACAO',
                  'ESTERILIZACAO',
                  'LAVAGEM',
                  'AERACAO',
                  'CICLO FINALIZADO']
        file = "4354_20230531_210206.txt"
        #lendo arquivo com os dados do ciclo
        result = self.ler_arquivo_dados(file)

        #filtrando apenas as fases
        segmentos_filtered = [x for x in result[1] if x[1] in fases]
        print(segmentos_filtered)

        #calculando os tempos de cada fase
        tempos  = self.calcular_diferenca_tempo(segmentos_filtered)

        #mostrando resultados
        for tempo in tempos:
            index = tempos.index(tempo)
            h,m,s = tempo
            print(f"{fases[index]}: {h}h {m}m {s}s")
        soma_total = self.calcular_soma_tempo(tempos)
        h,m,s = soma_total
        print(f"TOTAL: {h}h {m}m {s}s")
