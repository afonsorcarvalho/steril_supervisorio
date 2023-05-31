
# -*- coding: utf-8 -*-
{
    'name': 'Supervisorio Steriliza',
    'version': '1.0',
    'summary': 'Supervisório das máquinas de Limpeza e esterilização da Steriliza Corporation',
    'description': 'Descrição detalhada do módulo',
    'author': 'Afonso Carvalho',
    'depends': ['base','engc_os'],
    'data': [
        'views/supervisorio_menu_views.xml',
        'views/supervisorio_views.xml',
        'views/ciclos_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': True,
}
