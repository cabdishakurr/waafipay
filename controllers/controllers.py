# -*- coding: utf-8 -*-
from odoo import http
import logging
import pprint
import hashlib
from datetime import datetime

import requests
import werkzeug
from werkzeug import urls

from odoo import fields, http, SUPERUSER_ID, tools, _
from odoo.fields import Command
from odoo.addons.payment.models.payment_provider import ValidationError
from odoo.addons.payment.controllers.post_processing import PaymentPostProcessing
from odoo.addons.website_sale.controllers.main import PaymentPortal
from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.http import request
_logger = logging.getLogger(__name__)



class WebsiteSaleInherit(PaymentPortal):

    @staticmethod
    def _validate_transaction_kwargs(kwargs, additional_allowed_keys=()):
        """ Verify that the keys of a transaction route's kwargs are all whitelisted.

        The whitelist consists of all the keys that are expected to be passed to a transaction
        route, plus optional contextually allowed keys.

        This method must be called in all transaction routes to ensure that no undesired kwarg can
        be passed as param and then injected in the create values of the transaction.

        :param dict kwargs: The transaction route's kwargs to verify.
        :param tuple additional_allowed_keys: The keys of kwargs that are contextually allowed.
        :return: None
        :raise ValidationError: If some kwargs keys are rejected.
        """
        whitelist = {
            'provider_id',
            'payment_method_id',
            'token_id',
            'amount',
            'flow',
            'tokenization_requested',
            'landing_route',
            'is_validation',
            'csrf_token',
            'waafipay_payment_type',
        }
        whitelist.update(additional_allowed_keys)
        rejected_keys = set(kwargs.keys()) - whitelist
        if rejected_keys:
            raise ValidationError(
                _("The following kwargs are not whitelisted: %s", ', '.join(rejected_keys))
            )

    @http.route(
        '/shop/payment/transaction/<int:order_id>', type='json', auth='public', website=True
    )
    def shop_payment_transaction(self, order_id, access_token, **kwargs):
        """ Create a draft transaction and return its processing values.

        :param int order_id: The sales order to pay, as a `sale.order` id
        :param str access_token: The access token used to authenticate the request
        :param dict kwargs: Locally unused data passed to `_create_transaction`
        :return: The mandatory values for the processing of the transaction
        :rtype: dict
        :raise: ValidationError if the invoice id or the access token is invalid
        """
        request.env.context = dict(request.env.context)
        request.env.context.update({"waafipay_payment_type": request.params.get("waafipay_payment_type")})
        # Check the order id and the access token
        try:
            order_sudo = self._document_check_access('sale.order', order_id, access_token)
        except MissingError as error:
            raise error
        except AccessError:
            raise ValidationError(_("The access token is invalid."))

        if order_sudo.state == "cancel":
            raise ValidationError(_("The order has been canceled."))

        order_sudo._check_cart_is_ready_to_be_paid()

        self._validate_transaction_kwargs(kwargs)
        kwargs.update({
            'partner_id': order_sudo.partner_invoice_id.id,
            'currency_id': order_sudo.currency_id.id,
            'sale_order_id': order_id,  # Include the SO to allow Subscriptions to tokenize the tx
        })
        if not kwargs.get('amount'):
            kwargs['amount'] = order_sudo.amount_total

        if tools.float_compare(kwargs['amount'], order_sudo.amount_total, precision_rounding=order_sudo.currency_id.rounding):
            raise ValidationError(_("The cart has been updated. Please refresh the page."))

        tx_sudo = self._create_transaction(
            custom_create_values={'sale_order_ids': [Command.set([order_id])]}, **kwargs,
        )

        # Store the new transaction into the transaction list and if there's an old one, we remove
        # it until the day the ecommerce supports multiple orders at the same time.
        request.session['__website_sale_last_tx_id'] = tx_sudo.id

        self._validate_transaction_for_order(tx_sudo, order_id)

        return tx_sudo.with_context(
            wafi_payment_type=request.params.get("waafipay_payment_type"))._get_processing_values()


