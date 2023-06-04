
from odoo import models, fields, api, _
import base64
from datetime import date, datetime,timedelta

from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
import pytz
import re
from odoo.exceptions import UserError, ValidationError
import os

fuso_horario = pytz.timezone('America/Sao_Paulo')

class SupervisorioCiclos(models.Model):
    _name = 'steril_supervisorio.ciclos'

    _description = 'Ciclos do supervisorio'
    _order = 'data_inicio desc'
    _inherit = ['mail.thread', "mail.activity.mixin"]

    name = fields.Char(
        string='Codigo Ciclo',
    )
    state = fields.Selection(string='Status', selection=[('iniciado', 'Iniciado'),
                                                         ('em_andamento', 'Em andamento'),
                                                         ('finalizado', 'Finalizado') ,
                                                         ('incompleto', 'Incompleto') ,
                                                         ('esperando_biologico', 'Esperando Resultado'), 
                                                         ('abortado', 'Abortado'), 
                                                         ('concluido', 'Concluído'), 
                                                         ('cancelado', 'Cancelado'), 
                                                        
                                                         ], default='iniciado'
                                                         )
    data_inicio =  fields.Datetime()
    data_fim =  fields.Datetime(tracking=True)
    duration = fields.Float("Duração", compute = "_compute_duration",store=True)
    file = fields.Binary()
    modelo_ciclo = fields.Selection([('eto', 'ETO'),('vapor', 'VAPOR')], default='eto')
    def _get_default_supervisor(self):
        supervisor_default = self.env['ir.config_parameter'].sudo().get_param('steril_supervisorio.supervisor_ciclos')
        print(supervisor_default)
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
    
    def _arquivo_modificado_recentemente(self, path_arquivo):
        #pega paramento do sistema com a data da ultima atualizacao dos ciclos
        time_parametro_sistema = datetime.strptime(self.env['ir.config_parameter'].get_param('steril_supervisorio_ultima_atualizacao'), '%Y-%m-%d %H:%M:%S').date()
        print(time_parametro_sistema)

        timestamp_modificacao = os.path.getmtime(path_arquivo)
        data_modificacao = datetime.fromtimestamp(timestamp_modificacao).date()            
        if data_modificacao >= time_parametro_sistema:
            return True
        else:
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
          
            if os.path.isdir(caminho_pasta):
                print(nome_pasta)
                codigo_ciclo = nome_pasta

                print(os.listdir(caminho_pasta))
                lista_de_arquivos = os.listdir(caminho_pasta)
                print(lista_de_arquivos)

                # filtrando apenas os arquivos tipo txt
                lista_de_arquivos_txt = [arquivo for arquivo in lista_de_arquivos if arquivo.endswith('txt')]
                
                for arquivo in lista_de_arquivos_txt:  
                    path_full_file = caminho_pasta+'/'+arquivo
                    if self._arquivo_modificado_recentemente(path_full_file):
                        data_hora_inicio_str = arquivo.split('_')[1] + ' ' + arquivo.split('_')[2].replace('.txt', '')
                        
                        # Converter a data e hora para o formato datetime
                        data_inicio = self.convert_date_str_file_to_datetime(data_hora_inicio_str)
                        # Verificar se o código de ciclo já existe no modelo
                        ciclo_existente = self.env['steril_supervisorio.ciclos'].search([('name', '=', codigo_ciclo)])
                       
                        if not ciclo_existente:
                            print("tem novo ciclo")
                            # procurando equipamento pelo apelido
                            
                            print(equipment)
                            #    Criar um novo registro para o código de ciclo
                            ciclo = self.env['steril_supervisorio.ciclos'].create({
                                'name': codigo_ciclo,
                                'data_inicio': data_inicio,
                              
                                'equipment': equipment.id or None,
                                }
                                )

                        else:
                            ciclo=ciclo_existente
                        
                        print(ciclo)
                        if(ciclo ):
                            ciclo.adicionar_anexo_pdf(path_full_file)
                            ciclo.add_data_file_to_record(path_full_file)

        return True   
     
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
            print(segmentos[-1][0])
            return [True,self._calcular_tempo_decorrido(segmentos)]
        else:
            # retorna a a ultima hora do arquivo
            return [False,self._calcular_tempo_decorrido(dados)]
           
    def get_data_time_fim_de_ciclo(self,dados,segmentos):   
        formato = '%H:%M:%S'
        is_finish, data_time_delta  = self.ler_fim_de_ciclo(dados,segmentos)
        print(type(data_time_delta))
        print(data_time_delta)
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
            horas, minutos, segundos = diferenca
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

    def adicionar_anexo_pdf(self,caminho_arquivo):
        """
        Adiciona um anexo ao modelo atual a partir de um arquivo local. 

        
        :param caminho_arquivo: Caminho completo do arquivo local a ser anexado com o nome do arquivo .
        :return: O objeto de anexo criado ou retorna false caso não exista o arquivo em pdf
        """
        caminho_arquivo = caminho_arquivo.replace(".txt",".pdf")
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
        print(attachment)
        #self.message_post(attachment_ids=[attachment.id])
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
        fases = ['LEAK-TEST',
                  'ACONDICIONAMENTO',
                  'UMIDIFICACAO',
                  'ESTERILIZACAO',
                  'LAVAGEM',
                  'AERACAO',
                  'CICLO FINALIZADO']
        str_dados_ciclo = '<table class="table table-sm table-condensed table-striped">'
        #filtrando apenas as fases
        segmentos_filtered = [x for x in segmentos if x[1] in fases]
        print(segmentos_filtered)

        #calculando os tempos de cada fase
        tempos  = self.calcular_diferenca_tempo(segmentos_filtered)

        #mostrando resultados
        for tempo in tempos:
            index = tempos.index(tempo)
            h,m,s = tempo
            str_dados_ciclo =str_dados_ciclo + f'<tr ><td>{fases[index]}:</td><td align="right"> {h}h {m}m {s}s</td></tr>'
        soma_total = self.calcular_soma_tempo(tempos)
        h,m,s = soma_total
        print(f"TOTAL: {h}h {m}m {s}s")
        str_dados_ciclo =str_dados_ciclo + f'<tr align="right"><td>TOTAL</td><td> {h}h {m}m {s}s</td></tr>'
        str_dados_ciclo = str_dados_ciclo +"</table>"
        return str_dados_ciclo
    
    def monta_estatisticas_ciclo(self, dados):
        return 0
    
    def passaram_24_horas(self,data_inicio):
        agora = fields.Datetime.now()
        diff = agora - self.data_inicio

        if diff > timedelta(hours=24):
            return True
        else:
            return False

    def add_data_file_to_record(self,file):
        
        #lendo arquivo com os dados do ciclo
        dados,segmentos = self.ler_arquivo_dados(file)

        self.tempos_ciclo = self.monta_tempos_ciclo(segmentos)
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


        self.estatisticas_ciclo = self.monta_estatisticas_ciclo(dados)

    def action_ler_diretorio(self):
        self.ler_diretorio_ciclos("ETO03")