
# -*- coding: utf-8 -*-
{
    'name': 'Supervisorio Steriliza',
    'version': '1.0',
    'summary': 'Supervisório das máquinas de Limpeza e esterilização da Steriliza Corporation',
    'description': 'Descrição detalhada do módulo',
    'author': 'Afonso Carvalho',
    'depends': ['base','engc_os','web',  'board'],
    'sequence':-1,
    "qweb": [
        "static/src/components/steril_supervisorio_dashboard_view/steril_supervisorio_daschboard_view.xml",
        # "static/src/xml/owl_tree_view.xml",
    ],
    'data': [
        'security/steril_supervisorio_security.xml',
        'security/ir.model.access.csv',
        'wizards/inicia_incubacao_bi.xml',
        
        'views/res_config_settings_views.xml',
        'views/supervisorio_apelidos_operador_views.xml',
        'views/supervisorio_views.xml',
        'views/supervisorio_ciclos_views.xml',
        'views/supervisorio_dashboard_views.xml',
        'views/supervisorio_menu_views.xml',
        'reports/supervisorio_ciclo_reports_template.xml',
        'reports/supervisorio_ciclo_reports.xml',
    ],
    
    'assets':{
        'web.assets_backend':[
            'steril_supervisorio/static/src/components/steril_supervisorio_dashboard_view/*.xml',
            'steril_supervisorio/static/src/components/steril_supervisorio_dashboard_view/*.js',
            'steril_supervisorio/static/src/components/steril_supervisorio_dashboard_view/*.scss',
            'steril_supervisorio/static/src/components/kpi_card/*.xml',
            'steril_supervisorio/static/src/components/kpi_card/*.js',
            'steril_supervisorio/static/src/components/chart_renderer/*.js',
            'steril_supervisorio/static/src/components/chart_renderer/*.xml',
            'steril_supervisorio/static/src/js/*.js',
            'steril_supervisorio/static/src/scss/*.scss',
            'steril_supervisorio/static/src/xml/*.xml',

        ],

    },
    'installable': True,
    'application': True,
}
