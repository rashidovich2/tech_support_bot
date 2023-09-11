from __future__ import annotations
from collections import defaultdict
import logging

from db_managing import CustomerData, OperatorData, SupportBotData,\
    TgUserData,  TextMessageData, UserNotFound, PhoneAlreadyExists,\
    CustomerNotFound, MsgNotFound
from airtable_db import PhoneNotFound, find_name_by_phone_test


# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger('busines_logic')


class UserNotFoundOnSite(Exception):
    pass


class PhoneAlreadyBelongsCustomer(Exception):
    pass


class CacheMixin(object):
    __all_objects = defaultdict(dict)

    def __init__(self, key):
        self.__all_objects[self.__class__][key] = self

    @classmethod
    def get(cls, key):
        if key in cls.__all_objects[cls]:
            object_ = cls.__all_objects[cls][key]
            if object_ is not None:
                return object_
        return cls(key)


class SupportBot():
    def __init__(self):
        self.support_bot_data = SupportBotData()

    def add_tg_user(self, tg_id: int, tg_username: int) -> None:
        self.support_bot_data.add_tg_user(
          tg_id=tg_id,
          tg_username=tg_username
        )

    def add_operator(self, tg_id: int):
        self.support_bot_data.add_operator(
          tg_id=tg_id
        )

    def add_customer(self, tg_id: int, phone: str) -> Customer:
        """_summary_

        Args:
            tg_id (int): _description_
            phone (str): _description_

        Raises:
            UserNotFoundOnSite: Юзер не зарегистрирован на сайте
            PhoneAlreadyBelongsCustomer:
                Уже есть другой пользователь с этим номером

        Returns:
            Customer: _description_
        """
        try:
            name = find_name_by_phone_test(phone=phone)  # test !!!
        except PhoneNotFound:
            raise UserNotFoundOnSite('phone not found')

        try:
            customer_id = self.support_bot_data.add_customer(tg_id, phone)
            customer = Customer(customer_id)
        except PhoneAlreadyExists:
            customer = self.get_customer_by_tg_id(tg_id)
            if not customer:
                raise PhoneAlreadyBelongsCustomer()

        customer.change_first_name(name)
        return customer

    def add_textmessage(self, tg_id: int, support_chat_message_id: int):
        self.support_bot_data.add_message(
            tg_id=tg_id,
            support_chat_message_id=support_chat_message_id
        )

    def get_customer_list(self) -> list:
        return self.support_bot_data.get_customer_list()

    def get_tg_users(self) -> list:
        """Returning not customers tg ids"""
        return self.support_bot_data.get_tg_users()

    def get_ban_list(self) -> list:
        return self.support_bot_data.get_ban_list()

    def get_textmessage_by(
                self, support_chat_message_id: int) -> TextMessage | None:
        try:
            textmsg_id = self.support_bot_data.get_textmessage_id(
                support_chat_message_id=support_chat_message_id
            )
            return TextMessage.get(textmsg_id)
        except MsgNotFound:
            return None

    def get_customer_by_tg_id(self, tg_id: int) -> Customer | None:
        try:
            customer_id = self.support_bot_data.get_customer_id(tg_id)
            return Customer.get(customer_id)
        except CustomerNotFound:
            log.error('customer not found')
            return None
        except UserNotFound:
            log.error('tg_id not found')
            return None


class TgUser(CacheMixin):
    def __init__(self, tg_id: int):
        super(TgUser, self).__init__(key=tg_id)
        self.tg_id = tg_id
        self.tg_data = TgUserData(tg_id)

    def get_tg_id(self) -> int:
        return self.tg_id

    def get_username(self) -> str:
        username = self.tg_data.get_tg_username()
        return self.get_tg_id() if not username else username

    def is_banned(self) -> bool:
        return self.tg_data.is_banned()


class Operator(TgUser):
    def __init__(self, tg_id: int):
        super(Operator, self).__init__(tg_id=tg_id)

        self.operator_data = OperatorData()

    def get_tg_id(self):
        return self.operator_data.get_tg_id()

    @staticmethod
    def ban(tg_id: int) -> None:
        try:
            OperatorData.ban(tg_id)
            log.info(f'tg_user going to the ban: {tg_id}')
        except UserNotFound:
            log.error(f'tg_user_not_found: {tg_id}')

    @staticmethod
    def unban(tg_id: int) -> None:
        try:
            OperatorData.unban(tg_id)
            log.info(f'tg_user was unbaned: {tg_id}')
        except UserNotFound:
            log.error(f'tg_user_not_found: {tg_id}')


class Customer(CacheMixin):
    def __init__(self, gameuser_id: int):
        self.gameuser_id = gameuser_id
        self.customer_data = CustomerData(self.gameuser_id)

    def get_tg_id(self) -> int:
        return self.customer_data.get_tg_id()

    def get_first_name(self) -> str:
        return self.customer_data.get_first_name()

    def get_last_name(self) -> str:
        return self.customer_data.get_last_name()

    def change_last_name(self, new_last_name: str) -> None:
        self.customer_data.change_last_name(
            new_last_name=new_last_name
        )
        # update data from DB
        self.customer_data = CustomerData(self.gameuser_id)

    def change_first_name(self, new_first_name: str) -> None:
        self.customer_data.change_first_name(
            new_first_name=new_first_name
        )
        # update data from DB
        self.customer_data = CustomerData(self.gameuser_id)


class TextMessage(CacheMixin):
    def __init__(self, text_message_id: int):
        self.text_message_id = text_message_id
        self.text_message_data = TextMessageData(self.text_message_id)

    def get_tg_id(self) -> int:
        return self.text_message_data.get_tg_id()

    def get_tg_user(self) -> TgUser:
        return TgUser.get(self.get_tg_id())

    def get_support_chat_message_id(self) -> str:
        return self.text_message_data.get_support_chat_message_id()

    def is_answered(self) -> bool:
        return self.text_message_data.is_answered()

    def mark_answered(self) -> None:
        self.text_message_data.mark_answered()

    def mark_unanswered(self) -> None:
        self.text_message_data.mark_unanswered()
