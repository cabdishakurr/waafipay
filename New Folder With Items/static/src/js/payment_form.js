/** @odoo-module **/

import paymentForm from '@payment/js/payment_form';

paymentForm.include({
     _prepareTransactionRouteParams() {
        debugger;
        let transactionRouteParams = {
            'provider_id': this.paymentContext.providerId,
            'payment_method_id': this.paymentContext.paymentMethodId ?? null,
            'token_id': this.paymentContext.tokenId ?? null,
            'amount': this.paymentContext['amount'] !== undefined
                ? parseFloat(this.paymentContext['amount']) : null,
            'flow': this.paymentContext['flow'],
            'tokenization_requested': this.paymentContext['tokenizationRequested'],
            'landing_route': this.paymentContext['landingRoute'],
            'is_validation': this.paymentContext['mode'] === 'validation',
            'access_token': this.paymentContext['accessToken'],
            'csrf_token': odoo.csrf_token,
            'waafipay_payment_type': (this.paymentContext.paymentMethodCode === 'waafipay') ? $("input[type='radio'][name=waafi_payment_type]:checked").attr('id') : '',
        };
        // Generic payment flows (i.e., that are not attached to a document) require extra params.
        if (this.paymentContext['transactionRoute'] === '/payment/transaction') {
            Object.assign(transactionRouteParams, {
                'currency_id': this.paymentContext['currencyId']
                    ? parseInt(this.paymentContext['currencyId']) : null,
                'partner_id': parseInt(this.paymentContext['partnerId']),
                'reference_prefix': this.paymentContext['referencePrefix']?.toString(),
            });
        }
        return transactionRouteParams;
    },
});
