# ler dados da fita de impressão para AFR 1.3 mirax


import re
import statistics
from datetime import datetime, timedelta

class dataobject_fita_digital():

    """Extracts cycle sterilization data from a file.

    Args:
        filename (str): The name of the file to extract data from.

    Returns:
        dict: A dictionary containing the extracted data.

    Note:
        The file should contain lines with key-value pairs separated by ':',
        where the key is on the left side of ':' and the value is on the right side.
        Only specific keys ('Data', 'Hora', 'Equipamento', 'Operador', 'Cod. ciclo',
        'Ciclo Selecionado', 'Pulsos Acond.', 'Tempo Vapor (s))', 'Tempo Esteril. (s))',
        'P. Esteril. Max (bar)', 'P. Esteril. Min (bar)', 'Pulsos Lavagem', 'Pulsos Aeração')
        are considered for extraction.
    """
    filename = ""
    model_columns_name_data = []
    header_lines = 25
    header_items = []
    
    def set_filename(self,filename):
        self.filename = filename
    def set_header_lines(self,value):
        self.header_lines = value
    def set_header_items(self,items=['Data', 'Hora', 'Equipamento', 'Operador', 'Cod. ciclo', 'Ciclo Selecionado',
                            'Pulsos Acond.', 'Tempo Vapor (s))', 'Tempo Esteril. (s))', 'P. Esteril. Max (bar)',
                            'P. Esteril. Min (bar)', 'Pulsos Lavagem', 'Pulsos Aeração']):
        self.header_items = items

    def set_model_columns_name_data(self,columns_names=['Hora','PCI','TCI','UR']):
        self.model_columns_name_data = columns_names

    


    def extract_header_cycle_sterilization(self):
        
        # Dicionário para armazenar os dados extraídos
        data = {}
        header_lines = self.header_lines
        lines = []
        try:
            print(f"Lendo arquivo: {self.filename}")
            with open(self.filename, 'r') as file:
                lines = file.readlines()
                lines = lines[:25]
        except FileNotFoundError:
            print(f"Erro: O arquivo '{self.filename}' não foi encontrado.")
           
        except IOError:
            print(f"Erro: Houve um problema ao ler o arquivo '{self.filename}'.")
           
        # Iterar pelas linhas para extrair os dados
        for line in lines:
            # Verificar se a linha contém dois pontos
            
            if ':' in line:
                # Dividir a linha pelo separador ':'
                print(line)
                parts = line.split(':')
                if len(parts) >= 2:  # Verificar se a linha contém pelo menos dois elementos após a divisão
                    key = parts[0].strip()
                    value = ':'.join(parts[1:]).strip()  # Juntar os elementos restantes para o valor
                    # Remover os caracteres '\x00' do valor
                    value = value.replace('\x00', '')
                    # Adicionar os dados ao dicionário
                    if key in self.header_items:
                        data[key] = value
        print(f"Dados do Header lidos do arquivo: {data}")
        return data
    
    def filtrar_dados(self,dados):
        dados_filtrados = []
        padrao = r'\d{2}:\d{2}:\d{2}\s+-?\d+\.\d+\s+-?\d+\.\d+'
        for linha in dados:
            if re.match(padrao, linha):
                dados_filtrados.append(linha)
        return dados_filtrados
    
    def extract_cycle_data(self):

        """Extracts cycle data from a file starting from a specified line.

        Args:
            filename (str): The name of the file to extract data from.
            start_line (int): The line number to start extracting data from.

        Returns:
            list: A list of dictionaries containing the extracted data for each cycle.

        Note:
            The file should contain lines with space-separated values representing
            the hour, PCI, TCI, and UR. The function extracts data starting from
            the specified line number until the end of the file.
        """
        # Lista para armazenar os dados extraídos
        data = []
        
        # Abrir o arquivo e ler as linhas
        with open(self.filename, 'r') as file:
            lines = file.readlines()[self.header_lines - 1:]
       
        dados_filtrados = self.filtrar_dados(lines)
       
        lines = dados_filtrados
     

        # Iterar pelas linhas para extrair os dados
        for line in lines:
           
            # Verificar se a linha contém os dados de interesse
            if line.strip() and not line.startswith('-'):
                # Dividir a linha pelos espaços em branco
                parts = line.split()
               
                # Padrao para encontrar linhas com horas e numeros
                
               
                # Extrair os dados de interesse atraves da configuração grandezas
                
                if len(parts) == len(self.model_columns_name_data):
                 
                    d = dict()
                    for index,p in enumerate(parts):
                        d.update({self.model_columns_name_data[index]:p})    
                        
                    # Adicionar os dados à lista
                    data.append(d)
                    
       
        return data

    def mount_search(self,word):
        padrao = rf'^\d{{2}}:\d{{2}}:\d{{2}}\b.*\b{re.escape(word)}\b'

        return padrao
    def search_phase_time(self, phase_regex):
        padrao = self.mount_search(phase_regex)
        with open(self.filename, 'r') as file:
            for line in file:
                if re.search(padrao, line):
                    values = line.strip().split()
                    if len(values) >= 2:
                        return values[0]
        return None
    def compute_elapsed_time(self,start_time="00:00:00",end_time="00:00:00"):
        formato = '%H:%M:%S'

        if not start_time and not end_time:
            return None

        primeiro_item = datetime.strptime(start_time, formato)
        
        ultimo_item = datetime.strptime(end_time, formato)

         # Calcula a diferença de tempo entre os dois horários
        if primeiro_item <= ultimo_item:
            diferenca = ultimo_item - primeiro_item
        else:
            # Se o segundo horário for menor, significa que passou para o próximo dia
            # Adiciona um dia ao segundo horário
            ultimo_item += timedelta(days=1)
            diferenca = ultimo_item - primeiro_item

       

        return diferenca
            
    def extract_data_between_events(self, start_event, end_event):
        """Extracts data between two specified events from a file.

        Args:
        filename (str): The name of the file to extract data from.
        start_event (str): The start event to search for.
        end_event (str): The end event to search for.

        Returns:
        list: A list of dictionaries containing the extracted data.

        Note:
        The function looks for lines containing two values, where the second
        value matches either the start_event or end_event. It extracts data
        between the first occurrence of start_event and the first occurrence
        of end_event, inclusive.
        """
        data = []
        qtd_columns = len(self.model_columns_name_data)
       
        with open(self.filename, 'r') as file:
            found_start = False
            found_end = False

            for line in file:
                padrao = self.mount_search(start_event)
                if re.search(padrao, line):
                    found_start = True
                padrao = self.mount_search(end_event)
                if re.search(padrao, line):
                    found_end = True
                   

                if found_start and found_end:
                    break
                if found_start:
                    values = line.strip().split()
                    if len(values) >= qtd_columns:
                        d = dict()
                        for index,p in enumerate(values):
                            d.update({self.model_columns_name_data[index]:p}) 
                        # Adicionar os dados à lista
                        data.append(d)
            data = self.filtrar_dados(data)
        return data

    def extract_data_sterilization(self, event_start = 'ESTERILIZACAO', envent_stop ='LAVAGEM' ):
        data = self.extract_data_between_events(event_start,envent_stop)
        
        return data
    
    def data_threshold(self,data = [],threshold_name = 'PCI', threshold_value=-0.180, threshold_uncertainty=0.010):
    
        # Encontrar o índice onde a pressão PCI atinge ou ultrapassa o limite
        indice_inicio = None
        for i, dado in enumerate(data):

            print ("VALOR DO THERSHOLD - INCERTEZA")
            print (threshold_value - threshold_uncertainty)
            print ("VALOR DO DADO ESTERILIZAÇÃO")
            print (dado[threshold_name])
            if float(dado[threshold_name]) >=  (threshold_value - threshold_uncertainty) :
                indice_inicio = i
                print(indice_inicio)
                break

        # Se não encontrar nenhum ponto acima do limite, retornar uma lista vazia
        if indice_inicio is None:
            return []

        # Retornar os dados a partir do índice encontrado
        return data[indice_inicio:]
    
    #TODO refazer a função não está fazendo a media
    def calculate_metrics(self,data):
        from datetime import datetime, timedelta
        
        # Convert the time interval to seconds
      
        model_name_data = self.model_columns_name_data 
        # Convert the data times to datetime objects
        data_times = [datetime.strptime(entry[model_name_data[0]], '%H:%M:%S') for entry in data]
        values = {
            'duration': self.calcular_tempo_entre_horarios(data),
         }
        for index,md in enumerate(model_name_data):
            not_number = False
            value_column = []
            for d in data:
                try:
                   value_column.append(float(d[model_name_data[index]]))
                except:
                   not_number = True
                   pass
            if value_column:   
                values.update({
                    md: {
                        
                        'min': min(value_column),
                        'max': max(value_column),
                        'avg': statistics.mean(value_column)
                        }
                })
        #print(values)
        return values
        
        
    def calcular_tempo_entre_horarios(self,data):
        # Converte os horários para objetos datetime
        hora_formato = "%H:%M:%S"
        if len(data) < 2:
            return f"{0:02d}:{0:02d}:{0:02d}"
        primeiro_horario = datetime.strptime(data[0]['Hora'], hora_formato)
        segundo_horario = datetime.strptime(data[-1]['Hora'], hora_formato)
        
        # Calcula a diferença de tempo entre os dois horários
        if primeiro_horario <= segundo_horario:
            diferenca = segundo_horario - primeiro_horario
        else:
            # Se o segundo horário for menor, significa que passou para o próximo dia
            # Adiciona um dia ao segundo horário
            segundo_horario += timedelta(days=1)
            diferenca = segundo_horario - primeiro_horario
        
        # Formata a diferença de tempo para HH:mm:ss
        horas = diferenca.seconds // 3600
        minutos = (diferenca.seconds % 3600) // 60
        segundos = diferenca.seconds % 60
        
        return f"{horas:02d}:{minutos:02d}:{segundos:02d}"


        

    
#exemplo

#t = dataobject_fita_digital()
#t.set_filename("060224-01_20240206_131429.txt")
# t.set_model_columns_name_data(columns_names=['Hora','PCI','TCI','UR'])
#data_fase_sterilization = t.extract_header_cycle_sterilization()
# data_sterilization = t.data_threshold(data = data_fase_sterilization,threshold_name='PCI',threshold_value=-0.180)
# print('ESTERILIZAÇÃO')
# t.calculate_metrics(data_sterilization)
# data = t.extract_data_between_events(start_event='LAVAGEM',end_event='AERACAO')
# print('LAVAGEM')
# t.calculate_metrics(data)
# data = t.extract_data_between_events(start_event='AERACAO',end_event='CICLO FINALIZADO')
# print('AERACAO')
# t.calculate_metrics(data)



# data_statistics = t.calculate_metrics(data_sterilization, 120)
# print(data_statistics)
# data_statistics = t.calculate_metrics(data_sterilization, 235)

# print(data_statistics)