
from odoo import models, fields, api

import logging
_logger = logging.getLogger(__name__)


class InsertMassEtoWizard(models.TransientModel):
    _name = 'steril_supervisorio.insert.mass.eto.wizard'
    
    ciclo = fields.Many2one(
        'steril_supervisorio.ciclos', 
        required=True
        
       
        )
   
    value_mass_eto = fields.Float("Mass de gas (Kg)")
    
    def cancel(self):

        return {'type': 'ir.actions.act_window_close'}

    
    def save(self):
        # Lógica para salvar a data de início de incubação
            self.ciclo.write({
                'massa_eto': self.value_mass_eto*(self.ciclo.cycle_model.porcentagem_eto/100),
                'massa_eto_gas': self.value_mass_eto,
            })
          
        
               
       
            
        
