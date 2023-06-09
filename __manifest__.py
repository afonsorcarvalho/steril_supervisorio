
# -*- coding: utf-8 -*-
{
    'name': 'Supervisorio Steriliza',
    'version': '1.0',
    'summary': 'Supervisório das máquinas de Limpeza e esterilização da Steriliza Corporation',
    'description': 'Descrição detalhada do módulo',
    'author': 'Afonso Carvalho',
    'depends': ['base','engc_os'],
    'data': [
        'security/steril_supervisorio_security.xml',
        'security/ir.model.access.csv',
        'wizards/inicia_incubacao_bi.xml',
        'views/res_config_settings_views.xml',
        'views/supervisorio_apelidos_operador_views.xml',
        'views/supervisorio_views.xml',
        'views/supervisorio_ciclos_views.xml',
        'views/supervisorio_menu_views.xml',
        'reports/supervisorio_ciclo_reports_template.xml',
        'reports/supervisorio_ciclo_reports.xml',
    ],
    'installable': True,
    'application': True,
}
