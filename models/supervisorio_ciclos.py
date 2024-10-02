from odoo import models, fields, api, _
import io
import base64
from datetime import  datetime,timedelta
from dateutil import  parser
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from plotly import tools
from collections import Counter
import plotly.graph_objects as go
import plotly.offline as pyo


from .fita_digital.dataobject_fita_digital import dataobject_fita_digital
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

def dict2tuple(list_dict):
    temp_tuple = ()
    for mdn in list_dict.keys():
        f_value = str2float(list_dict[mdn])       
        temp_tuple = temp_tuple + (f_value if f_value else list_dict[mdn],)
    return temp_tuple
def str2float(value_str):
    try:
        valor = float(value_str)
        return valor
    except ValueError:
        return False
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
    
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.user.company_id
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
    tipo_ciclo = fields.Char() # tipo do ciclo ex. Esterilização, Aeração, Leak-test, Tecidos ...
    
    def _get_default_cycle_model(self):
        return self.equipment.cycle_model.id
    cycle_model = fields.Many2one('steril_supervisorio.cycle_model',default =_get_default_cycle_model, )
    
    
    indicador_biologico = fields.Many2one(
        'steril_supervisorio.ciclos.indicador.biologico',
        string='Lote BI', 
        )
   
    massa_eto = fields.Float("Massa ETO",help="Insira a quantidade de ETO admitida em Kg",  tracking=True)
    massa_eto_gas = fields.Float("Massa gas ETO",help="Insira a quantidade de gas ETO admitida em Kg", tracking=True)
    concentracao_eto = fields.Float("Concentração ETO", compute="_compute_concentracao_eto",
     tracking=True
    )
    @api.onchange('massa_eto')
    def onchange_field(self):
        self._compute_concentracao_eto()
    
    @api.depends('massa_eto')
    def _compute_concentracao_eto(self):
        # 1.	Dividir a massa ETO (Kg) pelo volume da câmara (10.000 L):
        # Cálculo:           Massa ETO (Kg) = _________ = _________Kg/ L              
        #                                 Volume (L)                                                                                   
        # 2.	Multiplica o valor acima encontrado por 90% Gás ETO.
        # O valor encontrado é o resultado da concentração em Kg/L:
        # Cálculo:        ___________Kg/L  X  90% ETO = __________Kg/L  
        #                 Valor acima encontrado
        # 3.	Transformar Kg em mg (Multiplicar Massa (Kg) x 1000mg).
        #     Cálculo:      _____________ Kg/L  X  1000mg = ____________mg/L
        #                     Valor acima encontrado               Concentração ETO
        try:
            self.concentracao_eto = self.massa_eto*1000000/self.equipment.chamber_size
        except:
            self.concentracao_eto = 0.0
        
    marca_bi = fields.Char(
        related='indicador_biologico.marca',
        readonly=True,
        store=True)
    modelo_bi = fields.Char(
        related='indicador_biologico.modelo',
        
        readonly=True,
        store=True)
    
    resultado_bi = fields.Selection(selection = [('positivo','Positivo'),('negativo','Negativo')], tracking=True)
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

    document_count = fields.Char(compute='_compute_total_document_count',
                                 string='Document Count',
                                 help='Get the documents count')

    @api.depends('document_count')
    def _compute_total_document_count(self):
        """Get the document count on smart tab"""
        for record in self:
            record.document_count = self.env[
                'ir.attachment'].search_count(
                [('res_id', '=', record.id), ('res_model', '=', 'steril_supervisorio.ciclos')])

    # plotly_chart = fields.Text(
    #      string='Plotly Chart',
    #      compute='_compute_plotly_chart',
        
    #  )
    
    # def _compute_plotly_chart(self):
    #     for rec in self:
    #          fig = rec.mount_fig_chart_plotly()
    #          rec.plotly_chart = pyo.plot(fig, include_plotlyjs=False, output_type='div')
 
    _sql_constraints = [('codigo_ciclo_equipment_unique', 'unique(codigo_ciclo, equipment)',
                         'Codigo de ciclo duplicado '
                         'Não é permitido')]
    
    def _get_index_hora(self,data_raw,hora):
           
        for index, item in enumerate(data_raw):
            if hora in item:
                return index
        return None 

    def mount_fig_chart_matplot(self):
        #TODO melhorar os pontos de medida para pegar a hora correta e não os pontos
        pontos_medida = [[30,'15 min'],[225,'120 min'],[430,'235 min']]
        data = []
        do = self._get_dataobject_cycle()
        if not do:
            _logger.warning(f"Não foi possível montar o gráfico ciclo {self.name}, data_object retornou False")
            return False
        data_raw = self._get_cycle_data()
        for d in data_raw:
            data.append(dict2tuple(d))
        vals=[]
      
        _logger.debug(data)
        
        for index in range(len(self.cycle_model.magnitude_data)):
            _logger.debug(f"Index:{index}")

            vals.append([item[index] for item in data]  ) 
   
        fig, ax1 = plt.subplots(figsize=(16, 9))

        color = 'tab:red'
        ax1.set_xlabel('Hora')
        ax1.set_ylabel('Pressão (Bar)', color=color)
        ax1.plot(vals[0], vals[1], color=color,label="Pressão")
        _logger.info(f"Aqui os valores de pressão {vals[1]}")
        ax1.tick_params(axis='y', labelcolor=color)
        ax1.tick_params(axis='x',labelrotation=90.0,labelsize=8)

        ax2 = ax1.twinx()
        color = 'tab:blue'
        ax2.set_ylabel('Temperatura (ºC) ', color=color)
        ax2.plot(vals[0], vals[2], color=color,label="Temperatura")
        ax2.tick_params( labelcolor=color,)
        
        ax2.set_ylim(0, 100)

        if len(vals)> 3:
            color = 'tab:green'
            #ax3 = ax2.twinx()
            ax2.plot(vals[0], vals[3], color=color,label="Umidade",)
            color = 'tab:gray'
            ax2.tick_params(axis='y', labelcolor=color,labelright=True)
            ax2.set_ylabel('Umidade % / Temperatura ºC', color=color)
            ax2.set_ylim(0, 100)
       
        #ax3.tick_params(axis='y', labelcolor=color)
        ax1.grid(True)

        #handles label legend
        handles, labels = ax1.get_legend_handles_labels()
        handles_2, labels_2= ax2.get_legend_handles_labels()
        #handle_3  = [plt.Circle((0, 0), 1, color='blue', alpha=0.2)]
        #handle_3  =   [Patch(facecolor='blue', edgecolor='blue', marker='o',label='5 min')]
        #labels_3 = ["UR% 5min"]
        ax2.grid(True)
        #ax3.grid(False)


        plt.xticks(rotation=90)
        
        fig.tight_layout()

        data_effective_sterilization = do.data_threshold(data = do.extract_data_sterilization(event_start='ESTERILIZACAO', envent_stop='LAVAGEM'),threshold_value= -0.180)
        #TODO FAZER PARA LER O VALOR DE UMIDADE COM 5 MIN, 120 MIN e 245 MIN
        # Adicionando pontos marcados
        if len(data_effective_sterilization) > 0:
            indice_start_sterilization = self._get_index_hora(data,data_effective_sterilization[0]['Hora'])
        else:
            indice_start_sterilization = 0
        _logger.debug(f"INDICE_START_STERILIZATION = {indice_start_sterilization}")
        pontos_marcar = []
        if indice_start_sterilization:
            # pegando pontos de medida na fita de impressao
            for pm in pontos_medida:
                pontos_marcar.append(data[indice_start_sterilization+pm[0]] if (indice_start_sterilization+pm[0]) < len(data) else [])
                _logger.debug(f"PONTOS MEDIDA: {pm}")
            _logger.debug(f"ponstos array: {pontos_marcar}")
            for index, pmrc in enumerate(pontos_marcar):
                if len(pmrc) > 0:
                    ax2.plot(pmrc[0], pmrc[3], 'o')  # 'o' representa círculos pretos ocos
                    ax2.text(pmrc[0], pmrc[3]+2, f"{pontos_medida[index][1]} \n {pmrc[3]}%", ha='center')

            # Adicionando a zona de esterilização
            #TODO fazer o envent_start e envent_stop, theshold = pegando da configuração do modelo de ciclo
            start_time = data_effective_sterilization[0]['Hora']
            end_time = data_effective_sterilization[-1]['Hora']
            zone_x = [start_time, end_time]  # Intervalo de x para a zona
            zone_y_lower = [0, 0]  # Limite inferior da zona para cada ponto x
            zone_y_upper = [100, 100]  # Limite superior da zona para cada ponto x
            ax2.fill_between(zone_x, zone_y_lower, zone_y_upper, color='yellow', alpha=0.2, label='Esterilização',)
        #ax2.text(zone_x[0], max(zone_y_upper) - 30, 'ESTERILIZAÇÃO', ha='center')
        x_ticks = np.linspace(start=0,stop=len(vals[0])-1,num=121)
        y_ticks = np.linspace(start=-0.9,stop=0.1,num=21)
        y_ticks_2 = np.linspace(start=0,stop=100,num=21)
        ax1.set_xticks(x_ticks)
        ax1.set_yticks(y_ticks)
        ax2.set_yticks(y_ticks_2)
        
        ax2.legend(handles=handles+handles_2+[plt.Rectangle((0, 0), 1, 1, fc='yellow', alpha=0.2)],labels = labels + labels_2+["ESTERILIZAÇÃO"] , loc='best')
        
       #ax1.legend(,FASES,loc='best',fontsize=12)
        return fig
    
    def mount_fig_chart_plotly(self):
        data_raw = self._get_cycle_data()
        data = []
        for d in data_raw:
            data.append(( d['Hora'], float(d['PCI']), float(d['TCI']), float(d['UR'])) )

        
        # Separar os dados em listas
        tempos = [item[0] for item in data]
        valores1 = [item[1] for item in data]
        valores2 = [item[2] for item in data]
        valores3 = [item[3] for item in data]

        # Criar os traces
        trace1 = go.Scatter(x=tempos, y=valores1, mode='lines', name='Pressão (bar)', yaxis="y1")
        trace2 = go.Scatter(x=tempos, y=valores2, mode='lines', name='Temperatura (ºC)', yaxis="y2")
        trace3 = go.Scatter(x=tempos, y=valores3, mode='lines', name='Umidade (UR%)', yaxis="y2")

        # Criar o layout
        layout = go.Layout(
            title='Gráfico do Ciclo ' + self.codigo_ciclo,
            xaxis=dict(title='Hora'),
            yaxis=dict(title='Pressão(Bar)', side='left', domain=[0, 1] ),
            yaxis2=dict(title='ºC / UR% ', side='right', overlaying='y',domain=[0, 1]),
            autosize=True,
            legend=dict(title='Dados'),
            
            width=1024,  # Largura da figura em pixels
            height=800  # Altura da figura em pixels
        )
        # Criar a figura
        umidade_5 = ['21:58:47',55]
        umidade_120 = ['23:53:33',64]
        umidade_235 = ['01:20:52',64]
        pontos_marcar = [umidade_5,umidade_120,umidade_235]

        # Limites da zona a ser marcada
        zone_x = ['21:32:37', '01:32:45']  # Intervalo de x para a zona
        zone_y_lower = [0, 0]  # Limite inferior da zona para cada ponto x
        zone_y_upper = [100, 100]  # Limite superior da zona para cada ponto x
            
        fig = go.Figure( layout=layout)
        fig.add_trace(trace1)
        fig.add_trace(trace2)
        fig.add_trace(trace3)
        for p in pontos_marcar:

            fig.add_trace(go.Scatter(x=[p[0]],
                                    y=[p[1]], mode='markers', 
                                    
                                    yaxis="y2",
                                    
                                    marker=dict(color='black', size=10,symbol='circle-open'),
                                    textposition='top center', showlegend=False,
                                    ))
            fig.add_trace(go.Scatter(x=[p[0]], y=[p[1]+2],yaxis="y2",textposition='top center', mode='text', text=[f"({p[0]},{p[1]}%)"], showlegend=False))
        # Adicionando a zona de esterilização
        fig.add_trace(go.Scatter(x=zone_x + zone_x[::-1],  # Criando uma linha fechada conectando os pontos
                        y=zone_y_lower + zone_y_upper[::-1],  # Adicionando os limites inferior e superior
                        fill='toself',  # Preenchendo a área entre as linhas
                        fillcolor='rgba(255, 255, 0, 0.2)',  # Cor do preenchimento (verde com transparência)
                        line=dict(color='rgba(0, 0, 0, 0)'),  # Escondendo a linha de contorno
                        name='Esterilização',
                        yaxis="y2",text="ESTERILIZAÇÃO"
                        
                        ))
        
        return fig
    
    def _get_dataobject_cycle(self,path_file_ciclo_txt = None, equipment=0):
                
        do_cycle = dataobject_fita_digital()
        _logger.debug(f"DataObject_fita: {do_cycle}")
        if path_file_ciclo_txt:
            do_cycle.set_filename(path_file_ciclo_txt if path_file_ciclo_txt else self.path_file_ciclo_txt)
        else:          
            if self.path_file_ciclo_txt:
                do_cycle.set_filename(self.path_file_ciclo_txt)
            else:
                raise ValidationError("Nenhum path_file_ciclo_txt encontrado")
        # procurando modelo do ciclo
        _logger.debug("PROCURANDO MODELO DO CICLO")
        if self.cycle_model:
            _logger.debug(f"Já cadastrado no ciclo {self.name} o cycle model {self.cycle_model.name}")
            _logger.debug(f"Dados do cabeçalho {self.cycle_model.header_data}")
            _logger.debug(f"Colunas de dados: {self.cycle_model.magnitude_data}")
            columns_data = self.cycle_model.magnitude_data
            header_data = self.cycle_model.header_data
            
        else:
            _logger.debug(f"Não encontrado cycle model no ciclo {self.name}, procurando o modelo de ciclo padrão do equipamento")
            if equipment:
                _logger.debug(f"Procurando cycle model no equipamento {equipment.name}")
                columns_data = equipment.cycle_model.magnitude_data
                header_data = equipment.cycle_model.header_data
                if not equipment.cycle_model:
                    raise ValidationError(f"O Equipamento {equipment.name} não tem um modelo de um ciclo padrão")
                _logger.debug(f"Modelo encontrado {equipment.cycle_model.name}")
            else:
                _logger.debug(f"No ciclo {self.name} não foi encontrado equipamento para pegar o modelo de um ciclo")
                return False
        #_logger.debug(columns_data)
        # Configura a quantidade de colunas da fita e as grandezas relacionadas
        columns_names =[]
        for col in columns_data:
            columns_names.append(col.name)
        header_names = []
        for header in header_data:
            header_names.append(header.name)
        _logger.debug(f"COLUMN NAMES: {columns_names}")
        _logger.debug(f"HEADER NAMES: {header_names}")
        do_cycle.set_model_columns_name_data(columns_names=columns_names)
        #do_cycle.set_model_columns_data(qtd_columns=len(columns_data),columns_names=columns_names) 
        # Configura a todos os dados que estao no cabecalho da fita
        do_cycle.set_header_items(items=header_names) #items do cabecalho
        #quantidade de linhas que tem o cabecalho
        do_cycle.set_header_lines(25) 
        return do_cycle

    def _get_cycle_data(self):
        dataobject_cycle = self._get_dataobject_cycle()
        if not dataobject_cycle:
            _logger.warning(f"Não foi possível pegar os dados do ciclo {self.name}, data_object retornou False")
            return []
        data = dataobject_cycle.extract_cycle_data()
        return data
    
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
              
        
        _logger.debug(f"Ultima Atualização: {data_ultima_atualizacao}")

       
        timestamp_modificacao = os.path.getmtime(path_arquivo)
        data_modificacao = datetime.fromtimestamp(timestamp_modificacao, tz=fuso_horario)

        
        # _logger.info(f"Data original de modificação do arquivo {path_arquivo}: {data_modificacao}")
        # data_modificacao = fuso_horario.localize(data_ultima_atualizacao).astimezone(pytz.utc).replace(tzinfo=None)                 
        _logger.debug(f"Data modificação do arquivo {path_arquivo}: {data_modificacao}")
        if data_modificacao >= (data_ultima_atualizacao - timedelta(minutes=10)):
            _logger.debug(f"A data {data_modificacao} é maior ou igual  {data_ultima_atualizacao}")
            return True
        else:
            _logger.debug(f"A data {data_modificacao} é menor que  {data_ultima_atualizacao}")
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
        dir_name_ciclos = self.env['ir.config_parameter'].get_param('steril_supervisorio_ultima_atualizacao')
        if not dir_name_ciclos:
            raise ValidationError("Nenhum steril_supervisorio_dir_name_ciclos encontrado nos paramentros da empresa.")
        diretorio = f"/var/lib/odoo/filestore/{dbname}/{dir_name_ciclos}/{equipment_alias}/" 
        equipment = self.env['engc.equipment'].search([('apelido','=like',equipment_alias )])
        _logger.debug(f"O equipamento de apelido {equipment_alias}  agora é: {equipment}")
        #TODO modificar para ver se só os diretórios que tiveram atualização estejam na lista
        
        for nome_pasta in os.listdir(diretorio):
            caminho_pasta = os.path.join(diretorio, nome_pasta)
            _logger.debug(f"Lendo diretorio: {caminho_pasta}")
           
          
            if os.path.isdir(caminho_pasta):

                codigo_carga = nome_pasta
                lista_de_arquivos = os.listdir(caminho_pasta)
                _logger.debug(f"Lista de arquivo do diretorio: {lista_de_arquivos}")

                # filtrando apenas os arquivos tipo txt
                lista_de_arquivos_txt = [arquivo for arquivo in lista_de_arquivos if arquivo.endswith('txt')]
                _logger.debug(f"Lista de arquivos encontrada: {lista_de_arquivos_txt}") 
                for arquivo in lista_de_arquivos_txt:  
                    path_full_file = caminho_pasta+'/'+arquivo
                   
                    if self._arquivo_modificado_recentemente(path_full_file):
                        arquivo_partes = arquivo.split('_')
                        data_hora_inicio_str = arquivo_partes[1] + ' ' + arquivo_partes[2].replace('.txt', '')
                        codigo_ciclo = arquivo.replace('.txt','')
                        _logger.debug(f"codigo_ciclo: {codigo_ciclo}")
                        # Converter a data e hora para o formato datetime
                        data_inicio = self.convert_date_str_file_to_datetime(data_hora_inicio_str)
                        _logger.debug(f"data_inicio: {data_inicio}")
                        # Verificar se o código de ciclo já existe no modelo
                        ciclo_existente = self.env['steril_supervisorio.ciclos'].search([('codigo_ciclo', '=', codigo_ciclo)])
                        if ciclo_existente:
                            _logger.debug(f"Ciclo {ciclo_existente.name} já existente no banco de dados")
                        else:
                            _logger.debug(f'Nenhum ciclo no banco cadastrado')
                        if len(ciclo_existente) < 1: #não existe ciclo
                            _logger.debug(f"Lendo header do arquivo: {path_full_file}")
                            header = self.get_header_fita(path_full_file,equipment)
                            
                            operador_id = self._ler_arquivo_operador(header)
                            _logger.debug(f'Operador:{operador_id}')
                           
                           
                            ciclo = self.env['steril_supervisorio.ciclos'].create({
                                'name': codigo_carga,
                                'codigo_ciclo': codigo_ciclo,
                                'data_inicio': data_inicio,
                                'operator': operador_id,
                                'company_id': equipment.company_id.id,
                                'equipment': equipment.id or None,
                                'path_file_ciclo_txt' : path_full_file,
                                'cycle_model': equipment.cycle_model.id
                                }
                            )
                            ciclo.flush()
                            _logger.debug(f"Ciclo {ciclo.name} criado!")

                        else:
                            ciclo_existente.write({'path_file_ciclo_txt' : path_full_file})
                            ciclo=ciclo_existente
                        
                      
                        #if(ciclo and ciclo.state not in ['finalizado']):
                        if(ciclo and ciclo.state in ['iniciado','em_andamento', 'incompleto']):
                           #_logger.debug("Adicionando estatisticass")
                           _logger.debug(f"Dados cabeçalho do ciclo: {ciclo.cycle_model},{ciclo.equipment.name}")
                           _logger.debug(f"Adicionando imagem do grafico do ciclo {ciclo.name}")

                           ciclo.set_chart_image()
                           _logger.debug(f"Adicionando anexo em pdf  do ciclo {ciclo.name}")
                           ciclo.adicionar_anexo_pdf()
                           _logger.debug(f"Atualizando dados ao banco  do ciclo {ciclo.name}")
                           ciclo.add_data_file_to_record()
                           ciclo.flush()
                           self.env.cr.commit()

        return True   
    def set_statistics_cycle(self):
        self._calcular_estatisticas_por_fase()

    def get_header_fita(self, path_file_name,equipment):
        do = self._get_dataobject_cycle(path_file_ciclo_txt=path_file_name, equipment = equipment)
        if not do:
            _logger.warning(f"Não foi possível pegar o cabecalho da fita do ciclo {self.name}, data_object retornou False")
            return
        data = do.extract_header_cycle_sterilization()
        
        _logger.debug(data)
        return data



    def _calcular_estatisticas_por_tempo_esterilizacao(self):
        do = self._get_dataobject_cycle()
        
        
      



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
                        'vals[1]': [],
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
                contador_valores1 = Counter(valores1)
                
                contador_valores2 = Counter(valores2)
                
                valor_maior_frequencia1 = contador_valores1.most_common(1)[0][0]
                valor_maior_frequencia2 = contador_valores2.most_common(1)[0][0]

                estatisticas_finais[fase] = {
                    'valor_minimo1': min(valores1 or []),
                    'valor_maximo1': max(valores1),
                    'media1': sum(valores1) / len(valores1),
                    'valor_minimo2': min(valores2 or []),
                    'valor_maximo2': max(valores2),
                    'media2': sum(valores2) / len(valores2),
                    'valor_maior_frequencia1': valor_maior_frequencia1,
                    'valor_maior_frequencia2': valor_maior_frequencia2,
                }

        return estatisticas_finais
 
    def _calcular_tempo_decorrido(self,lista):
        do = self._get_cycle_data()
        if not lista:
            return None
        diferenca_tempo = do.compute_elapsed_time(lista[0][0],lista[-1][0])
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
  
    # def ler_arquivo_dados(self,file):
    #     """
    #     Lê um arquivo de dados e extrai as informações.

    #     :param file: Caminho do arquivo a ser lido.
    #     :type file: str
    #     :return: Uma lista contendo os dados extraídos do arquivo e uma lista de segmentos.
    #     :rtype: list

    #     Exemplo de uso:
    #         arquivo = '/caminho/do/arquivo.txt'
    #         dados, segmentos = self.ler_arquivo_dados(arquivo)
    #         print(dados)
    #         print(segmentos)
    #     """

    #     dados = []
    #     segmentos = []
    #     nome_arquivo = file
    #     with open(nome_arquivo, 'r') as arquivo:
    #         linhas = arquivo.readlines()
  
    #         for linha in linhas:
    #             #colunas = linha.strip().split('\s+')
    #             colunas = re.split('\s+', linha)
    #             colunas = [valor for valor in colunas if valor]
                
               
    #             if len(colunas) > 1:
    #                 if (self.verificar_conversao_tempo(colunas[0])):
    #                     if(self.verificar_conversao_float(colunas[1])):
    #                         dados.append(colunas)
    #                     else:
    #                         dados.append([colunas[0],' '.join(colunas[1:])])
    #                         segmentos.append([colunas[0],' '.join(colunas[1:])])
    #     _logger.debug([dados,segmentos])
    #     return [dados,segmentos]
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

        #lendo configuração das fases
        phases = self.cycle_model.phase_data
        _logger.debug(f"As fases do modelo:{phases}")

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
        #_logger.debug([dados,segmentos])
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
        try:
            with open(caminho_arquivo, 'rb') as arquivo:
                nome_arquivo = os.path.basename(caminho_arquivo)
                arquivo_binario = arquivo.read()
                arquivo_base64 = base64.b64encode(arquivo_binario)
        except:
            _logger.info(f"Não foi possivel achar arquivo {caminho_arquivo}")
            return
        # Verificar se o arquivo já está presente nos anexos
        
        existente = self._file_attachment_exist( nome_arquivo )
        if existente:
            if len(existente.datas) != len(arquivo_base64):
                _logger.info("Arquivo é diferente, atualizando")
                existente.write({'datas': arquivo_base64})
                return existente
            else:
                _logger.info("Arquivo é igual, não faz nada")
                return existente

        attachment = self.env['ir.attachment'].create({
            'name': nome_arquivo,
            'datas': arquivo_base64,
            'res_model': 'steril_supervisorio.ciclos',
            'res_id': self.id,
            'type': 'binary',
        })
       
       
        self.write({'message_main_attachment_id' : attachment.id } )         
        return attachment
    
    def _file_attachment_exist(self, file_name):
        """
        Verifica se o arquivo já está presente nos anexos do modelo.

        :param self: Objeto que invoca o método.
        :param file: Nome do arquivo a ser verificado.
        :return: True se o arquivo existe nos anexos, False caso contrário.
        """

        existente = self.env['ir.attachment'].search([
            ('name', '=', file_name),
            ('res_model', '=', 'steril_supervisorio.ciclos'),
            ('res_id', '=', self.id),
        ])

        if existente:
            return existente
        else:
            return False

            
    def monta_tempos_ciclo(self, segmentos):
        
        str_dados_ciclo = '<table class="table table-sm table-condensed table-striped"><tbody>'
        #filtrando apenas as fases
        segmentos_filtered = [x for x in segmentos if x[1] in FASES]
       
        #calculando os tempos de cada fase
        tempos  = self.calcular_diferenca_tempo(segmentos_filtered)    
        soma_total = self.calcular_soma_tempo(tempos)
        
        return [tempos, soma_total]
    
    
    
    def identifica_ciclo_incompleto(self,data_inicio):
        agora = fields.Datetime.now()
        diff = agora - data_inicio

        if diff > timedelta(hours=8):
            return True
        else:
            return False
        
    def _ler_arquivo_operador(self,header):
        
        _logger.debug(f"HEADER: {header}")
        operador = header['Operador'] 
        apelido_operador = self.env['steril_supervisorio.ciclos.apelidos.operador'].search([('name','=',operador)])
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
        
        value = {}
        #lendo arquivo com os dados do ciclo
        _logger.debug(f"Entrando na add_data_file_to_record")

        # iniciando data object leitura da fita
        do = self._get_dataobject_cycle()
        if not do:
            _logger.warning(f"Não foi possível encontrar no ciclo {self.name} o data_object retornou False")
            return 0
        data_cycle = do.extract_cycle_data()
        if len(data_cycle) < 1:
            _logger.warning(f"Nenhum dado foi encontrado no ciclo {self.name}")
            return 0
        # pegando as configuraç~eos de fase
        
        phases = self.cycle_model.phase_data
        phases_name = phases.mapped('name') #nome da fase que sera mostrada
        phases_regex = phases.mapped('regex_tape') #regex de procura na fita
        _logger.debug(f"Fases do Ciclo: {phases_regex}")
        _logger.debug(f"Qtd fases: {len(phases_regex)}")
        for index, ph in enumerate(phases_regex):
           
            _logger.debug(f"Index: {index}")
            if index >= (len(phases_regex)-1):
                break
            start_event = ph
            end_event = phases_regex[index+1]
            data_phase = do.extract_data_between_events(start_event=start_event, end_event=end_event)
            if not data_phase:
                _logger.warning(f"Nao encontrada dados entre os eventos {start_event} e {end_event}")
                
            statistics = do.calculate_metrics(data_phase)
            value.update({'sequence': index,
                    'name': phases_name[index],
                    'ciclo': self.id,
                    'duration': self.converter_para_float_time(statistics['duration']) ,})
            value.update({
     
                    'pci_min': statistics['PCI']['min'] if statistics.get('PCI') else None,
                    'pci_max': statistics['PCI']['max'] if statistics.get('PCI') else None,
                    'pci_avg': statistics['PCI']['avg'] if statistics.get('PCI') else None,
                    
                    'tci_min': statistics['TCI']['min'] if statistics.get('TCI') else None,
                    'tci_max': statistics['TCI']['max'] if statistics.get('TCI') else None,
                    'tci_avg': statistics['TCI']['avg'] if statistics.get('TCI') else None,
                    'ur_min': statistics['UR']['min'] if statistics.get('UR') else None,
                    'ur_max': statistics['UR']['max'] if statistics.get('UR') else None ,
                    'ur_avg': statistics['UR']['avg'] if statistics.get('UR') else None,
               
            })
            
            fase = self.env['steril_supervisorio.ciclos.fases.eto'].search(['&',('name','=', phases_name[index]),('ciclo','=',self.id)])
            if len(fase) >  0:
                fase[0].write(value)
            else:
                fase = self.env['steril_supervisorio.ciclos.fases.eto'].create(value)
            # ATUALIZANDO STATUS DO CICLO
        #data_teste = do.extract_data_between_events(start_event=phases_regex[-2], end_event=phases_regex[-1])

        if not phases_regex:
            return 0
        #se ciclo finalizado
        start_cycle_time = data_cycle[0]['Hora']
        end_cycle_time = data_cycle[-1]['Hora']
        finished_cycle_time = do.search_phase_time(phases_regex[-1])
        
        if finished_cycle_time:
            time_cycle_duration = do.compute_elapsed_time(start_time=start_cycle_time,end_time = finished_cycle_time)
            self.write({
                'state':'finalizado',
                'data_fim': self.data_inicio + time_cycle_duration
            })
        else:
            if self.identifica_ciclo_incompleto(self.data_inicio):
                time_cycle_duration = do.compute_elapsed_time(start_time=start_cycle_time,end_time = end_cycle_time)
                self.write({
                    'state':'incompleto',
                    'data_fim': self.data_inicio + time_cycle_duration
                })
            else:
                self.write({
                    'state':'em_andamento'
                })

        return 0
        is_finish,tempo_fim_ciclo = self.get_data_time_fim_de_ciclo(dados,segmentos)
        _logger.debug(f"Ciclo finalizado: {is_finish}, tempo de fim de ciclo {tempo_fim_ciclo}")
        if(is_finish):
            pass
           
        else:
            if self.identifica_ciclo_incompleto(self.data_inicio):
                self.write({
                    'state':'incompleto',
                    'data_fim': self.data_inicio + tempo_fim_ciclo
                })
            else:
                self.write({
                    'state':'em_andamento'
                })

           
        return 0

        values = {
                    'sequence': sequence,
                    'name': fase_key,
                   
                    'ciclo': self.id,
                    'duration': tempos_integer.get(fase_key) ,
                    'pci_min': estatisticas_finais[fase_key]['PCI']['min'],
                    'pci_max': estatisticas_finais[fase_key]['PCI']['max'],
                    'pci_avg': estatisticas_finais[fase_key]['PCI']['avg'],
                    
                    'tci_min': estatisticas_finais[fase_key]['TCI']['min'],
                    'tci_max': estatisticas_finais[fase_key]['TCI']['max'],
                    'tci_avg': estatisticas_finais[fase_key]['TCI']['avg'],
                    'ur_min': estatisticas_finais[fase_key]['UR']['min'],
                    'ur_max': estatisticas_finais[fase_key]['UR']['max'],
                    'ur_avg': estatisticas_finais[fase_key]['UR']['avg'],
                    
                }

        data = do.extract_data_between_events(start_event='LAVAGEM',end_event='AERACAO')
        #dados,segmentos = self.ler_arquivo_dados(self.path_file_ciclo_txt)

        if len(data) == 0:
            _logger.debug(f"nenhum dado lido, saindo")
            return

        tempos,tempo_total = self.monta_tempos_ciclo(segmentos)
        tempos_integer = {}
        
        for tempo in tempos:
            h,m,s = tempos[tempo]
            tempos_integer[tempo] = h + m/60 + s/(60*60)
        is_finish,tempo_fim_ciclo = self.get_data_time_fim_de_ciclo(dados,segmentos)
        _logger.debug(f"Ciclo finalizado: {is_finish}, tempo de fim de ciclo {tempo_fim_ciclo}")
        if(is_finish):
            
            self.write({
                'state':'finalizado',
                'data_fim': self.data_inicio + tempo_fim_ciclo
            })
        else:
            if self.identifica_ciclo_incompleto(self.data_inicio):
                self.write({
                    'state':'incompleto',
                    'data_fim': self.data_inicio + tempo_fim_ciclo
                })
            else:
                self.write({
                    'state':'em_andamento'
                })

       
        estatisticas_finais = self._calcular_estatisticas_por_tempo_esterilizacao()
        self.estatisticas_ciclo = json.dumps(estatisticas_finais)
        sequence = 1

        for fase_key in estatisticas_finais.keys():
            values = {
                    'sequence': sequence,
                    'name': fase_key,
                   
                    'ciclo': self.id,
                    'duration': tempos_integer.get(fase_key) ,
                    'pci_min': estatisticas_finais[fase_key]['PCI']['min'],
                    'pci_max': estatisticas_finais[fase_key]['PCI']['max'],
                    'pci_avg': estatisticas_finais[fase_key]['PCI']['avg'],
                    
                    'tci_min': estatisticas_finais[fase_key]['TCI']['min'],
                    'tci_max': estatisticas_finais[fase_key]['TCI']['max'],
                    'tci_avg': estatisticas_finais[fase_key]['TCI']['avg'],
                    'ur_min': estatisticas_finais[fase_key]['UR']['min'],
                    'ur_max': estatisticas_finais[fase_key]['UR']['max'],
                    'ur_avg': estatisticas_finais[fase_key]['UR']['avg'],
                    
                }
            

    # def add_data_file_to_record(self):
        
    #     #lendo arquivo com os dados do ciclo
    #     _logger.debug(f"Entrando na add_data_file_to_record")
        
    #     dados,segmentos = self.ler_arquivo_dados(self.path_file_ciclo_txt)
    #     if len(dados) == 0:
    #         _logger.debug(f"nenhum dado lido, saindo")
    #         return

    #     tempos,tempo_total = self.monta_tempos_ciclo(segmentos)
    #     tempos_integer = {}
        
    #     for tempo in tempos:
    #         h,m,s = tempos[tempo]
    #         tempos_integer[tempo] = h + m/60 + s/(60*60)
    #     is_finish,tempo_fim_ciclo = self.get_data_time_fim_de_ciclo(dados,segmentos)
    #     _logger.debug(f"Ciclo finalizado: {is_finish}, tempo de fim de ciclo {tempo_fim_ciclo}")
    #     if(is_finish):
            
    #         self.write({
    #             'state':'finalizado',
    #             'data_fim': self.data_inicio + tempo_fim_ciclo
    #         })
    #     else:
    #         if self.identifica_ciclo_incompleto(self.data_inicio):
    #             self.write({
    #                 'state':'incompleto',
    #                 'data_fim': self.data_inicio + tempo_fim_ciclo
    #             })
    #         else:
    #             self.write({
    #                 'state':'em_andamento'
    #             })

    #     #estatisticas_finais = self._calcular_estatisticas_por_fase(dados)
    #     #estatisticas_finais = self._calcular_estatisticas_por_fase(dados)
    #     estatisticas_finais = self._calcular_estatisticas_por_tempo_esterilizacao()
    #     self.estatisticas_ciclo = json.dumps(estatisticas_finais)
    #     sequence = 1

    #     for fase_key in estatisticas_finais.keys():
    #         values = {
    #                 'sequence': sequence,
    #                 'name': fase_key,
                   
    #                 'ciclo': self.id,
    #                 'duration': tempos_integer.get(fase_key) ,
    #                 'pci_min': estatisticas_finais[fase_key]['PCI']['min'],
    #                 'pci_max': estatisticas_finais[fase_key]['PCI']['max'],
    #                 'pci_avg': estatisticas_finais[fase_key]['PCI']['avg'],
                    
    #                 'tci_min': estatisticas_finais[fase_key]['TCI']['min'],
    #                 'tci_max': estatisticas_finais[fase_key]['TCI']['max'],
    #                 'tci_avg': estatisticas_finais[fase_key]['TCI']['avg'],
    #                 'ur_min': estatisticas_finais[fase_key]['UR']['min'],
    #                 'ur_max': estatisticas_finais[fase_key]['UR']['max'],
    #                 'ur_avg': estatisticas_finais[fase_key]['UR']['avg'],
                    
    #             }
    #         fase = self.env['steril_supervisorio.ciclos.fases.eto'].search(['&',('name','=', fase_key),('ciclo','=',self.id)])
    #         if len(fase) >  0:
    #             fase[0].write(values)
    #         else:
    #             fase = self.env['steril_supervisorio.ciclos.fases.eto'].create(values)
    #         sequence +=1
            
    def set_chart_image(self):
        for rec in self:
            _logger.debug("Gerando grafico...")
            fig = rec.mount_fig_chart_matplot()
            if not fig:
                _logger.debug("Não foi possível salvar imagem do gráfico, erro na montagem com os dados da fita!")
                return False
            _logger.debug("Grafico gerado!")
           
            # # Convertendo a imagem PNG em dados binários
            buffer = io.BytesIO()
            fig.savefig(buffer, format='png')
            buffer.seek(0) 
            #pyo.plot_mpl()
            _logger.debug("Transformado em figura")
           

            _logger.debug("Colocando no banco de dados")
            rec.grafico_ciclo = base64.b64encode(buffer.read())

    
    # def get_chart_image(self):
        
    #     num_ticks = 11  # Quantidade desejada de ticks no eixo y
    #     # if not self.path_file_ciclo_txt:
    #     #     return
    #     data_full = self.ler_arquivo_dados(self.path_file_ciclo_txt)
    #     dados,segmentos = data_full
    #     dados = [x for x in dados if not x[1].startswith(('PULSO','INJETANDO ETO'))] # retirando todos os dados que tem pulsos
        
        
    #     #sanitizando dados
    #     dados_sanitizados = [x for x in dados if len(x)>2]
    #     segmentos_sanitizados = [x for x in segmentos if not x[1].startswith( 'PULSO')]
        
        
    #     # Criar uma lista de cores para os segmentos
    #     cores = ['red', 'green', 'blue', 'yellow', 'orange', 'purple', 'pink', 'gray']
        

    #     # Extrair os valores de cada coluna
    #     amostra = range(0, len(dados_sanitizados) )
       
    #     pci = [float(item[1]) for item in dados_sanitizados]
    #     tci = [float(item[2]) for item in dados_sanitizados]

    #     # data = [{'y': pci},{'y': tci}]
    #     # self.plotly_chart = plotly.offline.plot(data,
    #     #                                    include_plotlyjs=False,
    #     #                                    output_type='div')
        
    #     fases = [item[1] for item in segmentos_sanitizados]
    #     indices_fases = obter_faixas_indices_fases(dados,fases)
    #     if(len(indices_fases) > 1):
    #         indices_fases.append( [indices_fases[-1][1],len(dados_sanitizados)-1 ])
       

    #     # Configurar o gráfico com subplots
    #     fig, ax1 = plt.subplots(figsize=(21, 9))
        
    #     ax1.plot(amostra, pci, label='PCI', color='red',drawstyle='steps-mid')
       
    #     ax1.set_xlabel('Amostra')
    #     ax1.set_ylabel('PCI', color='red')
    #     ax1.tick_params('y', colors='red')
    #     ax1.tick_params(axis='both',labelsize=12)

    #     # Plotar as áreas preenchidas para cada segmento
    #     for fase in indices_fases:
    #         ax1.fill_between(fase, -1,0, facecolor=cores[indices_fases.index(fase)], alpha=.2)

    #     # Criar os patches para a legenda
    #     list_patch = []
    #     for f in FASES:
    #         list_patch.append(plt.Rectangle((0, 0), 1, 1, fc=cores[FASES.index(f)], alpha=0.5))
       

    #     # Adicionar a legenda com os patches personalizados
    #     #ax1.legend([patch1, patch2], ['Área 1', 'Área 2'])
                
    #     ax2 = ax1.twinx()
    #     ax2.plot(amostra, tci, label='TCI', color='blue',drawstyle='steps-mid')
    #     ax2.set_ylabel('TCI', color='blue')
    #     ax2.tick_params('y', colors='blue')
    #     ax2.tick_params(axis='both',labelsize=12)
        
    #     # Definir escalas fixas para os eixos de PCI e TCI
    #     ax1.set_ylim(-1, 0)  # Define a escala fixa de 0 a 10 para o eixo de PCI
    #     ax2.set_ylim(0, 100)  # Define a escala fixa de 40 a 60 para o eixo de TCI
    #     # Aumentar a quantidade de ticks nos eixos y
      
    #     y_ticks_pci = np.linspace(-1, 0, num_ticks)
    #     y_ticks_tci = np.linspace(0, 100, num_ticks)

    #     ax1.set_yticks(y_ticks_pci)
    #     ax2.set_yticks(y_ticks_tci)
 
       

    #     # Combine as legendas de ambos os eixos
    #     handles, labels = ax1.get_legend_handles_labels()
    #     handles2, labels2 = ax2.get_legend_handles_labels()
    #     ax1.legend(list_patch,FASES,loc='best',fontsize=12)
    #     ax2.legend(handles + handles2, labels + labels2,loc='best',fontsize=12)
    #     ax1.grid(True, color='lightgray')
    #     ax2.grid(True, color='gray')
    #     plt.title('Gráfico P.C.I e T.C.I',fontsize=14)

              
    #     # Salvar o gráfico em um buffer
    #     buffer = io.BytesIO()
    #     plt.savefig(buffer, format='svg')
    #     buffer.seek(0)
        
    #     # Fechar a figura atual
    #     plt.close()
    #     # Retornar os dados da imagem
    #     self.grafico_ciclo = base64.b64encode(buffer.read())
        
    def action_update_grafico(self):
        self.set_chart_image()

    def action_ler_diretorio(self):
        #TODO ver se a data do diretório é maior que a data da ultima_atualizacao, atualizando somente máquinas que tiverem ciclos novos
        
        # self.ler_diretorio_ciclos("ETO04")
        # self.ler_diretorio_ciclos("ETO03")
        # self.ler_diretorio_ciclos("ETO02")
        self.ler_diretorio_ciclos("ETO04")

    def action_insert_mass_eto(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Inserir Massa ETO',
            'res_model': 'steril_supervisorio.insert.mass.eto.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {'default_ciclo': self.id,
                        'default_state_ciclo': self.state}
         }
    
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
                        'default_indicador_bi': self.indicador_biologico,
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
                        'default_indicador_bi': self.indicador_biologico,
                        'default_reprovado': True,
                        }
        }
    
    def action_ciclos_documents(self):
        """Return the documents of corresponding ciclos """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documentos',
            'view_mode': 'kanban,form',
            'res_model': 'ir.attachment',
            'domain': [('res_id', '=', self.id),
                       ('res_model', '=', 'steril_supervisorio.ciclos')],
            'context': "{'create': True}"
        }

class SupervisorioCiclosIndicadorBiologico(models.Model):
    _name = 'steril_supervisorio.ciclos.indicador.biologico'
    _description = 'Indicador Biológico'
   
    name = fields.Char("Lote")
    marca = fields.Char()
    modelo = fields.Char()
    data_fabricacao = fields.Date()
    data_validade = fields.Date()


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
    pci_max =  fields.Float(string='Pmax')
    pci_min =  fields.Float(string='Pmin')
    pci_avg =  fields.Float(string='Pmedia')
    pci_freq =  fields.Float(string='Pfreq')
    tci_max =  fields.Float(string='Tmax')
    tci_min =  fields.Float(string='Tmin')
    tci_avg =  fields.Float(string='Tmedia')
    tci_freq =  fields.Float(string='Tfreq')
    ur_max =  fields.Float(string='URmax')
    ur_min =  fields.Float(string='URmin')
    ur_avg =  fields.Float(string='URmedia')
    ur_freq =  fields.Float(string='URfreq')
    

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


    
   
    