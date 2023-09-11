import psycopg2
from config import DB_HOST, DB_NAME, DB_USER, DB_PASS, DB_PORT

db_config = {'host': DB_HOST,
             'dbname': DB_NAME,
             'user': DB_USER,
             'password': DB_PASS,
             'port': DB_PORT}


class UserNotFound(Exception):
    pass


class CustomerNotFound(Exception):
    pass


class MsgAlreadyExists(Exception):
    pass


class MsgNotFound(Exception):
    pass


class PhoneAlreadyExists(Exception):
    pass


class SupportBotData:
    @staticmethod
    def add_tg_user(tg_id: int, tg_username: str) -> None:
        connection = psycopg2.connect(**db_config)
        with connection.cursor() as cursor:
            insert_values = (tg_id, tg_username)
            insert_script = '''INSERT INTO tg_user (tg_id, tg_username)
                                VALUES (%s, %s)
                                ON CONFLICT (tg_id)
                                DO UPDATE
                                SET tg_username = EXCLUDED.tg_username;'''
            cursor.execute(insert_script, insert_values)
        connection.commit()
        connection.close()

    @staticmethod
    def does_user_exist(tg_id: int) -> bool:
        connection = psycopg2.connect(**db_config)
        with connection.cursor() as cursor:
            select_script = '''
                    SELECT exists(
                       SELECT tg_id
                       FROM tg_user
                       WHERE tg_id = %s);'''
            cursor.execute(select_script, (tg_id,))
            exists, = cursor.fetchone()
        connection.commit()
        connection.close()
        return exists

    @staticmethod
    def add_operator(tg_id: int) -> None:
        connection = psycopg2.connect(**db_config)
        with connection.cursor() as cursor:
            insert_values = (tg_id,)
            insert_script = '''INSERT INTO operator (tg_id) VALUES (%s)
                                ON CONFLICT (tg_id) DO NOTHING;'''
            cursor.execute(insert_script, insert_values)
        connection.commit()
        connection.close()

    @staticmethod
    def add_customer(tg_id: int, phone: str) -> int:
        if SupportBotData.does_phone_exist(phone):
            raise PhoneAlreadyExists(
                'db: customer with given phone number already exists')
        connection = psycopg2.connect(**db_config)
        with connection.cursor() as cursor:
            insert_values = (tg_id, phone)
            insert_script = '''
                    INSERT INTO customer (tg_id, phone)
                    VALUES (%s, %s)
                    ON CONFLICT (tg_id)
                    DO UPDATE
                    SET phone = EXCLUDED.phone
                    RETURNING customer_id;'''
            cursor.execute(insert_script, insert_values)
            customer_id, = cursor.fetchone()
        connection.commit()
        connection.close()
        return customer_id

    @staticmethod
    def does_phone_exist(phone: str) -> bool:
        connection = psycopg2.connect(**db_config)
        with connection.cursor() as cursor:
            select_script = '''
                SELECT exists(
                   SELECT phone
                   FROM customer
                   WHERE phone = %s);'''
            cursor.execute(select_script, (phone,))
            exists, = cursor.fetchone()
        connection.commit()
        connection.close()
        return exists

    @staticmethod
    def add_message(tg_id: int, support_chat_message_id: int) -> None:
        if SupportBotData.does_message_exist(support_chat_message_id):
            raise MsgAlreadyExists('db: support_chat_message already exists')
        connection = psycopg2.connect(**db_config)
        with connection.cursor() as cursor:
            insert_values = (tg_id, support_chat_message_id)
            insert_script = '''
                    INSERT INTO message (tg_id, support_chat_message_id)
                    VALUES (%s, %s);'''
            cursor.execute(insert_script, insert_values)
        connection.commit()
        connection.close()

    @staticmethod
    def does_message_exist(support_chat_message_id: int) -> bool:
        connection = psycopg2.connect(**db_config)
        with connection.cursor() as cursor:
            select_script = '''SELECT exists(
                                   SELECT support_chat_message_id
                                   FROM message
                                   WHERE support_chat_message_id = %s);'''
            cursor.execute(select_script, (support_chat_message_id,))
            exists, = cursor.fetchone()
        connection.commit()
        connection.close()
        return exists

    @staticmethod
    def get_textmessage_id(support_chat_message_id: int) -> int:
        if SupportBotData.does_message_exist(support_chat_message_id):
            connection = psycopg2.connect(**db_config)
            with connection.cursor() as cursor:
                insert_script = '''
                    SELECT text_message_id
                    FROM message
                    WHERE support_chat_message_id = %s;'''
                cursor.execute(insert_script, (support_chat_message_id,))
                text_message_id, = cursor.fetchone()
            connection.commit()
            connection.close()
            return text_message_id
        else:
            raise MsgNotFound('db: support_chat_message not found')

    @staticmethod
    def get_customer_id(tg_id: int) -> int:
        if not SupportBotData.does_user_exist(tg_id):
            raise UserNotFound('db: tg_user not found')
        connection = psycopg2.connect(**db_config)
        with connection.cursor() as cursor:
            insert_script = '''
                    SELECT customer_id
                    FROM customer
                    WHERE tg_id = %s;'''
            cursor.execute(insert_script, (tg_id,))
            if result := cursor.fetchone():
                customer_id, = result
            else:
                raise CustomerNotFound('db: customer_id not found')
        connection.commit()
        connection.close()
        return customer_id

    @staticmethod
    def get_customer_list() -> list:
        connection = psycopg2.connect(**db_config)
        with connection.cursor() as cursor:
            select_script = '''SELECT tg_user.tg_id FROM tg_user
                                INNER JOIN customer
                                ON tg_user.tg_id = customer.tg_id
                                WHERE tg_user.is_banned = FALSE;'''
            cursor.execute(select_script)
            try:
                id_list = cursor.fetchall()
            except TypeError:
                id_list = []
        connection.commit()
        connection.close()
        return [id_tuple[0] for id_tuple in id_list]

    @staticmethod
    def get_tg_users() -> list:
        connection = psycopg2.connect(**db_config)
        with connection.cursor() as cursor:
            select_script = '''SELECT tg_id FROM tg_user
                                WHERE is_banned = FALSE
                                EXCEPT SELECT tg_id FROM customer;'''
            cursor.execute(select_script)
            try:
                id_list = cursor.fetchall()
            except TypeError:
                id_list = []
        connection.commit()
        connection.close()
        return [id_tuple[0] for id_tuple in id_list]

    @staticmethod
    def get_ban_list() -> list:
        connection = psycopg2.connect(**db_config)
        with connection.cursor() as cursor:
            select_script = '''SELECT tg_id FROM tg_user
                                WHERE is_banned = TRUE;'''
            cursor.execute(select_script)
            try:
                id_list = cursor.fetchall()
            except TypeError:
                id_list = []
        connection.commit()
        connection.close()
        return [id_tuple[0] for id_tuple in id_list]


