# ler dados da fita de impressão para AFR 1.3 mirax

def extract_cycle_sterilization_data(filename):
    # Dicionário para armazenar os dados extraídos
    data = {}

    # Abrir o arquivo e ler as linhas
    with open(filename, 'r') as file:
        lines = file.readlines()

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
                if key in ['Data', 'Hora', 'Equipamento', 'Operador', 'Cod. ciclo', 'Ciclo Selecionado',
                           'Pulsos Acond.', 'Tempo Vapor (s))', 'Tempo Esteril. (s))', 'P. Esteril. Max (bar)',
                           'P. Esteril. Min (bar)', 'Pulsos Lavagem', 'Pulsos Aeração']:
                    data[key] = value

    return data
 
def extract_cycle_data(filename,start_line):
    # Lista para armazenar os dados extraídos
    data = []

    # Abrir o arquivo e ler as linhas
    with open(filename, 'r') as file:
        lines = file.readlines()[start_line - 1:]

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
def extract_data_between_events(filename, start_event, end_event):
    data = []
    with open(filename, 'r') as file:
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

def dados_desde_pressao_limite(dados, pressao_limite):
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


# Exemplo de uso
filename = '060224-01_20240206_131429.txt'  # Substitua pelo nome do seu arquivo
sterilization_data = extract_cycle_sterilization_data(filename)
print(sterilization_data)

cycle_data = extract_cycle_data(filename,25)
for entry in cycle_data:
    print(entry)

print("AGORA SÓ OS DADOS DE ESTERILIZAÇÃO")
sterilization_data = extract_data_between_events(filename, "ESTERILIZACAO", "LAVAGEM")
for line in sterilization_data:
    print(line)

print("AGORA SÓ ESTERILIZANDO")

pressao_limite = -0.180
dados_desde_ponto = dados_desde_pressao_limite(sterilization_data, pressao_limite)
print(dados_desde_ponto)


