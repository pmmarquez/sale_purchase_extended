# -*- coding: utf-8 -*-

# from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
# from odoo.tools import float_compare

class SaleOrder(models.Model):
    _inherit = 'sale.order'


    @api.depends('order_line.invoice_lines')
    def _get_invoiced(self):
        # The invoice_ids are obtained thanks to the invoice lines of the SO
        # lines, and we also search for possible refunds created directly from
        # existing invoices. This is necessary since such a refund is not
        # directly linked to the SO.
        for order in self:
            # invoices = order.order_line.invoice_lines.move_id.sudo().filtered(lambda r: r.type in ('out_invoice', 'out_refund'))
            invoices = self.env['account.move'].sudo().search([('invoice_origin','ilike',self.name)])
            order.invoice_ids = invoices
            order.invoice_count = len(invoices)

    def _activity_cancel_on_purchase(self):
        """ If some SO are cancelled, we need to put an activity on their generated purchase. If sale lines of
            different sale orders impact different purchase, we only want one activity to be attached.
        """
        purchase_to_notify_map = {}  # map PO -> recordset of SOL as {purchase.order: set(sale.orde.liner)}

        purchase_order_lines = self.env['purchase.order.line'].search([('sale_line_id', 'in', self.mapped('order_line').ids), ('state', '!=', 'cancel')])
        for purchase_line in purchase_order_lines:
            purchase_to_notify_map.setdefault(purchase_line.order_id, self.env['sale.order.line'])
            purchase_to_notify_map[purchase_line.order_id] |= purchase_line.sale_line_id

        for purchase_order, sale_order_lines in purchase_to_notify_map.items():
            # purchase_order.activity_schedule_with_view('mail.mail_activity_data_warning',
            #     user_id=purchase_order.user_id.id or self.env.uid,
            #     views_or_xmlid='sale_purchase.exception_purchase_on_sale_cancellation',
            #     render_context={
            #         'sale_orders': sale_order_lines.mapped('order_id'),
            #         'sale_order_lines': sale_order_lines,
            # })
            # [ADD] cancel all related PO
            purchase_order.sudo().button_cancel()

    def create_full_invoice(self):
        context = {
            'active_model': 'sale.order',
            'active_ids': [self.id],
            'active_id': self.id,
        }
        payment = self.env['sale.advance.payment.inv'].with_context(context).create({
            'advance_payment_method': 'delivered'
        })
        payment.create_invoices()
        for inv in self.invoice_ids:
            if inv.state == 'draft':
                inv.post()
                invoice = inv
        return invoice.id

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _purchase_service_create(self, quantity=False):
        """ On Sales Order confirmation, some lines (services ones) can create a purchase order line and maybe a purchase order.
            If a line should create a RFQ, it will check for existing PO. If no one is find, the SO line will create one, then adds
            a new PO line. The created purchase order line will be linked to the SO line.
            :param quantity: the quantity to force on the PO line, expressed in SO line UoM
        """
        PurchaseOrder = self.env['purchase.order']
        supplier_po_map = {}
        sale_line_purchase_map = {}
        for line in self:
            line = line.with_context(force_company=line.company_id.id)
            # determine vendor of the order (take the first matching company and product)
            suppliers = line.product_id.with_context(force_company=line.company_id.id)._select_seller(
                quantity=line.product_uom_qty, uom_id=line.product_uom)
            if not suppliers:
                raise UserError(_("There is no vendor associated to the product %s. Please define a vendor for this product.") % (line.product_id.display_name,))
            supplierinfo = suppliers[0]
            partner_supplier = supplierinfo.name  # yes, this field is not explicit .... it is a res.partner !

            # Allways generate PO to every product supplier for this SO
            sellers = line.product_id.seller_ids
            for seller in sellers:
                # not create if allready exist
                purchase_order_count = self.env['purchase.order'].search_count([('partner_id', '=', seller.id),('origin','ilike',self.order_id.name)])
                if  purchase_order_count == 0:
                    values = line._purchase_service_prepare_order_values(seller)
                    purchase_order = PurchaseOrder.create(values)
                    values = line._purchase_service_prepare_line_values(purchase_order, quantity=quantity)
                    purchase_line = line.env['purchase.order.line'].create(values)

            # link the generated purchase to the SO line
            sale_line_purchase_map.setdefault(line, line.env['purchase.order.line'])
            sale_line_purchase_map[line] |= purchase_line
        return sale_line_purchase_map
