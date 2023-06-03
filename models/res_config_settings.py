# Copyright 2022 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    supervisor_ciclos = fields.Many2one(
         string='Supervisor',
         comodel_name='hr.employee',
      
        
    )
  

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('steril_supervisorio.supervisor_ciclos', self.supervisor_ciclos.id)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res['supervisor_ciclos'] = self.env['ir.config_parameter'].sudo().get_param('steril_supervisorio.supervisor_ciclos')
        return res
  