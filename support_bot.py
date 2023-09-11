import logging
import typing

from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils import callback_data, exceptions
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types.message import ContentType

# Import modules of this project
from config import API_TOKEN, SUPPORT_CHAT_ID
from business_logic import Operator, SupportBot, TextMessage, \
    UserNotFoundOnSite, PhoneAlreadyBelongsCustomer
from texts_for_replay import instruction_text, phone_found_text, \
    phone_not_found_text, help_text, instruction_how_use_support, \
    phone_already_belong_customer_text, help_for_opertor_text

# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger('support_bot')

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())

# Sructure of callback buttons
button_cb = callback_data.CallbackData(
    'btn', 'question_name', 'answer', 'data')

# Initialize business logic
support_bot = SupportBot()


#  -------------------------------------------------------------- ВХОД ТГ ЮЗЕРА
def get_empty_keyboard():
    return types.ReplyKeyboardMarkup(resize_keyboard=True)


def get_phone_keyboard():
    keyboard = types.ReplyKeyboardMarkup(
        one_time_keyboard=True,
        resize_keyboard=True
    )
    keyboard.add(types.KeyboardButton(
        text='Отправить свой телефон 📞',
        request_contact=True)
    )
    return keyboard


class CustomerState(StatesGroup):
    waiting_for_contact = State()


@dp.message_handler(
    lambda message: message.chat.type == 'private',
    commands=['start'], state="*")
async def start_command(message: types.Message, state: FSMContext):
    log.info('start command from: %r', message.from_user.id)

    support_bot.add_tg_user(
        tg_id=message.from_user.id,
        tg_username=message.from_user.username
    )

    await CustomerState.waiting_for_contact.set()
    await message.answer(
        text=instruction_text,
        reply_markup=get_phone_keyboard())


@dp.message_handler(
    lambda message: message.chat.type == 'private',
    content_types=ContentType.CONTACT,
    state=CustomerState.waiting_for_contact)