class TgUserData:
    def __init__(self, tg_id: int):
        self._tg_id = tg_id

        connection = psycopg2.connect(**db_config)
        with connection.cursor() as cursor:
            select_script = '''SELECT tg_username, is_banned
                                FROM tg_user
                                WHERE tg_id = %s;'''
            cursor.execute(select_script, (tg_id,))
            select_username, is_banned = cursor.fetchone()
        connection.commit()
        connection.close()

        self._tg_username = select_username
        self._is_banned = is_banned

    def get_tg_id(self) -> int:
        return self._tg_id

    def get_tg_username(self) -> str:
        return self._tg_username

    def is_banned(self) -> bool:
        connection = psycopg2.connect(**db_config)
        with connection.cursor() as cursor:
            select_script = '''
                        SELECT is_banned
                        FROM tg_user
                        WHERE tg_id = %s;'''
            cursor.execute(select_script, (self._tg_id,))
            is_banned, = cursor.fetchone()
        connection.commit()
        connection.close()
        return is_banned


class OperatorData:
    def __init__(self, operator_id: int):
        self._operator_id = operator_id

        connection = psycopg2.connect(**db_config)
        with connection.cursor() as cursor:
            select_script = '''SELECT tg_id FROM operator
                                WHERE operator_id = %s;'''
            cursor.execute(select_script, (operator_id,))
            tg_id, = cursor.fetchone()
        connection.commit()
        connection.close()

        self._tg_id = tg_id

    def get_tg_id(self):
        return self._tg_id

    @staticmethod
    def ban(tg_id: int) -> None:
        if SupportBotData.does_user_exist(tg_id):
            connection = psycopg2.connect(**db_config)
            with connection.cursor() as cursor:
                update_script = '''UPDATE tg_user
                                    SET is_banned = TRUE
                                    WHERE tg_id = %s;'''
                cursor.execute(update_script, (tg_id,))
            connection.commit()
            connection.close()
        else:
            raise UserNotFound('db: tg_user not found')

    @staticmethod
    def unban(tg_id: int) -> None:
        if SupportBotData.does_user_exist(tg_id):
            connection = psycopg2.connect(**db_config)
            with connection.cursor() as cursor:
                update_script = '''UPDATE tg_user
                                    SET is_banned = FALSE
                                    WHERE tg_id = %s;'''
                cursor.execute(update_script, (tg_id,))
            connection.commit()
            connection.close()
        else:
            raise UserNotFound('db: tg_user not found')


