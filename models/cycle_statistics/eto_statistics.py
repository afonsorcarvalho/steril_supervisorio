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
    def dados_desde_pressao_limite(dados, pressao_limite):
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
            if float(dado['PCI'])>= pressao_limite:
                indice_inicio = i
                break

        # Se não encontrar nenhum ponto acima do limite, retornar uma lista vazia
        if indice_inicio is None:
            return []

        # Retornar os dados a partir do índice encontrado
        return dados[indice_inicio:]

# t = eto_statistics()
# t.set_filename("060224-01_20240206_131429.txt")
# print(t.extract_cycle_data())