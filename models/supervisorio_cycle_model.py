# -*- encoding: utf-8 -*-
# © 2024 Afonso Carvalho


from odoo import api, fields, models

class CycleModel(models.Model):
    _name = 'steril_supervisorio.cycle_model'
    _description = 'Modulo de modelo de ciclo para equipamentos'
    
    name = fields.Char()
    header_data = fields.One2many(string='Cabeçalho',comodel_name='steril_supervisorio.cycle.model.header.data',inverse_name='cycle_model' )
    phase_data = fields.One2many(string='Fases',comodel_name='steril_supervisorio.cycle.model.phase.data',inverse_name='cycle_model' )
    magnitude_data = fields.One2many(string='Grandezas',comodel_name='steril_supervisorio.cycle.model.magnitude',inverse_name='cycle_model' )
   


class CycleModelHeaderData(models.Model):
    _name = 'steril_supervisorio.cycle.model.header.data'
   
    _description = 'Configura dados do cabeçalho'

    cycle_model = fields.Many2one(string='Modelo de ciclo', comodel_name='steril_supervisorio.cycle_model', ondelete='cascade')
    name = fields.Char("Nome")
    regex_tape = fields.Char("Regex Fita")
    value = fields.Char("Valor")
    type = fields.Selection([('char', 'Char'),('int', 'Integer'),('float','Float')])

class CycleModelPhaseData(models.Model):
    _name = 'steril_supervisorio.cycle.model.phase.data'
   
    _description = 'Configura das fases do ciclo'

    sequence = fields.Integer(string='Sequência', default=10)
    cycle_model = fields.Many2one(string='Modelo de ciclo', comodel_name='steril_supervisorio.cycle_model', ondelete='cascade')
    name = fields.Char("Nome")
    regex_tape = fields.Char("Regex Fita")
    type_search_tape = fields.Selection([('regex', 'Regex'), ('value_magnitude', 'Valor de magnitude')], default='regex')
    magnitude = fields.Many2one(comodel_name='steril_supervisorio.cycle.model.magnitude',string='Grandeza procura')
    magnitude_expression = fields.Char("Expressão",help="Expressão que procura na grandeza de procura selecionada.Ex. >= -0.180")
    hour_stop = fields.Char()
    is_invisible = fields.Boolean("Invisivel", default=False)
    type = fields.Selection([('char', 'Char'),('int', 'Integer'),('float','Float')])
class CycleModelMagnitudes(models.Model):
    _name = 'steril_supervisorio.cycle.model.magnitude'
   
    _description = 'Configuração das grandezas dos dados do ciclo'

    cycle_model = fields.Many2one(string='Modelo de ciclo', comodel_name='steril_supervisorio.cycle_model', ondelete='cascade')
    name = fields.Char("Nome")
    colunm = fields.Integer()
    type = fields.Selection([('char', 'Char'),('int', 'Integer'),('float','Float'),('time','Time')])
    magnitude = fields.Char(string='Grandeza')
   


