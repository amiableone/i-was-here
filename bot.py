import asyncio
import json
import os
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

DATA_FILE = Path("data.json")


def load_data() -> dict:
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text())
    return {"last_visitor": None, "users": {}}


def save_data(data: dict) -> None:
    DATA_FILE.write_text(json.dumps(data))


def register_user(chat_id: int) -> None:
    data = load_data()
    data["users"][str(chat_id)] = True
    save_data(data)


class Form(StatesGroup):
    waiting_for_message = State()


dp = Dispatcher()

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="I was here")]],
    resize_keyboard=True,
)

skip_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Skip")]],
    resize_keyboard=True,
)


def last_visitor_text() -> str:
    data = load_data()
    visitor = data.get("last_visitor")
    if not visitor:
        return "No one has been here yet. Be the first!"
    full_name = visitor["full_name"]
    user_id = visitor["user_id"]
    if visitor.get("message"):
        return f'<a href="tg://user?id={user_id}">{full_name}</a> said: "{visitor["message"]}"'
    return f'<a href="tg://user?id={user_id}">{full_name}</a> was here'


async def broadcast(bot: Bot, exclude_chat_id: int) -> None:
    data = load_data()
    text = last_visitor_text()
    chat_ids = [int(cid) for cid in data["users"] if int(cid) != exclude_chat_id]
    await asyncio.gather(
        *(bot.send_message(cid, text, parse_mode="HTML") for cid in chat_ids),
        return_exceptions=True,
    )


@dp.message(Command("start"))
async def cmd_start(message: Message) -> None:
    register_user(message.chat.id)
    await message.answer(last_visitor_text(), parse_mode="HTML", reply_markup=main_keyboard)


@dp.message(F.text == "I was here")
@dp.message(Command("i_was_here"))
async def cmd_i_was_here(message: Message, state: FSMContext) -> None:
    data = load_data()
    data["last_visitor"] = {
        "full_name": message.from_user.full_name,
        "user_id": message.from_user.id,
        "message": None,
    }
    save_data(data)
    await state.set_state(Form.waiting_for_message)
    await message.answer("Want to leave a message?", reply_markup=skip_keyboard)


@dp.message(Form.waiting_for_message, F.text == "Skip")
async def skip_message(message: Message, state: FSMContext, bot: Bot) -> None:
    await state.clear()
    await message.answer(last_visitor_text(), parse_mode="HTML", reply_markup=main_keyboard)
    await broadcast(bot, exclude_chat_id=message.chat.id)


@dp.message(Form.waiting_for_message)
async def process_message(message: Message, state: FSMContext, bot: Bot) -> None:
    data = load_data()
    data["last_visitor"]["message"] = message.text
    save_data(data)
    await state.clear()
    await message.answer(last_visitor_text(), parse_mode="HTML", reply_markup=main_keyboard)
    await broadcast(bot, exclude_chat_id=message.chat.id)


async def main() -> None:
    bot = Bot(token=os.environ["BOT_TOKEN"])
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
