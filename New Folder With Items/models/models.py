# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime


import dateutil.parser
import pytz
import pprint
from odoo.tools import consteq, float_round, image_process, ustr
from werkzeug import urls

from odoo import api, fields, models, _
# from odoo.addons.payment.models.payment_acquirer import ValidationError

# from odoo.tools.float_utils import float_compare
# from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.waafipay.controllers.controllers import Waafipay
# from odoo.addons.payment_gateway.wipay_payment.controllers.controllers import WipayController
from odoo.exceptions import ValidationError
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import dateutil, pytz
from werkzeug import urls
_logger = logging.getLogger(__name__)


class PaymentTransactionInherit(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, processing_values):
        """ Override of payment to return Sips-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of acquirer-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'waafipay':
            return res

        api_url = self.provider_id.waafipay_get_form_action_url()

        return {
            'hppUrl': processing_values.get('hppUrl'),
            'referenceId': processing_values.get('referenceId'),
            'hppRequestId': processing_values.get('hppRequestId'),
        }

    def _get_specific_processing_values(self, processing_values):
        """ Override of payment to return Adyen-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of acquirer-specific processing values
        :rtype: dict
        """

        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'waafipay':
            return res
        else:
            processing_values['wafi_payment_type'] = self.env.context.get("wafi_payment_type")
            return self.provider_id.waafipay_form_generate_values(processing_values)



class WaafiPay(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(selection_add=[
        ('waafipay', 'waafipay')
    ], ondelete={'waafipay': 'set default'})
    waafipay_merchant_id = fields.Char(string="Merchant ID")
    waafipay_storekey = fields.Char(string="Store key")
    waafipay_storeid = fields.Char(string="Store ID")
    bank = fields.Boolean(string="Bank Account", default=True)
    creditcard = fields.Boolean(string="Credit Card", default=True)
    mobilwallet = fields.Boolean(string="Mobile Account", default=True)
    qr_enabled = fields.Boolean(string="Enable QR Payments", default=False)
    qr_code = fields.Binary(string="QR Code", attachment=True)

    @api.model
    def _get_waafipay_urls(self, environment):

        """ waafipay URLS """
        if environment == 'prod':
            return {
                'waafipay_form_url': 'https://api.waafipay.net/asm',
            }
        else:
            return {
                'waafipay_form_url': 'https://sandbox.waafipay.net/asm',
            }

    def waafipay_form_generate_values(self, values):
        base_url = self.get_base_url()
        
        # Validate payment type
        valid_types = ['bank', 'credit', 'mobile']
        if not values.get('wafi_payment_type'):
            raise ValidationError(_('Payment type is required'))
        
        if values.get('wafi_payment_type') not in valid_types:
            raise ValidationError(_('Invalid payment type. Must be one of: %s') % ', '.join(valid_types))
        
        # Map payment types
        payment_type_mapping = {
            'bank': 'MWALLET_BANKACCOUNT',
            'credit': 'CREDIT_CARD', 
            'mobile': 'MWALLET_ACCOUNT'
        }
        payment_type = payment_type_mapping[values['wafi_payment_type']]

        currency = False
        if values.get('currency_id'):
            currency = self.env['res.currency'].browse(values.get('currency_id'))

        if not currency:
            raise ValidationError('Currency not found.')

        import requests
        # Get the correct API URL based on environment
        environment = 'prod' if self.state == 'enabled' else 'test'
        api_url = self._get_waafipay_urls(environment)['waafipay_form_url']
        
        _logger.info('WaafiPay Environment: %s', environment)
        _logger.info('WaafiPay API URL: %s', api_url)
        
        payload = "{\n                \"schemaVersion\"    : \"1.0\"," \
                  "\n                \"requestId\"         : \"R17100517154423\"," \
                  "\n                \"timestamp\"         : \"%s\"," \
                  "\n                \"channelName\"       : \"WEB\"," \
                  "\n                \"serviceName\"       : \"HPP_PURCHASE\"," \
                  "\n                \"serviceParams\": {" \
                  "\n                        \"storeId\"               : \"%s\"," \
                  "\n                        \"hppKey\"                : \"%s\"," \
                  "\n                        \"merchantUid\"           : \"%s\"," \
                  "\n                        \"hppSuccessCallbackUrl\" : \"%s\"," \
                  "\n                        \"hppFailureCallbackUrl\" : \"%s\"," \
                  "\n                        \"hppRespDataFormat\"  : \"4\"," \
                  "\n                        \"paymentMethod\"    : \"%s\"," \
                  "\n                        \n \"transactionInfo\" : {" \
                  "\n                                \"referenceId\"   : \"%s\"," \
                  "\n                                \"invoiceId\"  : \"%s\"," \
                  "\n                                \"amount\"     : \"%s\"," \
                  "\n                                \"currency\"   : \"%s\"," \
                  "\n                                \"description\": \"testing\"\n}\n}\n}" % (datetime.now(), self.waafipay_storeid, self.waafipay_storekey, self.waafipay_merchant_id,urls.url_join(base_url, Waafipay._return_url),urls.url_join(base_url, Waafipay._return_url), payment_type, values['reference'].replace("-","/"),values['reference'].replace("-","/"), values["amount"], currency.name)
        headers = {
            'content-type': "application/json",
            'cache-control': "no-cache",
        }

        response = requests.request("POST", api_url, data=payload, headers=headers)
        _logger.info('WaafiPay API Response: %s', response.text)

        try:
            response_data = response.json()
            if 'params' not in response_data:
                raise ValidationError(_('Invalid response format from WaafiPay: missing params'))
            
            params = response_data['params']
            required_fields = ['hppUrl', 'hppRequestId', 'referenceId']
            missing_fields = [field for field in required_fields if field not in params]
            
            if missing_fields:
                raise ValidationError(_('Missing required fields in WaafiPay response: %s') % ', '.join(missing_fields))
            
            waafipay_tx_values = dict(values)
            waafipay_tx_values.update({
                "hppUrl": params["hppUrl"],
                "hppRequestId": params["hppRequestId"],
                "referenceId": params["referenceId"],
            })
            return waafipay_tx_values
        
        except json.JSONDecodeError:
            _logger.error('Failed to decode JSON response from WaafiPay: %s', response.text)
            raise ValidationError(_('Invalid JSON response from WaafiPay'))
        except Exception as e:
            _logger.error('Error processing WaafiPay response: %s', str(e))
            raise ValidationError(_('Error processing payment: %s') % str(e))

    def waafipay_get_form_action_url(self):
        self.ensure_one()
        environment = 'prod' if self.state == 'enabled' else 'test'
        return self._get_waafipay_urls(environment)['waafipay_form_url']

    @api.model
    def _get_default_payment_method_id(self, code):
        if code != 'waafipay':
            return super()._get_default_payment_method_id(code)
        return self.env.ref('waafipay.payment_method_waafipay_account').id


class WaafipayPayment(models.Model):           #form transaction
    _inherit = 'payment.transaction'

    # waafipay_hash = fields.Char('Hash')

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    @api.model
    def _get_tx_from_notification_data(self, provider, data):
        tx = super()._get_tx_from_notification_data(provider, data)
        if provider != 'waafipay':
            return tx
        reference = data.json()['params']['referenceId'].replace("/", "-")
        if not reference:
            error_msg = _('waafipay: received data with missing reference (%s) or txn_id (%s)') % (reference, txn_id)
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        txs = self.env['payment.transaction'].search([('reference', '=', reference)])
        if not txs or len(txs) > 1:
            error_msg = 'waafipay: received data for reference %s' % (reference)
            if not txs:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.info(error_msg)
            raise ValidationError(error_msg)
        return txs[0]

    def _waafipay_form_get_invalid_parameters(self, data):
        invalid_parameters = []
        # # TODO: txn_id: shoudl be false at draft, set afterwards, and verified with txn details

        return invalid_parameters

    def _process_notification_data(self, data):
        super()._process_notification_data(data)
        if self.provider_code != 'waafipay':
            return
        status = data.json()['params']['state']
        former_tx_state = self.state
        res = {
            'provider_reference': data.json()['params']['referenceId'].replace("/", "-"),
        }

        if status in ['APPROVED']:
            try:
                # dateutil and pytz don't recognize abbreviations PDT/PST
                tzinfos = {
                    'PST': -8 * 3600,
                    'PDT': -7 * 3600,
                }
                date = dateutil.parser.parse(data.json().get('timestamp'), tzinfos=tzinfos).astimezone(
                    pytz.utc).replace(
                    tzinfo=None)
            except:
                date = fields.Datetime.now()
            res.update(last_state_change=date)
            self._set_done()
            if self.state == 'done' and self.state != former_tx_state:
                _logger.info('Validated waafipay payment for tx %s: set as done' % (self.reference))
                return self.write(res)
            return True
        else:
            error = 'Received unrecognized status for waafipay payment %s: %s, set as error' % (self.reference, status)
            res.update(state_message=error)
            self._set_canceled()
            if self.state == 'cancel' and self.state != former_tx_state:
                _logger.info(error)
                return self.write(res)
            return True

class AccountPaymentMethod(models.Model):
    _inherit = 'account.payment.method'

    @api.model
    def _get_payment_method_information(self):
        res = super()._get_payment_method_information()
        res['waafipay'] = {'mode': 'unique', 'domain': [('type', '=', 'bank')]}
        return res

    @api.model
    def _get_sdd_payment_method_code(self):
        res = super()._get_sdd_payment_method_code()
        res.append('waafipay')
        return res


