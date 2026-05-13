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
    return {}


def save_data(data: dict) -> None:
    DATA_FILE.write_text(json.dumps(data))


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
    if not data:
        return "No one has been here yet. Be the first!"
    full_name = data["full_name"]
    user_id = data["user_id"]
    if data.get("message"):
        return f'<a href="tg://user?id={user_id}">{full_name}</a> said: "{data["message"]}"'
    return f'<a href="tg://user?id={user_id}">{full_name}</a> was here'


@dp.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(last_visitor_text(), parse_mode="HTML", reply_markup=main_keyboard)


@dp.message(F.text == "I was here")
@dp.message(Command("i_was_here"))
async def cmd_i_was_here(message: Message, state: FSMContext) -> None:
    save_data({
        "full_name": message.from_user.full_name,
        "user_id": message.from_user.id,
        "message": None,
    })
    await state.set_state(Form.waiting_for_message)
    await message.answer("Want to leave a message?", reply_markup=skip_keyboard)


@dp.message(Form.waiting_for_message, F.text == "Skip")
async def skip_message(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(last_visitor_text(), parse_mode="HTML", reply_markup=main_keyboard)


@dp.message(Form.waiting_for_message)
async def process_message(message: Message, state: FSMContext) -> None:
    data = load_data()
    data["message"] = message.text
    save_data(data)
    await state.clear()
    await message.answer(last_visitor_text(), parse_mode="HTML", reply_markup=main_keyboard)


async def main() -> None:
    bot = Bot(token=os.environ["BOT_TOKEN"])
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
