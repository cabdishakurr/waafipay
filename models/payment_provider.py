from odoo import api, fields, models
from odoo.exceptions import ValidationError

class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('waafipay', 'WaafiPay')],
        ondelete={'waafipay': 'set default'}
    )
    waafipay_merchant_id = fields.Char(
        string='WaafiPay Merchant ID',
        help='The merchant ID provided by WaafiPay',
        required_if_provider='waafipay'
    )
    waafipay_api_key = fields.Char(
        string='WaafiPay API Key',
        help='The API key provided by WaafiPay',
        required_if_provider='waafipay'
    )
    waafipay_secret_key = fields.Char(
        string='WaafiPay Secret Key',
        help='The secret key provided by WaafiPay',
        required_if_provider='waafipay'
    )
    waafipay_environment = fields.Selection(
        string='Environment',
        selection=[('test', 'Test'), ('prod', 'Production')],
        default='test',
        required_if_provider='waafipay'
    )

    def _compute_feature_support_fields(self):
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'waafipay').update({
            'support_tokenization': True,
            'support_express_checkout': True,
            'support_refund': 'full_only',
        })

    @api.constrains('code', 'waafipay_environment')
    def _check_waafipay_environment(self):
        for provider in self:
            if provider.code == 'waafipay' and not provider.waafipay_environment:
                raise ValidationError("WaafiPay environment must be selected.")