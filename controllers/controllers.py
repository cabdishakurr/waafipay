import json
import logging
from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class WaafipayController(http.Controller):
    
    @http.route('/payment/waafipay/return', type='http', auth='public', csrf=False)
    def waafipay_return(self, **data):
        _logger.info("WaafiPay: handling return data: %s", data)
        request.env['payment.transaction'].sudo()._handle_feedback_data('waafipay', data)
        return request.redirect('/payment/status')

    @http.route('/payment/waafipay/cancel', type='http', auth='public', csrf=False)
    def waafipay_cancel(self, **data):
        _logger.info("WaafiPay: handling cancellation: %s", data)
        request.env['payment.transaction'].sudo()._handle_feedback_data('waafipay', data)
        return request.redirect('/payment/status')

    @http.route('/payment/waafipay/webhook', type='json', auth='public', csrf=False)
    def waafipay_webhook(self):
        data = json.loads(request.httprequest.data)
        _logger.info("WaafiPay: handling webhook data: %s", data)
        
        # Verify webhook signature
        signature = request.httprequest.headers.get('X-WaafiPay-Signature')
        if not signature:
            raise Forbidden("No signature provided")
            
        request.env['payment.transaction'].sudo()._handle_feedback_data('waafipay', data)
        return {'status': 'ok'}