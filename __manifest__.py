# -*- coding: utf-8 -*-
{
    'name': "Waafipay",

    'summary': """WaafiPay Payment Gateway allows businesses and eCommerce to accept credit cards, mobile money and other payment methods securely and with easy integration.""",

    'description': """Waafipay Payment Provider""",

    'author': "Safarifone Inc",
    'website': "https://www.waafipay.net",


    'category': 'Accounting/Payment Provider',
    'version': '17.0.0.1',
    'depends': ['payment', 'account'],

    # always loaded
    'data': [
        'views/views.xml',
        'views/methode.xml',
        'views/templates.xml',
        'demo/demo.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'waafipay/static/src/js/payment_form.js',
            'waafipay/static/src/css/style.scss',
        ],
    },
    # only loaded in demonstration mode
    'demo': [],
    'price': '0.00',
    'currency': 'USD',
    'installable': True,
    'images': ['static/description/waafipay.png'],

    'external_dependencies': {
        'python': [
            'qrcode',
            'pycryptodome',
            'requests'
        ],
    },

}
