# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, SUPERUSER_ID
from odoo.tests import Form


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    note = fields.Text('Terms and conditions from SO')
    title = fields.Text('title from SO')
    commitment_date = fields.Datetime('Delivery Date from SO')
    require_materials = fields.Boolean('Require Materials from SO')

    def button_cancel(self):
        if self.state == 'sent':
            sale_order = self.env['sale.order'].search([('name','ilike',self.origin)])
            self.env['bus.bus'].sendone(
                self._cr.dbname + '_' + str(sale_order.partner_id.id),
                {'type': 'purchase_order_notification', 'action':'canceled', "order_id":self.id})
        result = super(PurchaseOrder, self).button_cancel()
        return result

    def _activity_cancel_on_sale(self):
        """ If some PO are cancelled, we need to put an activity on their origin SO (only the open ones). Since a PO can have
            been modified by several SO, when cancelling one PO, many next activities can be schedulded on different SO.
        """
        sale_to_notify_map = False
    
    def button_confirm(self):
        result = super(PurchaseOrder, self).button_confirm()
        # cancel other orders related to same SO
        self.env['bus.bus'].sendone(
            self._cr.dbname + '_' + str(self.partner_id.id),
            {'type': 'purchase_order_notification', 'action':'confirmed', "order_id":self.id})
        purchase_orders = self.env['purchase.order'].search([('id', 'not in', self.ids),('origin','ilike',self.origin)])
        for order in purchase_orders:
            order.sudo().button_cancel()
            self.env['bus.bus'].sendone(
                self._cr.dbname + '_' + str(order.partner_id.id),
                {'type': 'purchase_order_notification', 'action':'calceled', "order_id":order.id})
        self.update_sale_order_lines()
        return result

    def update_sale_order_lines(self):
        # update SO with new PO lines
        sale_order_lines = self.env['sale.order.line'].search([('order_id.name','ilike',self.origin)])
        sale_order_line_ids = []
        for sale_order_line in sale_order_lines:
            sale_order_line_ids.append(sale_order_line.id)
        for purchase_order_line in self.order_line:
            if purchase_order_line.sale_line_id.id not in sale_order_line_ids:
                purchase_order_line.sudo()._sale_service_create_line()
        return True

    def create_full_invoice(self):
        action = self.action_view_invoice()
        invoice_form = Form(self.env['account.move'].with_user(SUPERUSER_ID).with_context(
            action['context']
        ))
        invoice = invoice_form.save()
        invoice.post()
        return invoice.id
    
    def set_state_sent(self):
        self.write({'state': "sent"})
        # add origin SO client to followers
        for order in self.filtered(lambda order: order.partner_id not in order.message_partner_ids):
            sale_order = self.env['sale.order'].search([('name','ilike',order.origin)])
            order.message_subscribe([order.partner_id.id, sale_order.partner_id.id])
            self.env['bus.bus'].sendone(
                self._cr.dbname + '_' + str(sale_order.partner_id.id),
                {'type': 'purchase_order_notification', 'action':'accepted', "order_id":order.id})
        return True
        
    def search_messages(self, domain, fields):
        return  self.env['mail.message'].sudo().search_read(domain,fields)

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _sale_service_create_line(self):
        """ Create sale.order.line from purchase.order.line.
            :param 
            :rtype: dict
        """
        self.ensure_one()

        # compute quantity from PO line UoM
        product_quantity = self.product_qty
        purchase_qty_uom = self.product_uom._compute_quantity(product_quantity, self.product_id.uom_po_id)
        
        sale_order = self.env['sale.order'].sudo().search([('name','ilike', self.order_id.origin)])
        
        fpos = sale_order.fiscal_position_id
        taxes = fpos.map_tax(self.product_id.supplier_taxes_id) if fpos else self.product_id.supplier_taxes_id
        if taxes:
            taxes = taxes.filtered(lambda t: t.company_id.id == self.company_id.id)

        # compute unit price
        price_unit = 0.0
        
        price_unit = self.env['account.tax'].sudo()._fix_tax_included_price_company(self.price_unit, self.product_id.supplier_taxes_id, taxes, self.company_id)
        if sale_order.currency_id and self.currency_id != sale_order.currency_id:
            price_unit = self.currency_id.compute(price_unit, sale_order.currency_id)

        values = {
            'name': '[%s] %s' % (self.product_id.default_code, self.name) if self.product_id.default_code else self.name,
            'product_uom_qty': purchase_qty_uom,
            'product_id': self.product_id.id,
            'product_uom': self.product_id.uom_po_id.id,
            'price_unit': price_unit,
            'tax_id': [(6, 0, taxes.ids)],
            'order_id': sale_order.id,
            'purchase_line_ids': [(6, 0, self.ids)],
        }
        
        return self.env['sale.order.line'].sudo().create(values) 