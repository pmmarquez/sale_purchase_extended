# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, SUPERUSER_ID
try:
    from xmlrpc import client as xmlrpclib
except ImportError:
    import xmlrpclib

class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _message_post_process_attachments(self, attachments, attachment_ids, message_values):
        new_attachments = []
        if attachments:
            for attachment in attachments:
                if len(attachment) == 2 or len(attachment) == 3:
                    if isinstance(attachment[1], xmlrpclib.Binary):
                        attachment[1] = bytes(attachment[1].data)
                new_attachments.append(attachment)
            attachments = new_attachments
        return super(MailThread, self)._message_post_process_attachments(attachments, attachment_ids, message_values)

    