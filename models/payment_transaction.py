import logging
import pprint
from werkzeug import urls

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'waafipay':
            return res

        base_url = self.provider_id.get_base_url()
        waafipay_values = {
            'merchant_id': self.provider_id.waafipay_merchant_id,
            'api_key': self.provider_id.waafipay_api_key,
            'amount': self.amount,
            'currency': self.currency_id.name,
            'reference': self.reference,
            'return_url': urls.url_join(base_url, '/payment/waafipay/return'),
            'cancel_url': urls.url_join(base_url, '/payment/waafipay/cancel'),
            'webhook_url': urls.url_join(base_url, '/payment/waafipay/webhook'),
        }
        return waafipay_values

    def _process_notification_data(self, notification_data):
        super()._process_notification_data(notification_data)
        if self.provider_code != 'waafipay':
            return

        _logger.info("Processing WaafiPay notification data: %s", pprint.pformat(notification_data))
        
        # Verify the notification data
        if not self._verify_waafipay_signature(notification_data):
            raise ValidationError("Invalid WaafiPay signature")

        status = notification_data.get('status')
        if status == 'COMPLETED':
            self._set_done()
        elif status == 'FAILED':
            self._set_error("WaafiPay: " + notification_data.get('error_message', 'Payment failed'))
        elif status == 'PENDING':
            self._set_pending()
        elif status == 'CANCELLED':
            self._set_canceled()

    def _verify_waafipay_signature(self, notification_data):
        """Verify the signature of the notification data"""
        # Implement signature verification logic here
        return True