class CustomerData:
    def __init__(self, customer_id: int):
        self._customer_id = customer_id

        connection = psycopg2.connect(**db_config)
        with connection.cursor() as cursor:
            select_script = '''
                SELECT tg_id, phone, first_name, last_name
                FROM customer
                WHERE customer_id = %s;'''
            cursor.execute(select_script, (customer_id,))
            tg_id, phone, first_name, last_name = cursor.fetchone()
        connection.commit()
        connection.close()

        self._tg_id = tg_id
        self._phone = phone
        self._first_name = first_name
        self._last_name = last_name

    def get_tg_id(self) -> int:
        return self._tg_id

    def get_phone(self) -> str:
        return self._phone

    def get_first_name(self) -> str:
        return self._first_name

    def get_last_name(self) -> str:
        return self._last_name

    def change_first_name(self, new_first_name: str) -> None:
        connection = psycopg2.connect(**db_config)
        with connection.cursor() as cursor:
            insert_values = (new_first_name, self._customer_id)
            update_script = '''UPDATE customer
                                SET first_name = %s
                                WHERE customer_id = %s;'''
            cursor.execute(update_script, insert_values)
        connection.commit()
        connection.close()

    def change_last_name(self, new_last_name: str) -> None:
        connection = psycopg2.connect(**db_config)
        with connection.cursor() as cursor:
            insert_values = (new_last_name, self._customer_id)
            update_script = '''UPDATE customer
                                SET last_name = %s
                                WHERE customer_id = %s;'''
            cursor.execute(update_script, insert_values)
        connection.commit()
        connection.close()


class TextMessageData:
    def __init__(self, text_message_id: int):
        self._text_message_id = text_message_id

        connection = psycopg2.connect(**db_config)
        with connection.cursor() as cursor:
            select_script = '''SELECT tg_id, support_chat_message_id,
                                        is_answered
                                FROM message
                                WHERE text_message_id = %s;'''
            cursor.execute(select_script, (text_message_id,))
            tg_id, support_chat_message_id, is_answered = cursor.fetchone()
        connection.commit()
        connection.close()

        self._tg_id = tg_id
        self._support_chat_message_id = support_chat_message_id
        self._is_answered = is_answered

    def get_tg_id(self) -> int:
        return self._tg_id

    def get_support_chat_message_id(self) -> str:
        return self._support_chat_message_id

    def is_answered(self) -> bool:
        connection = psycopg2.connect(**db_config)
        with connection.cursor() as cursor:
            select_script = '''
                SELECT is_answered
                FROM message
                WHERE text_message_id = %s;'''
            cursor.execute(select_script, (self._text_message_id,))
            is_answered, = cursor.fetchone()
        connection.commit()
        connection.close()
        return is_answered

    def mark_answered(self) -> None:
        connection = psycopg2.connect(**db_config)
        with connection.cursor() as cursor:
            update_script = '''UPDATE message
                                SET is_answered = TRUE
                                WHERE text_message_id = %s;'''
            cursor.execute(update_script, (self._text_message_id,))
        connection.commit()
        connection.close()

    def mark_unanswered(self) -> None:
        connection = psycopg2.connect(**db_config)
        with connection.cursor() as cursor:
            update_script = '''UPDATE message
                                SET is_answered = FALSE
                                WHERE text_message_id = %s;'''
            cursor.execute(update_script, (self._text_message_id,))
        connection.commit()
        connection.close()
