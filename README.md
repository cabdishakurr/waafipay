# WaafiPay Payment Provider for Odoo 17

## Overview
This module integrates WaafiPay payment gateway with Odoo 17 Community Edition, allowing businesses to accept payments through WaafiPay's payment services.

## Features
- Seamless integration with Odoo's payment system
- Support for multiple payment methods
- Real-time payment status updates
- Detailed transaction reporting

- Secure payment processing
- Test and Production environments

## Installation

1. Clone the repository:
```bash
git clone https://github.com/cabdishakurr/waafipay.git
```

2. Add the module to your Odoo addons path:
```bash
cp -r waafipay /path/to/odoo/addons
```

3. Update the Odoo apps list and install the module:
- Go to Apps menu
- Click on "Update Apps List"
- Search for "WaafiPay"
- Click Install

## Configuration

1. Go to Invoicing/Accounting → Configuration → Payment Providers
2. Create or edit WaafiPay provider
3. Configure the following:
   - Merchant ID
   - API Key
   - Secret Key
   - Environment (Test/Production)
4. Set provider to 'Enabled' status

## Usage

### For Customers
1. Select WaafiPay as payment method during checkout
2. Complete payment through WaafiPay interface
3. Receive confirmation

### For Administrators
1. Monitor transactions in Invoicing/Accounting → Payments
2. View detailed payment reports
3. Process refunds if necessary

## Security
- All sensitive data is encrypted
- PCI DSS compliant
- Implements secure token-based authentication
- Regular security updates

## Support
For support, please contact:
- Email: support@example.com
- GitHub Issues: [Create an issue](https://github.com/cabdishakurr/waafipay/issues)

## License
This module is licensed under LGPL-3.

## Contributing
1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request