
from odoo import models, fields, api, _
from datetime import date, datetime,timedelta
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
import re
from odoo.exceptions import UserError, ValidationError
import os

class SupervisorioCiclos(models.Model):
    _name = 'steril_supervisorio.ciclos'
    _description = 'Ciclos do supervisorio'
    _order = 'data_inicio desc'

  

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
    modelo_ciclo = fields.Selection([('eto', 'ETO'),('vapor', 'VAPOR')], default='eto')
    supervisor = fields.Many2one(
         string='Supervisor',
         comodel_name='hr.employee',
        
    )
    dados_ciclo = fields.Html("Dados do Ciclo")
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
    
    def ler_diretorio_ciclos(self):
        ciclos = self.env['steril_supervisorio.ciclos']
        diretorio = "/var/lib/odoo/filestore/odoo-steriliza/ciclos/ETO03/"
        time_parametro_sistema = datetime.strptime(self.env['ir.config_parameter'].get_param('steril_supervisorio_ultima_atualizacao'), '%Y-%m-%d %H:%M:%S').date()
        print(time_parametro_sistema)
        
        for nome_pasta in os.listdir(diretorio):
            caminho_pasta = os.path.join(diretorio, nome_pasta)
          
            if os.path.isdir(caminho_pasta):
                print(nome_pasta)
                codigo_ciclo = nome_pasta

                # Verificar se o código de ciclo já existe no modelo
                ciclo_existente = ciclos.search([('name', '=', codigo_ciclo)])

                if not ciclo_existente:
                    # Obter a data e hora de início do ciclo a partir do nome do arquivo de texto
                    print(os.listdir(caminho_pasta))
                    nome_arquivo = os.listdir(caminho_pasta)
                    print(nome_arquivo)

                   

                    # Comparar a data de modificação com o parâmetro do sistema
                   
                    arquivos_txt = [arquivo for arquivo in nome_arquivo if arquivo.endswith('txt')]
                    print(arquivos_txt)
                    
                    for arquivo in arquivos_txt: 
                                #filtrando se foi modificado recentemente
                        timestamp_modificacao = os.path.getmtime(caminho_pasta+'/'+arquivo)
                        data_modificacao = datetime.fromtimestamp(timestamp_modificacao).date()
                        if data_modificacao >= time_parametro_sistema:
                            data_hora_inicio = arquivo.split('_')[1] + ' ' + arquivo.split('_')[2].replace('.txt', '')
                            print(data_hora_inicio)
                            # Converter a data e hora para o formato datetime
                            data_hora_inicio = datetime.strptime(data_hora_inicio, '%Y%m%d %H%M%S')
                            print(data_hora_inicio)

                            # Criar um novo registro para o código de ciclo
                            novo_ciclo = ciclos.create({'name': codigo_ciclo, 'data_inicio': data_hora_inicio})
                            print(novo_ciclo)
                            # Outras operações que você deseja realizar para o novo ciclo
                            # Por exemplo, ler arquivos dentro da pasta e atualizar campos do ciclo

        return True    
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

    def converter_para_float_time(self,diferenca_tempo):
        horas, minutos, segundos = map(int, diferenca_tempo.split(':'))
        valor_float = horas + (minutos / 60) + (segundos / 3600)
        return valor_float        
                
                
    def action_get_file(self):
        fases = ['LEAK-TEST',
                  'ACONDICIONAMENTO',
                  'UMIDIFICACAO',
                  'ESTERILIZACAO',
                  'LAVAGEM',
                  'AERACAO',
                  'CICLO FINALIZADO']
        file = "4354_20230531_210206.txt"
        str_dados_ciclo = ""
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
            str_dados_ciclo =str_dados_ciclo + f"{fases[index]}: {h}h {m}m {s}s<br/>"
        soma_total = self.calcular_soma_tempo(tempos)
        h,m,s = soma_total
        print(f"TOTAL: {h}h {m}m {s}s")
        str_dados_ciclo =str_dados_ciclo + f"<b>TOTAL</b>: {h}h {m}m {s}s<br/>"
        self.dados_ciclo = str_dados_ciclo

    def action_ler_diretorio(self):
        self.ler_diretorio_ciclos()