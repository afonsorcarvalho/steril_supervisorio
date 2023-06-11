from odoo import models, fields, api, _
import io
import base64
from datetime import date, datetime,timedelta
from dateutil import tz, parser
import numpy as np
import matplotlib.pyplot as plt

import json


from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
import pytz
import re
from odoo.exceptions import UserError, ValidationError
import os


import logging
_logger = logging.getLogger(__name__)


FASES = ['LEAK-TEST',
                  'ACONDICIONAMENTO',
                  'UMIDIFICACAO',
                  'ESTERILIZACAO',
                  'LAVAGEM',
                  'AERACAO',
                  'CICLO ABORTADO',
                  'CICLO FINALIZADO']
fuso_horario = pytz.timezone('America/Sao_Paulo')  # Exemplo de fuso horário (America/Sao_Paulo)

def is_float(value):
        try:
            float(value)
            return True
        except ValueError:
            return False
        
def obter_faixas_indices_fases(dados, segmentos):
    indices_segmentos = []
    for segmento in segmentos:
        indices = [i for i, item in enumerate(dados) if len(item) > 1 and item[1] == segmento]
        if indices:
            indices_segmentos.append(indices[0])
    result =   [[indices_segmentos[i], indices_segmentos[i+1]] for i in range(len(indices_segmentos)-1)]
    return result

