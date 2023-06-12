
from odoo import models, fields, api

import logging
_logger = logging.getLogger(__name__)


class StartIncubationWizard(models.TransientModel):
    _name = 'steril_supervisorio.incubation_wizard'
    
    ciclo = fields.Many2one(
        'steril_supervisorio.ciclos', 
        required=True
        
       
        )
    indicador_biologico = fields.Many2one(
        'steril_supervisorio.ciclos.indicador.biologico',
        string='Lote BI', required=True
        )
    resultado_bi = fields.Selection(selection = [('positivo','Positivo'),('negativo','Negativo')])
    state_ciclo = fields.Selection(string='Status', selection=[('iniciado', 'Iniciado'),
                                                         ('em_andamento', 'Em andamento'),
                                                         ('finalizado', 'Finalizado') ,
                                                         ('incompleto', 'Incompleto') ,
                                                         ('esperando_biologico', 'Esperando Resultado BI'), 
                                                         ('esperando_aprovacao_supervisor', 'Esperando Aprovação Supervisor'), 
                                                         ('abortado', 'Abortado'), 
                                                         ('concluido', 'Concluído'), 
                                                         ('cancelado', 'Cancelado'), 
                                                         ('reprovado', 'Reprovado'), 
                                                        
                                                         ] 
                                                         )
    
    
    date_start = fields.Datetime(string='Data de Início de Incubação', 
        required=True, default=fields.Datetime.now,
        
        
    )
    date_end = fields.Datetime(string='Data de Leitura de Incubação', 
        required=True, default=fields.Datetime.now,
        
        
    )
    reprovado = fields.Boolean()
    motivo_reprovacao =  fields.Char(string='')

    
    def cancel(self):

        return {'type': 'ir.actions.act_window_close'}

    
    def save(self):
        # Lógica para salvar a data de início de incubação
        if self.state_ciclo == 'finalizado':
            self.ciclo.write({
                'data_incubacao_bi': self.date_start,
                'state':'esperando_biologico',
                'indicador_biologico': self.indicador_biologico,

            })
        if self.state_ciclo == 'esperando_biologico':
            self.ciclo.write({
                'data_leitura_resultado_bi': self.date_end,
                'state':'esperando_aprovacao_supervisor',
                'resultado_bi': self.resultado_bi,

            })
        if self.state_ciclo == 'esperando_aprovacao_supervisor':
            motivo_reprovacao = ""
            _logger.info(self.reprovado)
            if self.reprovado == True:
                motivo_reprovacao = self.motivo_reprovacao
                self.ciclo.write({
                
                'state':'reprovado',
                
                'motivo_reprovado': motivo_reprovacao,

                })
            else:
                self.ciclo.write({'state':'concluido'})
               
       
            
        
