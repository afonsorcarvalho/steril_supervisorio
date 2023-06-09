
from odoo import models, fields, api

class StartIncubationWizard(models.TransientModel):
    _name = 'steril_supervisorio.incubation_wizard'
    
    date_start = fields.Date(string='Data de Início de Incubação')

    @api.multi
    def cancel(self):
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def save(self):
        # Lógica para salvar a data de início de incubação
        return {'type': 'ir.actions.act_window_close'}
