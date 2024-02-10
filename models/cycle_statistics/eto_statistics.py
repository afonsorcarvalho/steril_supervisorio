# ler dados da fita de impressão para AFR 1.3 mirax


class eto_statistics():

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
    header_lines = 25
    def set_filename(self,filename):
        self.filename = filename
    def set_header_lines(self,value):
        self.header_lines = value
    def extract_header_cycle_sterilization(self):
        
            

        header_items = ['Data', 'Hora', 'Equipamento', 'Operador', 'Cod. ciclo', 'Ciclo Selecionado',
                            'Pulsos Acond.', 'Tempo Vapor (s))', 'Tempo Esteril. (s))', 'P. Esteril. Max (bar)',
                            'P. Esteril. Min (bar)', 'Pulsos Lavagem', 'Pulsos Aeração']
        # Dicionário para armazenar os dados extraídos
        data = {}
        try:
            with open(self.filename, 'r') as file:
                lines = file.readlines()
        except FileNotFoundError:
            print(f"Erro: O arquivo '{self.filename}' não foi encontrado.")
           
        except IOError:
            print(f"Erro: Houve um problema ao ler o arquivo '{self.filename}'.")
           
               

        # Iterar pelas linhas para extrair os dados
        for line in lines:
            # Verificar se a linha contém dois pontos
            if ':' in line:
                # Dividir a linha pelo separador ':'
                parts = line.split(':')
                if len(parts) >= 2:  # Verificar se a linha contém pelo menos dois elementos após a divisão
                    key = parts[0].strip()
                    value = ':'.join(parts[1:]).strip()  # Juntar os elementos restantes para o valor
                    # Remover os caracteres '\x00' do valor
                    value = value.replace('\x00', '')
                    # Adicionar os dados ao dicionário
                    if key in header_items:
                        data[key] = value

        return data
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

        # Iterar pelas linhas para extrair os dados
        for line in lines:
            # Verificar se a linha contém os dados de interesse
            if line.strip() and not line.startswith('-'):
                # Dividir a linha pelos espaços em branco
                parts = line.split()
                # Extrair os dados de interesse (hora, PCI, TCI, UR)
                if len(parts) == 4:
                    hora, pci, tci, ur = parts
                    # Adicionar os dados à lista
                    data.append({'Hora': hora, 'PCI': pci, 'TCI': tci, 'UR': ur})

        return data
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
        with open(self.filename, 'r') as file:
            found_start = False
            found_end = False
            for line in file:
                values = line.strip().split()
                if len(values) == 2:
                    if values[1] == start_event:
                        found_start = True
                    if values[1] == end_event:
                        found_end = True

                if found_start and found_end:
                    break
                if found_start:
                    values = line.strip().split()
                    if len(values) >= 4:
                        hora, pci, tci, ur = values[:4]
                        data.append({'Hora': hora, 'PCI': pci, 'TCI': tci, 'UR': ur})
        return data

    def extract_data_sterilization(self):
        data = self.extract_data_between_events('ESTERILIZACAO','LAVAGEM')
        return data
    def dados_desde_pressao_limite(self,dados, pressao_limite):
        """Returns data from a specified point where the PCI pressure reaches or exceeds a limit.

            Args:
                dados (list): A list of dictionaries containing data with 'Hora' and 'PCI' keys.
                pressao_limite (float): The PCI pressure limit.

            Returns:
                list: A list of dictionaries containing data from the point where PCI pressure reaches or exceeds the limit.

            Note:
                The function searches for the first occurrence where the PCI pressure in the data exceeds
                or equals the specified limit. It returns all data from that point onwards.
        """
        # Encontrar o índice onde a pressão PCI atinge ou ultrapassa o limite
        indice_inicio = None
        for i, dado in enumerate(dados):
            if float(dado['PCI']) >=  pressao_limite:
                indice_inicio = i
                #print(indice_inicio)
                break

        # Se não encontrar nenhum ponto acima do limite, retornar uma lista vazia
        if indice_inicio is None:
            return []

        # Retornar os dados a partir do índice encontrado
        return dados[indice_inicio:]
    
    def calculate_metrics(self,data, time_interval):
        from datetime import datetime, timedelta
        
        # Convert the time interval to seconds
        time_interval_seconds = time_interval * 60
        
        # Convert the data times to datetime objects
        data_times = [datetime.strptime(entry['Hora'], '%H:%M:%S') for entry in data]
        print(data_times)
        # Initialize lists to store values within the time interval
        pci_values = []
        tci_values = []
        ur_values = []
        
        # Initialize variables for total sum
        total_pci = 0
        total_tci = 0
        total_ur = 0
        
        # Initialize variables for min and max
        min_pci = float('inf')
        min_tci = float('inf')
        min_ur = float('inf')
        max_pci = float('-inf')
        max_tci = float('-inf')
        max_ur = float('-inf')
        
        # Initialize a variable to count entries within the time interval
        count_entries = 0
        
        # Loop through the data and calculate metrics
        for i, entry in enumerate(data):
            # Get the current time and calculate the difference from the start time
            current_time = data_times[i]
            time_difference = current_time - data_times[0]
            
            # # If the time difference is within the interval, update metrics
            # if time_difference.total_seconds() <= time_interval_seconds:
            #     count_entries += 1
                
            # Convert string values to float
            pci = float(entry['PCI'])
            tci = float(entry['TCI'])
            ur = float(entry['UR'])
            
            # Add values to lists
            pci_values.append(pci)
            tci_values.append(tci)
            ur_values.append(ur)
            
            # Update total sum
            total_pci += pci
            total_tci += tci
            total_ur += ur
            
            # Update min and max values
            min_pci = min(min_pci, pci)
            min_tci = min(min_tci, tci)
            min_ur = min(min_ur, ur)
            max_pci = max(max_pci, pci)
            max_tci = max(max_tci, tci)
            max_ur = max(max_ur, ur)
          
                
        # Calculate average values
        avg_pci = total_pci / count_entries if count_entries > 0 else 0
        avg_tci = total_tci / count_entries if count_entries > 0 else 0
        avg_ur = total_ur / count_entries if count_entries > 0 else 0
        
        # Return metrics
        return {
            'PCI': {'min': min_pci,'max': max_pci,'avg': avg_pci},
            'TCI': {'min': min_tci,'max': max_tci,'avg': avg_tci},
            'UR': {'min': min_ur,'max': max_ur,'avg': avg_ur},
        
        }

    


# t = eto_statistics()
# t.set_filename("060224-01_20240206_131429.txt")
# data = t.extract_data_sterilization()
# data_sterilization = t.dados_desde_pressao_limite(data,-0.180)
# data_statistics = t.calculate_metrics(data_sterilization, 5)
# print(data_statistics)



# data_statistics = t.calculate_metrics(data_sterilization, 120)
# print(data_statistics)
# data_statistics = t.calculate_metrics(data_sterilization, 235)

# print(data_statistics)
