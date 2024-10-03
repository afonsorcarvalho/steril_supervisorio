# -*- encoding: utf-8 -*-
# © 2024 Afonso Carvalho


from odoo import api, fields, models

class CycleModel(models.Model):
    _name = 'steril_supervisorio.cycle_model'
    _description = 'Modulo de modelo de ciclo para equipamentos'
    
    name = fields.Char()
    header_data = fields.One2many(string='Cabeçalho',comodel_name='steril_supervisorio.cycle.model.header.data',inverse_name='cycle_model',
    copy=True
     )
    phase_data = fields.One2many(string='Fases',comodel_name='steril_supervisorio.cycle.model.phase.data',inverse_name='cycle_model',copy=True )
    magnitude_data = fields.One2many(string='Grandezas',comodel_name='steril_supervisorio.cycle.model.magnitude',inverse_name='cycle_model',copy=True )
    porcentagem_eto = fields.Float(string="Porcentagem ETO",copy=True)
    incomplete_time_cycle = fields.Integer(help="Tempo onde é considerado incompleto o ciclo") 

    # isso é usado pra calcular onde começa e finaliza a esterilização

    effective_sterilization_event_start = fields.Char() # qual a fase que inicia a esterilizacao na fita
    effective_sterilization_envent_stop = fields.Char() # qual a fase que finaliza a esterilizacao na fita
    effective_sterilization_threshold_value = fields.Float() # valor que indica início da esterilização na fita
    effective_sterilization_threshold_uncertainty = fields.Float()  # valor da incerteza que indica início da esterilização na fita
    effective_sterilization_threshold_column_name = fields.Char() # nome da coluna que indica início da esterilização efetiva na fita
    
    def copy(self, default=None):
        if default is None:
            default = {}
        # Adicione aqui sua lógica personalizada
        # Por exemplo, definir um novo nome para a cópia
        default['name'] = 'Cópia de ' + (self.name or '')
        return super(CycleModel, self).copy(default=default)
   


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
   


