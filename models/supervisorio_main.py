from odoo import models, fields,api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    active_standard_price = fields.Boolean(string='Standard price as a code',
                                           help="check this box to show cost on the product labels as code")
    active_ref = fields.Boolean(string='Show product reference ',
                                help="check this box to show product reference as in product labels")

 
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        active_standard_price = params.get_param('active_standard_price', default=False)
        active_ref = params.get_param('active_ref', default=False)
        res.update(
            active_standard_price=bool(active_standard_price),
            active_ref=bool(active_ref),
        )
        return res


    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param("active_standard_price",
                                                         self.active_standard_price)
        self.env['ir.config_parameter'].sudo().set_param("active_ref",
                                                         self.active_ref)

class Supervisorio(models.Model):
    _name = 'steril_supervisorio.supervisorio'
    _description = 'Descrição do Meu Modelo'

    name = fields.Char(string='Nome', required=True)
    campo_outro = fields.Integer(string='Campo Outro')
    supervisor = fields.Many2one(
         string='Supervisor',
         comodel_name='hr.employee',
        
    )