class SupervisorioCiclos(models.Model):
    _name = 'steril_supervisorio.ciclos'

    _description = 'Ciclos do supervisorio'
    _order = 'data_inicio desc'
    _inherit = ['mail.thread', "mail.activity.mixin"]

    name = fields.Char(
        string='Codigo Carga',
    )
    codigo_ciclo = fields.Char("Codigo Ciclo")
    state = fields.Selection(string='Status', selection=[('iniciado', 'Iniciado'),
                                                         ('em_andamento', 'Em andamento'),
                                                         ('finalizado', 'Finalizado') ,
                                                         ('incompleto', 'Incompleto') ,
                                                         ('esperando_biologico', 'Esperando Resultado BI'), 
                                                         ('esperando_aprovacao_supervisor', 'Esperando Aprovação Supervisor'), 
                                                         ('abortado', 'Abortado'), 
                                                         ('concluido', 'Concluído'), 
                                                         ('cancelado', 'Cancelado'), 
                                                         ('reprovado', 'Reprovado'), 
                                                        
                                                         ], default='iniciado', tracking=True
                                                         )
    data_inicio =  fields.Datetime()
    data_fim =  fields.Datetime(tracking=True)
    duration = fields.Float("Duração", compute = "_compute_duration",store=True)
    file = fields.Binary()
    modelo_ciclo = fields.Selection([('eto', 'ETO'),('vapor', 'VAPOR')], default='eto')
    resultado_bi = fields.Selection(selection = [('positivo','Positivo'),('negativo','Negativo')])
    data_incubacao_bi = fields.Datetime(tracking=True)
    data_leitura_resultado_bi = fields.Datetime(tracking=True)
    def _get_default_supervisor(self):
        supervisor_default = self.env['ir.config_parameter'].sudo().get_param('steril_supervisorio.supervisor_ciclos')
        return self.env['hr.employee'].search([('id','=', supervisor_default)])
    
    supervisor = fields.Many2one(
         string='Supervisor',
         comodel_name='hr.employee',
         default=_get_default_supervisor)
        
    
    tempos_ciclo = fields.Html("Tempos do Ciclo")
    estatisticas_ciclo = fields.Html("Estatísticas do Ciclo")
    operator = fields.Many2one(
        string='Operador',
        comodel_name='hr.employee',
        
    )
    path_file_ciclo_txt = fields.Char()
    equipment = fields.Many2one(
        string='Equipamento',
        comodel_name='engc.equipment'
        
    )
    fases = fields.One2many(string='Fases',comodel_name='steril_supervisorio.ciclos.fases.eto',inverse_name='ciclo' )
    grafico_ciclo = fields.Binary()
    motivo_reprovado = fields.Char()

    _sql_constraints = [('codigo_ciclo_equipment_unique', 'unique(codigo_ciclo, equipment)',
                         'Codigo de ciclo duplicado '
                         'Não é permitido')]
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
    
    def _arquivo_modificado_recentemente(self, path_arquivo):
        #pega paramento do sistema com a data da ultima atualizacao dos ciclos
        data_ultima_atualizacao_str = self.env['ir.config_parameter'].get_param('steril_supervisorio_ultima_atualizacao')
        data_ultima_atualizacao =  parser.parse(data_ultima_atualizacao_str).astimezone(pytz.utc)
              
        
        _logger.info(f"Ultima Atualização: {data_ultima_atualizacao}")

       
        timestamp_modificacao = os.path.getmtime(path_arquivo)
        data_modificacao = datetime.fromtimestamp(timestamp_modificacao, tz=fuso_horario)

        
        # _logger.info(f"Data original de modificação do arquivo {path_arquivo}: {data_modificacao}")
        # data_modificacao = fuso_horario.localize(data_ultima_atualizacao).astimezone(pytz.utc).replace(tzinfo=None)                 
        _logger.info(f"Data modificação do arquivo {path_arquivo}: {data_modificacao}")
        if data_modificacao >= data_ultima_atualizacao:
            _logger.info(f"A data {data_modificacao} é maior ou igual  {data_ultima_atualizacao}")
            return True
        else:
            _logger.info(f"A data {data_modificacao} é menor que  {data_ultima_atualizacao}")
            return False
        
    def convert_date_str_file_to_datetime(self,date_str):
        data_hora = datetime.strptime(date_str, '%Y%m%d %H%M%S')
        fuso_horario_usuario = fuso_horario
        data_hora_inicio_usuario = fuso_horario_usuario.localize(data_hora)
        date_return = data_hora_inicio_usuario.astimezone(pytz.utc).replace(tzinfo=None)
        return date_return

    def ler_diretorio_ciclos(self,equipment_alias):
        """
        Lê o diretório contendo os ciclos do equipamento e cria registros para cada ciclo encontrado.
        Adiciona pdf do ciclo em anexo ao registro

        :param self: Objeto que invoca o método.
        :param equipment_alias: Alias do equipamento.
        :return: True se a leitura e criação dos ciclos foram concluídas com sucesso.

        Exemplo de uso:
        >>> objeto = MeuModelo()
        >>> alias = 'equipamento1'
        >>> resultado = objeto.ler_diretorio_ciclos(alias)
        >>> print(resultado)
        True
        """
         
        dbname = self.env.cr.dbname
        
        #lendo do diretorio que é atualizado pela IHMs dos equipamentos
        diretorio = f"/var/lib/odoo/filestore/{dbname}/ciclos/{equipment_alias}/" 
        equipment = self.env['engc.equipment'].search([('apelido','=like',equipment_alias )])
        
        for nome_pasta in os.listdir(diretorio):
            caminho_pasta = os.path.join(diretorio, nome_pasta)
            _logger.info(f"Lendo diretorio: {caminho_pasta}")
           
          
            if os.path.isdir(caminho_pasta):

                
                codigo_carga = nome_pasta
                lista_de_arquivos = os.listdir(caminho_pasta)
                _logger.info(f"Lista de arquivo do diretorio: {lista_de_arquivos}")

                # filtrando apenas os arquivos tipo txt
                lista_de_arquivos_txt = [arquivo for arquivo in lista_de_arquivos if arquivo.endswith('txt')]
                _logger.info(f"Lista de arquivos encontrada: {lista_de_arquivos_txt}") 
                for arquivo in lista_de_arquivos_txt:  
                    path_full_file = caminho_pasta+'/'+arquivo
                   
                    if self._arquivo_modificado_recentemente(path_full_file):
                        arquivo_partes = arquivo.split('_')
                        data_hora_inicio_str = arquivo_partes[1] + ' ' + arquivo_partes[2].replace('.txt', '')
                        codigo_ciclo = arquivo.replace('.txt','')
                        
                        # Converter a data e hora para o formato datetime
                        data_inicio = self.convert_date_str_file_to_datetime(data_hora_inicio_str)
                        # Verificar se o código de ciclo já existe no modelo
                        ciclo_existente = self.env['steril_supervisorio.ciclos'].search([('codigo_ciclo', '=', codigo_ciclo)])
                        _logger.debug(ciclo_existente)
                        if len(ciclo_existente) < 1: #não existe ciclo
                            
                            operador_id = self._ler_arquivo_operador(path_full_file)
                            # procurando equipamento pelo apelido

                            #    Criar um novo registro para o código de ciclo
                            ciclo = self.env['steril_supervisorio.ciclos'].create({
                                'name': codigo_carga,
                                'codigo_ciclo': codigo_ciclo,
                                'data_inicio': data_inicio,
                                'operator': operador_id,
                                'equipment': equipment.id or None,
                                'path_file_ciclo_txt' : path_full_file,
                                }
                                )

                        else:
                            ciclo_existente.write({'path_file_ciclo_txt' : path_full_file})
                            ciclo=ciclo_existente
                        
                        print(ciclo)
                        if(ciclo and ciclo.state not in ['finalizado']):
                            ciclo.get_chart_image()
                            ciclo.adicionar_anexo_pdf()
                            ciclo.add_data_file_to_record()

        return True   
    # def _sanitiza_dados(self,dados):
    #     dados_sanitizados = []
    #     for linha in dados:
    #         if len(linha) > 1:

    def _calcular_estatisticas_por_fase(self,dados):
        estatisticas = {}
        fase_atual = None 
        dados_filtered = [x for x in dados if not x[1].startswith(('PULSO','INJETANDO ETO','CICLO FINALIZADO'))]
      
       
        for linha in dados_filtered:
            hora = linha[0]
            if len(linha) == 2:
                if linha[1].startswith('PULSO'):
                    fase_atual = None
                else:
                    fase_atual = linha[1]
                    estatisticas[fase_atual] = {
                        'valores1': [],
                        'valores2': [],
                    }
            else:
                if fase_atual:
                    valores1 = estatisticas[fase_atual]['valores1']
                    valores2 = estatisticas[fase_atual]['valores2']
                    valores1.append(float(linha[1]))
                    valores2.append(float(linha[2]))

        estatisticas_finais = {}

        for fase, valores_fase in estatisticas.items():
            valores1 = valores_fase['valores1']
            valores2 = valores_fase['valores2']
            if len(valores1) > 0 and len(valores2) > 0:
                estatisticas_finais[fase] = {
                    'valor_minimo1': min(valores1 or []),
                    'valor_maximo1': max(valores1),
                    'media1': sum(valores1) / len(valores1),
                    'valor_minimo2': min(valores2 or []),
                    'valor_maximo2': max(valores2),
                    'media2': sum(valores2) / len(valores2),
            }

        return estatisticas_finais
 
    def _calcular_tempo_decorrido(self,lista):
        formato = '%H:%M:%S'

        if not lista:
            return None

        primeiro_item = datetime.strptime(lista[0][0], formato)
        ultimo_item = datetime.strptime(lista[-1][0], formato)

        diferenca_tempo = ultimo_item - primeiro_item

        return diferenca_tempo
    
    def ler_fim_de_ciclo(self,dados,segmentos):
        
        # verifica se ciclo foi finalizado
        is_finish =  any('CICLO FINALIZADO' in item for item in segmentos)

        if is_finish:
            # retorna a hora do ciclo finalizado
            
            return [True,self._calcular_tempo_decorrido(segmentos)]
        else:
            # retorna a a ultima hora do arquivo
            return [False,self._calcular_tempo_decorrido(dados)]
           
    def get_data_time_fim_de_ciclo(self,dados,segmentos):   
        formato = '%H:%M:%S'
        is_finish, data_time_delta  = self.ler_fim_de_ciclo(dados,segmentos)
      
        return [is_finish,timedelta(seconds=data_time_delta.seconds)]
       



    def ler_arquivo_dados(self,file):
        """
        Lê um arquivo de dados e extrai as informações.

        :param file: Caminho do arquivo a ser lido.
        :type file: str
        :return: Uma lista contendo os dados extraídos do arquivo e uma lista de segmentos.
        :rtype: list

        Exemplo de uso:
            arquivo = '/caminho/do/arquivo.txt'
            dados, segmentos = self.ler_arquivo_dados(arquivo)
            print(dados)
            print(segmentos)
        """

        dados = []
        segmentos = []
        nome_arquivo = file
        with open(nome_arquivo, 'r') as arquivo:
            linhas = arquivo.readlines()
  
            for linha in linhas:
                #colunas = linha.strip().split('\s+')
                colunas = re.split('\s+', linha)
                colunas = [valor for valor in colunas if valor]
               
                if len(colunas) > 1:
                    if (self.verificar_conversao_tempo(colunas[0])):
                        if(self.verificar_conversao_float(colunas[1])):
                            dados.append(colunas)
                        else:
                            dados.append([colunas[0],' '.join(colunas[1:])])
                            segmentos.append([colunas[0],' '.join(colunas[1:])])
        
        return [dados,segmentos]
    
    def calcular_diferenca_tempo(self,lista):
        diferenca_tempo = {}
        for i in range(1, len(lista)):
            hora1 = datetime.strptime(lista[i-1][0], '%H:%M:%S')
            hora2 = datetime.strptime(lista[i][0], '%H:%M:%S')
            diferenca = hora2 - hora1

            # Extrair horas, minutos e segundos da diferença
            horas = diferenca.seconds // 3600
            minutos = (diferenca.seconds // 60) % 60
            segundos = diferenca.seconds % 60

            diferenca_tempo[lista[i-1][1]] = (horas, minutos, segundos)
        return diferenca_tempo
    
           
    def calcular_soma_tempo(self, diferencas_tempo):
        """
        Calcula a soma de uma lista de diferenças de tempo.

        :param self: Objeto que invoca o método.
        :param diferencas_tempo: Lista contendo as diferenças de tempo no formato (horas, minutos, segundos).
        :return: Tupla contendo a soma total das horas, minutos e segundos.

        Exemplo de uso:
        >>> objeto = MeuModelo()
        >>> diferencas = [(2, 30, 0), (1, 45, 30), (0, 15, 45)]
        >>> resultado = objeto.calcular_soma_tempo(diferencas)
        >>> print(resultado)
        (4, 31, 15)
        """

        soma_tempo = timedelta()  # Inicializa a soma como zero
      
        for diferenca in diferencas_tempo:
            horas, minutos, segundos = diferencas_tempo[diferenca]
            delta = timedelta(hours=horas, minutes=minutos, seconds=segundos)
            soma_tempo += delta
        # Extrair horas, minutos e segundos da soma total
        horas_soma = soma_tempo.seconds // 3600
        minutos_soma = (soma_tempo.seconds // 60) % 60
        segundos_soma = soma_tempo.seconds % 60
        return (horas_soma, minutos_soma, segundos_soma)

    def converter_para_float_time(self,diferenca_tempo):
        """
        Converte uma diferença de tempo no formato "hh:mm:ss" para um valor float representando o tempo em horas.

        :param self: Objeto que invoca o método.
        :param diferenca_tempo: String contendo a diferença de tempo no formato "hh:mm:ss".
        :return: Valor float representando o tempo em horas.

        Exemplo de uso:
        >>> objeto = MeuModelo()
        >>> tempo = "02:30:45"
        >>> resultado = objeto.converter_para_float_time(tempo)
        >>> print(resultado)
        2.5125
        """
        horas, minutos, segundos = map(int, diferenca_tempo.split(':'))
        valor_float = horas + (minutos / 60) + (segundos / 3600)
        return valor_float        

    def adicionar_anexo_pdf(self):
        """
        Adiciona um anexo ao modelo atual a partir de um arquivo local. 

        
        :param caminho_arquivo: Caminho completo do arquivo local a ser anexado com o nome do arquivo .
        :return: O objeto de anexo criado ou retorna false caso não exista o arquivo em pdf
        """
        caminho_arquivo = self.path_file_ciclo_txt.replace(".txt",".pdf")
        with open(caminho_arquivo, 'rb') as arquivo:
            nome_arquivo = os.path.basename(caminho_arquivo)
            arquivo_binario = arquivo.read()
            arquivo_base64 = base64.b64encode(arquivo_binario)
        # Verificar se o arquivo já está presente nos anexos
        if self._file_attachment_exist(nome_arquivo):
            return

        attachment = self.env['ir.attachment'].create({
            'name': nome_arquivo,
            'datas': arquivo_base64,
            'res_model': 'steril_supervisorio.ciclos',
            'res_id': self.id,
            'type': 'binary',
        })
       
       
        self.write({'message_main_attachment_id' : attachment.id } )         
        return attachment
    
    def _file_attachment_exist(self, file):
        """
        Verifica se o arquivo já está presente nos anexos do modelo.

        :param self: Objeto que invoca o método.
        :param file: Nome do arquivo a ser verificado.
        :return: True se o arquivo existe nos anexos, False caso contrário.
        """

        existente = self.env['ir.attachment'].search([
            ('name', '=', file),
            ('res_model', '=', 'steril_supervisorio.ciclos'),
            ('res_id', '=', self.id),
        ])

        return existente           
    def monta_tempos_ciclo(self, segmentos):
        
        str_dados_ciclo = '<table class="table table-sm table-condensed table-striped"><tbody>'
        #filtrando apenas as fases
        segmentos_filtered = [x for x in segmentos if x[1] in FASES]
       
        #calculando os tempos de cada fase
        tempos  = self.calcular_diferenca_tempo(segmentos_filtered)    
        soma_total = self.calcular_soma_tempo(tempos)
        
        return [tempos, soma_total]
    
    
    
    def passaram_24_horas(self,data_inicio):
        agora = fields.Datetime.now()
        diff = agora - data_inicio

        if diff > timedelta(hours=24):
            return True
        else:
            return False
        
    def _ler_arquivo_operador(self,file):
        with open(file, 'r') as arquivo:
            linhas = arquivo.readlines()
  
            for linha in linhas:
                colunas = re.split('\s+', linha)
                colunas = [valor for valor in colunas if valor]
               
                if len(colunas) > 1:
                    if colunas[0] == 'Operador:':

                        print(colunas)
                        apelido_operador = self.env['steril_supervisorio.ciclos.apelidos.operador'].search([('name','=',colunas[1])])
                        if len(apelido_operador):
                            operador = apelido_operador[0].operador
                            return operador.id
                        
    def atualiza_parametro_ultima_atualizacao(self):
        date = datetime.now(fuso_horario)
        _logger.info(f"Data de atual sem localize:{date}")
       
        
        
        date_str =  date.strftime('%Y-%m-%d %H:%M:%S %Z%z')
        existing_param = self.env['ir.config_parameter'].sudo().search([('key', '=', 'steril_supervisorio_ultima_atualizacao')])
        if existing_param:
            # Atualiza o valor existente
            existing_param.sudo().write({'value': date_str})
            
    def add_data_file_to_record(self):
        
        #lendo arquivo com os dados do ciclo
        
        dados,segmentos = self.ler_arquivo_dados(self.path_file_ciclo_txt)

        tempos,tempo_total = self.monta_tempos_ciclo(segmentos)
        tempos_integer = {}
        
        for tempo in tempos:
            h,m,s = tempos[tempo]
            tempos_integer[tempo] = h + m/60 + s/(60*60)
        is_finish,tempo_fim_ciclo = self.get_data_time_fim_de_ciclo(dados,segmentos)
       
        if(is_finish):
            
            self.write({
                'state':'finalizado',
                'data_fim': self.data_inicio + tempo_fim_ciclo
            })
        else:
            if self.passaram_24_horas(self.data_inicio):
                self.write({
                    'state':'incompleto',
                    'data_fim': self.data_inicio + tempo_fim_ciclo
                })
            else:
                self.write({
                    'state':'em_andamento'
                })

        estatisticas_finais = self._calcular_estatisticas_por_fase(dados)
        self.estatisticas_ciclo = json.dumps(estatisticas_finais)
        sequence = 1

        for fase_key in estatisticas_finais.keys():
            values = {
                    'sequence': sequence,
                    'name': fase_key,
                   
                    'ciclo': self.id,
                    'duration': tempos_integer.get(fase_key) ,
                    'pci_min': estatisticas_finais[fase_key]['valor_minimo1'],
                    'pci_max': estatisticas_finais[fase_key]['valor_maximo1'],
                    'pci_avg': estatisticas_finais[fase_key]['media1'],
                    'tci_min': estatisticas_finais[fase_key]['valor_minimo2'],
                    'tci_max': estatisticas_finais[fase_key]['valor_maximo2'],
                    'tci_avg': estatisticas_finais[fase_key]['media2'],
                }
            fase = self.env['steril_supervisorio.ciclos.fases.eto'].search(['&',('name','=', fase_key),('ciclo','=',self.id)])
            if len(fase) >  0:
                fase[0].write(values)
            else:
                fase = self.env['steril_supervisorio.ciclos.fases.eto'].create(values)
            sequence +=1
    
    
    def get_chart_image(self):
        
        num_ticks = 11  # Quantidade desejada de ticks no eixo y
        # if not self.path_file_ciclo_txt:
        #     return
        data_full = self.ler_arquivo_dados(self.path_file_ciclo_txt)
        dados,segmentos = data_full
        dados = [x for x in dados if not x[1].startswith(('PULSO','INJETANDO ETO'))] # retirando todos os dados que tem pulsos
        
        
        #sanitizando dados
        dados_sanitizados = [x for x in dados if len(x)>2]
        segmentos_sanitizados = [x for x in segmentos if not x[1].startswith( 'PULSO')]
        print(dados_sanitizados)
        print(segmentos_sanitizados)
        # Criar uma lista de cores para os segmentos
        cores = ['red', 'green', 'blue', 'yellow', 'orange', 'purple', 'pink', 'gray']
        

        # Extrair os valores de cada coluna
        amostra = range(0, len(dados_sanitizados) )
       
        pci = [float(item[1]) for item in dados_sanitizados]
        tci = [float(item[2]) for item in dados_sanitizados]
        
        fases = [item[1] for item in segmentos_sanitizados]
        indices_fases = obter_faixas_indices_fases(dados,fases)
        if(len(indices_fases) > 1):
            indices_fases.append( [indices_fases[-1][1],len(dados_sanitizados)-1 ])
        print(indices_fases)

        # Configurar o gráfico com subplots
        fig, ax1 = plt.subplots(figsize=(21, 9))
        
        ax1.plot(amostra, pci, label='PCI', color='red',drawstyle='steps-mid')
       
        ax1.set_xlabel('Amostra')
        ax1.set_ylabel('PCI', color='red')
        ax1.tick_params('y', colors='red')
        ax1.tick_params(axis='both',labelsize=12)

        # Plotar as áreas preenchidas para cada segmento
        for fase in indices_fases:
            ax1.fill_between(fase, -1,0, facecolor=cores[indices_fases.index(fase)], alpha=.2)

        # Criar os patches para a legenda
        list_patch = []
        for f in FASES:
            list_patch.append(plt.Rectangle((0, 0), 1, 1, fc=cores[FASES.index(f)], alpha=0.5))
       

        # Adicionar a legenda com os patches personalizados
        #ax1.legend([patch1, patch2], ['Área 1', 'Área 2'])
                
        ax2 = ax1.twinx()
        ax2.plot(amostra, tci, label='TCI', color='blue',drawstyle='steps-mid')
        ax2.set_ylabel('TCI', color='blue')
        ax2.tick_params('y', colors='blue')
        ax2.tick_params(axis='both',labelsize=12)
        
        # Definir escalas fixas para os eixos de PCI e TCI
        ax1.set_ylim(-1, 0)  # Define a escala fixa de 0 a 10 para o eixo de PCI
        ax2.set_ylim(0, 100)  # Define a escala fixa de 40 a 60 para o eixo de TCI
        # Aumentar a quantidade de ticks nos eixos y
      
        y_ticks_pci = np.linspace(-1, 0, num_ticks)
        y_ticks_tci = np.linspace(0, 100, num_ticks)

        ax1.set_yticks(y_ticks_pci)
        ax2.set_yticks(y_ticks_tci)
 
       

        # Combine as legendas de ambos os eixos
        handles, labels = ax1.get_legend_handles_labels()
        handles2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(list_patch,FASES,loc='best',fontsize=12)
        ax2.legend(handles + handles2, labels + labels2,loc='best',fontsize=12)
        ax1.grid(True, color='lightgray')
        ax2.grid(True, color='gray')
        plt.title('Gráfico P.C.I e T.C.I',fontsize=14)

              
        # Salvar o gráfico em um buffer
        buffer = io.BytesIO()
        plt.savefig(buffer, format='svg')
        buffer.seek(0)
        
        # Fechar a figura atual
        plt.close()
        # Retornar os dados da imagem
        self.grafico_ciclo = base64.b64encode(buffer.read())
        

    def action_ler_diretorio(self):
        self.ler_diretorio_ciclos("ETO03")

    def action_inicia_incubacao(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Inicia Incubação',
            'res_model': 'steril_supervisorio.incubation_wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {'default_ciclo': self.id,
                        'default_state_ciclo': self.state}
         }
        
    def action_leitura_incubacao(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Leitura de Incubação',
            'res_model': 'steril_supervisorio.incubation_wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
             'context': {'default_ciclo': self.id,
                        'default_state_ciclo': self.state}
         }
    def action_aprova_supervisor(self):
        self.write({
            'state': "concluido"

        })
    def action_reprova_supervisor(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Motivo Reprovação',
            'res_model': 'steril_supervisorio.incubation_wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
             'context': {'default_ciclo': self.id,
                        'default_state_ciclo': self.state,
                        'default_reprovado': True,
                        }
        }
       

class SupervisorioCiclosFasesETO(models.Model):
    _name = 'steril_supervisorio.ciclos.fases.eto'

    _description = 'Fases do Ciclos do supervisorio ETO'
    _order = 'sequence asc'

    sequence = fields.Integer(string="Sequence")
    name = fields.Char("Nome")
    ciclo = fields.Many2one(
        string='Ciclo',
        comodel_name='steril_supervisorio.ciclos',
        ondelete='cascade',
        required=True
        
    )
    
    duration = fields.Float(string='Duração(HH:mm)',help="Duração em horas  da fase")
    pci_max =  fields.Float(string='Pmax C.I.')
    pci_min =  fields.Float(string='Pmin C.I.')
    pci_avg =  fields.Float(string='Pmedia C.I.')
    tci_max =  fields.Float(string='Tmax C.I.')
    tci_min =  fields.Float(string='Tmin C.I.')
    tci_avg =  fields.Float(string='Tmedia C.I.')

class SupervisorioCiclosFasesVapor(models.Model):
    _name = 'steril_supervisorio.ciclos.fases.vapor'

    _description = 'Fases do Ciclos do supervisorio Vapor'
    _order = 'sequence asc'

    ciclo = fields.Many2one(
        string='Ciclo',
        comodel_name='steril_supervisorio.ciclos',
        ondelete='cascade',
        required=True
        
    )
    sequence = fields.Integer(string="Sequence")
    name = fields.Char("Nome")
    duration = fields.Float(string='Duração(HH:mm)',help="Duração em segundos da fase")
    pci_max =  fields.Float(string='Pmax C.I.')
    pci_min =  fields.Float(string='Pmin C.I.')
    pci_avg =  fields.Float(string='Pmedia C.I.')
    tci_max =  fields.Float(string='Tmax C.I.')
    tci_min =  fields.Float(string='Tmin C.I.')
    tci_avg =  fields.Float(string='Tmedia C.I.')


    
   
    