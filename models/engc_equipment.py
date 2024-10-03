# -*- encoding: utf-8 -*-
# © 2024 Afonso Carvalho


from odoo import api, fields, models

class EngcEquipment(models.Model):
    _inherit = 'engc.equipment'

    cycle_model = fields.Many2one(string='Modelo de ciclo', comodel_name='steril_supervisorio.cycle_model', ondelete='restrict')
    chamber_size = fields.Float(string="Volume Câmara (L)")
    alarm_ids = fields.One2many(comodel_name='engc.equipment.alarms',inverse_name='equipment_id')

class EngcEquipmentAlarms(models.Model):
    _name = 'engc.equipment.alarms'
    _description = 'Log de Alarmes dos equipamentos'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _check_company_auto = True
    _order = "date_start,id"

    date_start = fields.Datetime("Data Início")
    date_stop = fields.Datetime("Data Fim")
    alarm_name = fields.Char("Alarme")
    alarm_code = fields.Char("Codigo")
    alarm_group = fields.Char("Grupo")
    equipment_id = fields.Many2one('engc.equipment')
    cycle_id = fields.Many2one('steril_supervisorio.ciclos')





    