class PaymentProcessing(PaymentPostProcessing):

    @staticmethod
    def add_payment_transaction(transactions):
        if not transactions:
            return False
        tx_ids_list = set(request.session.get("__payment_tx_ids__", [])) | set(transactions.ids)
        request.session["__payment_tx_ids__"] = list(tx_ids_list)
        return True


class Waafipay(http.Controller):
    _return_url = '/handle_waafipay_response'

    # @http.route('/shop/payment/token', type='http', auth="public", methods=['POST', 'GET'], csrf=False)
    # def waafipay_dpn_gavdhjs(self, **post):
    #     print("yes")

    @http.route('/handle_waafipay_response', type='http', auth="public", methods=['POST', 'GET'], csrf=False)
    def waafipay_dpn(self, **post):
        """ waafipay DPN """
        _logger.info('Beginning waafipay DPN form_feedback with post data %s', pprint.pformat(post))  # debug
        try:
            print("Confirmation Done.")
            res = self.waafipay_validate_data(**post)
        except ValidationError:
            _logger.exception('Unable to validate the waafipay payment')
        return werkzeug.utils.redirect('/payment/status')
        # return werkzeug.utils.redirect('/payment/process')

    def waafipay_validate_data(self, **post):
        response = self.get_hpp_resultinfo(post)
        res = False
        # post['cmd'] = '_notify-validate'
        reference = response.json()["params"]["referenceId"]
        tx = None
        if reference:
            tx = request.env['payment.transaction'].sudo().search([('reference', '=', reference.replace("/","-"))])
        if not tx:
            # we have seemingly received a notification for a payment that did not come from
            # odoo, acknowledge it otherwise paypal will keep trying
            _logger.warning('received notification for unknown payment reference')
            return False

        resp = []
        if tx:
            resp.append(response.json()['params']['state'])
        else:
            resp.append(response.json()['params']['state'])
        if 'APPROVED' in resp:
            _logger.info('WaafiPay: validated data')
            res = request.env['payment.transaction'].sudo()._handle_notification_data('waafipay', response)
            if not res and tx:
                tx._set_error('Validation error occured. Please contact your administrator.')
        elif 'DECLINED' in resp:
            _logger.warning('WaafiPay: answered INVALID/FAIL on data verification')
            if tx:
                tx._set_error('Invalid response from WaafiPay. Please contact your administrator.')
        else:
            _logger.warning(
                'WaafiPay: unrecognized paypal answer, received %s instead of VERIFIED/SUCCESS or INVALID/FAIL (validation: %s)' % (
                resp, 'PDT' if pdt_request else 'IPN/DPN'))
            if tx:
                tx._set_error('Unrecognized error from WaafiPay. Please contact your administrator.')
        return res

    def get_hpp_resultinfo(self, post):
        import requests
        key = request.env['payment.provider'].sudo().search([('code', '=', "waafipay")]).waafipay_storekey
        storeid = request.env['payment.provider'].sudo().search([('code', '=', "waafipay")]).waafipay_storeid
        merchantid = request.env['payment.provider'].sudo().search([('code', '=', "waafipay")]).waafipay_merchant_id

        url = "https://sandbox.safarifoneict.com/asm"

        payload = "{\n            \"schemaVersion\"     : \"1.0\"," \
                  "\n            \"requestId\"         : \"R17100517154423\"," \
                  "\n            \"timestamp\"         : \"%s\"," \
                  "\n            \"channelName\"       : \"WEB\"," \
                  "\n            \"serviceName\"       : \"HPP_GETRESULTINFO\"," \
                  "\n\n            \"serviceParams\"     : {" \
                  "\n\n                \"storeId\"       : \"%s\"," \
                  "\n                \"hppKey\"        : \"%s\"," \
                  "\n                \"merchantUid\"   : \"%s\"," \
                  "\n                \"hppResultToken\": \"%s\"\n}" \
                  "\n}" % (datetime.now(), storeid, key, merchantid, post['hppResultToken'])
        headers = {
            'content-type': "application/json",
            'cache-control': "no-cache",
        }
        response = requests.request("POST", url, data=payload, headers=headers)
        print(response.text)
        return response
