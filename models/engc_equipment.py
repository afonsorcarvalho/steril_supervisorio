# -*- encoding: utf-8 -*-
# © 2024 Afonso Carvalho


from odoo import api, fields, models
import logging
_logger = logging.getLogger(__name__)
from odoo.exceptions import UserError, ValidationError
import csv
from datetime import datetime

class EngcEquipment(models.Model):
    _inherit = 'engc.equipment'

    cycle_model = fields.Many2one(string='Modelo de ciclo', comodel_name='steril_supervisorio.cycle_model', ondelete='restrict')
    chamber_size = fields.Float(string="Volume Câmara (L)")
    alarm_path_file = fields.Char()
    alarm_ids = fields.One2many(comodel_name='engc.equipment.alarms',inverse_name='equipment_id')

    def load_alarms(self,equipment_alias=""):
        dbname = self.env.cr.dbname
        dir_name_ciclos = self.env['ir.config_parameter'].get_param('steril_supervisorio_dir_name_ciclos')
        alias = equipment_alias if equipment_alias else self.apelido 
        diretorio = f"/var/lib/odoo/filestore/{dbname}/{dir_name_ciclos}/{alias}/"
        equipment = self.env['engc.equipment'].search([('apelido','=like',alias )])
        if not equipment:
           raise ValidationError(f'Não foi possível achar equipamento com o apelido {alias}') 
        alarm_path_file = diretorio + equipment.alarm_path_file

        # Ler o arquivo CSV no modo binário e remover caracteres nulos
        try:
            with open(alarm_path_file, mode='rb') as file:
                content = file.read().replace(b'\x00', b'')  # Remover caracteres NULL
            content = content.decode('ISO-8859-1')  # Decodificar usando a codificação correta
        
            # Processar o conteúdo como CSV
            reader = csv.reader(content.splitlines(), delimiter='\t')
            print(reader)
        except Exception as e:
            _logger.exception(e)
            raise ValidationError(f'Não foi possível ler arquivo: {alarm_path_file}') 
        # Reabrir o conteúdo como texto após remover os caracteres nulos
        values =[]
        alarms = []
        primeiro = True
        
        for row in reader:
            if primeiro:
                primeiro = False
                continue
            if self.alarm_ids.search([('date_start','=',row[1]+" "+row[2])]):
                print(f"já tem: {row} ")
                continue
            else:
                alarms.append(row)
        
         
        for line in alarms[1:]:
            values.append((0,0,{
                 'date_start' : datetime.strptime(line[1]+" "+line[2], '%Y-%m-%d %H:%M:%S'),
                 'date_stop' : datetime.strptime(line[5]+" "+line[6], '%Y-%m-%d %H:%M:%S') if line[5] else None,
                 'alarm_code' : line[7],
                 'alarm_name' : line[8],
                 'equipment_id': equipment.id
             }))
           
        print(self.write({'alarm_ids':values}))

    # Função para remover caracteres nulos e filtrar alarmes entre duas datas
    def filter_alarms_by_date(self,csv_file, start_date, end_date):
        filtered_alarms = []
        
        # Converter strings de data para objetos datetime
        start_date = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
        end_date = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
        
        # Ler o arquivo CSV no modo binário e remover caracteres nulos
        with open(csv_file, mode='rb') as file:
            content = file.read().replace(b'\x00', b'')  # Remover caracteres NUL

        # Reabrir o conteúdo como texto após remover os caracteres nulos
        content = content.decode('ISO-8859-1')  # Decodificar usando a codificação correta
        
        # Processar o conteúdo como CSV
        reader = csv.reader(content.splitlines(), delimiter='\t')
        
        # Iterar sobre cada linha do conteúdo filtrado
        for row in reader:
            try:
                # Tentar converter a "Trigger Time" para datetime
                trigger_time = datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S')
                
                # Verificar se a data está dentro do intervalo
                if start_date <= trigger_time <= end_date:
                    filtered_alarms.append(row)
            except (ValueError, IndexError):
                # Se houver erro ao processar a data ou a linha não estiver formatada corretamente, ignorar
                continue
        
        return filtered_alarms


class EngcEquipmentAlarms(models.Model):
    _name = 'engc.equipment.alarms'
    _description = 'Log de Alarmes dos equipamentos'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _check_company_auto = True
    _order = "date_start desc"

    date_start = fields.Datetime("Data Início")
    date_stop = fields.Datetime("Data Fim")
    alarm_name = fields.Char("Alarme")
    alarm_code = fields.Char("Codigo")
    alarm_group = fields.Char("Grupo")
    equipment_id = fields.Many2one('engc.equipment')
    cycle_id = fields.Many2one('steril_supervisorio.ciclos')
    
    _sql_constraints = [('date_start_equipment_id_unique', 'unique(date_start, equipment_id,alarm_code)',
                         'Alarme já cadastrado'
                         'Não é permitido')]
    
    







    
