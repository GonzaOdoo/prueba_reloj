# -*- coding: utf-8 -*-
{
    'name': "Biometrico pruebas",

    'summary': """
        Módulo para pruebas con dispositivos biométricos
        """,

    'description': """
        Módulo para pruebas con dispositivos biométricos    
    """,

    'author': "GonzaOdoo",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': ['base_setup', 'hr_attendance'],

    # always loaded
    "data": ["security/ir.model.access.csv",
             'views/biometric_device_details_views.xml',
             'views/hr_employee_views.xml',
             'views/biometric_device_attendance_menus.xml',
            ],
}
