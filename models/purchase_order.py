# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def button_confirm(self):
        result = super(PurchaseOrder, self).button_confirm()
        # cancel other orders related to same SO
        purchase_orders = self.env['purchase.order'].search([('id', 'not in', self.ids),('origin','ilike',self.origin)])
        for order in purchase_orders:
            order.sudo().button_cancel()
        return result    
        