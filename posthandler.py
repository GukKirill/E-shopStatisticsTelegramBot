import datetime
import imaplib
import email
from email import utils
import base64
from texthandler import handle_new_data
from dbhandler import FromMailDBHandler
import os
from dotenv import load_dotenv

load_dotenv()
SHOP_EMAIL = os.getenv('SHOP_EMAIL')


class MailHandler:
    def __init__(self, login: str, password: str, domain=None):
        self.__login = login
        self.__password = password
        if domain:
            self.imap_server = domain
        else:
            self.imap_server = self.check_imap_server()
        self.mailbox = None
        self.db = FromMailDBHandler()
        self.last_checked_uid = self.db.get_mail_last_uid()
        self.uid_list = list()

    def check_imap_server(self) -> str:
        if '@' in self.__login and self.__login.count('@') == 1:
            at_index = self.__login.index('@')
            domain = self.__login[at_index+1:]
            if '.' in domain[1:] and domain[1:].count('.') == 1:
                domain_test = domain.replace('.', '')
                if domain_test.isalpha():
                    return 'imap.'+domain

    def login_mailbox(self) -> None:
        if self.imap_server:
            self.mailbox = imaplib.IMAP4_SSL(self.imap_server)    # need checking!!!!
            self.mailbox.login(self.__login, self.__password)

    def get_inbox_uid_list(self) -> None:
        self.mailbox.select('INBOX')
        res, self.uid_list = self.mailbox.uid('search', 'ALL')
        self.uid_list = self.uid_list[0].split()

    def handle_new_messages(self) -> None:
        self.login_mailbox()
        self.get_inbox_uid_list()
        for next_id in self.uid_list:
            next_int_id = int(next_id)
            if next_int_id > self.last_checked_uid:
                res, msg_data = self.mailbox.uid('fetch', next_id, '(RFC822)')
                msg = email.message_from_bytes(msg_data[0][1])
                if msg["Return-path"] == SHOP_EMAIL:
                    msg_datetime = email.utils.parsedate_tz(msg["Date"])
                    msg_date = str(datetime.date(msg_datetime[0], msg_datetime[1], msg_datetime[2]))
                    for part in msg.walk():
                        if part.get_content_maintype() == 'text' and part.get_content_subtype() == 'html':
                            mail_text = base64.b64decode(part.get_payload()).decode()
                            if 'В интернет-магазине сделан заказ.' in mail_text:
                                handled_data = handle_new_data(mail_text, msg_date)
                                for data in handled_data:
                                    self.db.insert_new_data(*data)

                self.db.set_mail_last_uid(next_int_id)
                self.last_checked_uid = next_int_id
        self.db.close_connection()