async def new_contact(message: types.Message, state: FSMContext):
    log.info('new_contact from: %r', message.from_user.id)

    phone = message.contact.phone_number.strip('+')
    try:
        customer = support_bot.add_customer(
            tg_id=message.from_user.id,
            phone=phone
        )
    except UserNotFoundOnSite:
        await message.answer(
            text=phone_not_found_text,
            reply_markup=get_phone_keyboard()
        )
    except PhoneAlreadyBelongsCustomer:
        await message.answer(
            text=phone_already_belong_customer_text,
            reply_markup=get_phone_keyboard()
        )

    await message.reply(
        text=phone_found_text,
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.finish()
    await message.answer(
        text=f'Здравствуйте, {customer.get_first_name()}!'
    )
    await message.answer(
        text=instruction_how_use_support
    )


@dp.message_handler(
    lambda message: message.chat.type == 'private',
    commands=['help'], state="*")
async def send_help(message: types.Message, state: FSMContext):
    log.info('help command from: %r', message.from_user.id)
    await message.answer(
        text=help_text,
        reply_markup=types.ReplyKeyboardRemove()
    )


@dp.message_handler(
    lambda message: message.chat.id == SUPPORT_CHAT_ID,
    commands=['help'], state="*")
async def send_help_to_operator(message: types.Message, state: FSMContext):
    log.info('send_help_to_operator: %r', message.from_user.id)
    await message.answer(
        text=help_for_opertor_text,
        reply_markup=types.ReplyKeyboardRemove()
    )


#  ------------------------------------------------------------ ПРИЕМ ОБРАЩЕНИЙ
answered_button = 'Отвечено ✔️'
unanswered_button = 'Не отвечено❗'
ban_button = 'Бан'
unban_button = '🚫 Забанен'


def make_inline_keyboard(
        question_name: str,
        answers: list,
        data=0) -> types.InlineKeyboardMarkup:
    """Возвращает клавиатуру для сообщений"""
    if not answers:
        return None

    keyboard = types.InlineKeyboardMarkup()
    row = []
    for answer in answers:  # make a botton for every answer
        cb_data = button_cb.new(
            question_name=question_name,
            answer=answer,
            data=data)
        row.append(types.InlineKeyboardButton(answer,
                                              callback_data=cb_data))
    if len(row) <= 2:
        keyboard.row(*row)
    else:
        for button in row:
            keyboard.row(button)

    return keyboard


def keyboard_for_message_in_support_chat(
        answers: list) -> types.InlineKeyboardMarkup:
    return make_inline_keyboard(
        question_name='customer_textmessage', answers=answers, data=0
    )


@dp.message_handler(
    lambda message: message.chat.type == 'private',
    content_types=[ContentType.TEXT, ContentType.PHOTO],
    state='*')
async def new_text_message(message: types.Message, state: FSMContext):
    if message.from_user.id in support_bot.get_ban_list():
        return
    log.info('new_text_message_for_support from: %r', message.from_user.id)
    if customer := support_bot.get_customer_by_tg_id(message.from_user.id):
        signature = (
            f'<b>От: 🧑 {customer.get_first_name()} '
            f'{customer.get_last_name()}</b>\n'
        )
    else:
        signature = (
            f'<b>От: 🐨 {message.from_user.full_name} '
            f'{message.from_user.id}</b>\n'
        )

    if message.content_type == ContentType.TEXT:
        support_chat_msg = await bot.send_message(
            chat_id=SUPPORT_CHAT_ID,
            text=signature + message.text,
            reply_markup=keyboard_for_message_in_support_chat(
                [ban_button, unanswered_button])
        )
    if message.content_type == ContentType.PHOTO:
        text = signature + str(message.caption) if message.caption else signature
        support_chat_msg = await bot.send_photo(
            chat_id=SUPPORT_CHAT_ID,
            photo=message.photo[0]['file_id'],
            caption=text,
            reply_markup=keyboard_for_message_in_support_chat(
                [ban_button, unanswered_button])
        )

    support_bot.add_textmessage(
        tg_id=message.from_user.id,
        support_chat_message_id=support_chat_msg.message_id
    )


#  --------------------------------------------------------- ОТВЕТ НА ОБРАЩЕНИЕ
def get_keyboard_for_current_message(
        textmessage: TextMessage) -> types.InlineKeyboardMarkup:
    """Возвращает актуальную клавиатуру
        для этого сообщения и пользователя

    Returns:
        types.InlineKeyboardMarkup: _description_
    """
    tg_user = textmessage.get_tg_user()

    first_button = unban_button if tg_user.is_banned() else ban_button
    if textmessage.is_answered():
        second_button = answered_button
    else:
        second_button = unanswered_button

    return keyboard_for_message_in_support_chat([first_button, second_button])


@dp.message_handler(
    lambda message: 'reply_to_message' in message,
    lambda message: message.chat.id == SUPPORT_CHAT_ID,
    content_types=[ContentType.PHOTO, ContentType.TEXT])
async def replay_on_message(message: types.Message, state: FSMContext):
    log.info('replay_on_message from: %r', message.from_user.id)
    msg_id = message.reply_to_message.message_id
    textmessage = support_bot.get_textmessage_by(
        support_chat_message_id=msg_id
    )
    if not textmessage:
        await message.reply(text='Не удалось отправить')
        return

    # send answer to customer
    if message.content_type == ContentType.TEXT:
        await bot.send_message(
            chat_id=textmessage.get_tg_id(),
            text=message.text
        )
    if message.content_type == ContentType.PHOTO:
        await bot.send_photo(
            chat_id=textmessage.get_tg_id(),
            photo=message.photo[0]['file_id'],
            caption=message.caption
        )
    textmessage.mark_answered()

    # edit buttons under message in support chat
    try:
        await bot.edit_message_reply_markup(
            chat_id=SUPPORT_CHAT_ID,
            message_id=msg_id,
            reply_markup=get_keyboard_for_current_message(
                textmessage=textmessage
            )
        )
    except exceptions.MessageNotModified:
        pass
    except exceptions.MessageToEditNotFound:
        log.warning('message was deleted')


@dp.callback_query_handler(
    button_cb.filter(
        question_name=['customer_textmessage'],
        answer=[ban_button, unban_button]
    ),
    state='*')
async def callback_ban(
        query: types.CallbackQuery,
        callback_data: typing.Dict[str, str],
        state: FSMContext):
    log.info('Got this callback data: %r', callback_data)

    textmessage = support_bot.get_textmessage_by(
        support_chat_message_id=query.message.message_id
    )
    tg_id = textmessage.get_tg_id()

    if callback_data['answer'] == ban_button:
        Operator.ban(tg_id=tg_id)
    elif callback_data['answer'] == unban_button:
        Operator.unban(tg_id=tg_id)

    await query.message.edit_reply_markup(
        reply_markup=get_keyboard_for_current_message(
            textmessage=textmessage
        )
    )
    await query.answer()


@dp.callback_query_handler(
    button_cb.filter(
        question_name=['customer_textmessage'],
        answer=[answered_button, unanswered_button]
    ),
    state='*')
async def callback_answered_button(
        query: types.CallbackQuery,
        callback_data: typing.Dict[str, str],
        state: FSMContext):
    log.info('Got this callback data: %r', callback_data)

    textmessage = support_bot.get_textmessage_by(
        support_chat_message_id=query.message.message_id
    )

    if callback_data['answer'] == answered_button:
        textmessage.mark_unanswered()
    elif callback_data['answer'] == unanswered_button:
        textmessage.mark_answered()

    await query.message.edit_reply_markup(
        reply_markup=get_keyboard_for_current_message(
            textmessage=textmessage
        )
    )
    await query.answer()


@dp.message_handler(
    lambda message: message.chat.type == 'private',
    content_types=ContentType.ANY,
    state='*')
async def other_message_types(message: types.Message, state: FSMContext):
    if message.from_user.id in support_bot.get_ban_list():
        return
    log.info('other_message_types from: %r', message.from_user.id)
    await message.reply(
        text='Вы можете отправлять только текст или фото',
        reply_markup=types.ReplyKeyboardRemove())

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=False)
