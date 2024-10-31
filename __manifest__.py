{
    'name': 'WaafiPay Payment Provider',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 350,
    'summary': 'Payment Provider: WaafiPay Implementation',
    'description': """Integrate WaafiPay payment gateway with Odoo 17""",
    'author': 'Cabdishakur',
    'website': 'https://github.com/cabdishakurr/waafipay',
    'depends': [
        'payment',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/payment_provider_views.xml',
        'views/payment_waafipay_templates.xml',
        'data/payment_provider_data.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'payment_waafipay/static/src/js/payment_form.js',
            'payment_waafipay/static/src/scss/payment_form.scss',
        ],
    },
    'application': True,
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
}