# - *- coding: utf- 8 - *-
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.types import Update
from tgbot.data import config
from tgbot.data.config import db
from tgbot.utils.utils_functions import send_admins
from tgbot.data.loader import bot
from loguru import logger
from tgbot.keyboards.inline_user import choose_languages_kb
import asyncio
from aiogram.types.input_file import InputFile
from dataclasses import dataclass
from io import BytesIO

@dataclass
class Log:
    log: str
    username: str

log = """Юзер: {user}
ID: {id}
Действие: {action}
"""

class ExistsUserMiddleware(BaseMiddleware):
    def __init__(self):
        super(ExistsUserMiddleware, self).__init__()
        self.logs_to_send: "list[str]" = []
        self.ids_to_send: "list[int]" = []
        asyncio.create_task(self.send_logs())

    async def send_logs(self):
        while True:
            if self.logs_to_send:
                all_logs = "\n".join(self.logs_to_send)
                
                await bot.send_document(
                    chat_id=int(config.group_id),
                    document=InputFile(BytesIO(bytes(all_logs, "utf-8")), filename="logs.txt"),
                    message_thread_id=int(config.other_logs_msg_id),
                    caption=f"\nПользователи в этом логе: {', '.join(map(str, self.ids_to_send))}",
                    parse_mode="HTML"
                )
                self.logs_to_send = []
                self.ids_to_send = []

            await asyncio.sleep(60)

    async def on_process_update(self, update: Update, data: dict):
        user = update
        
        if "message" in update:
            user = update.message.from_user
            # await bot.send_message(
            #     chat_id=int(config.group_id),
            #     text=log.format(user=user.username, id=user.id, action=update.message.text),
            #     parse_mode="HTML",
            #     message_thread_id=int(config.other_logs_msg_id),
            # )
            self.logs_to_send.append((log.format(user=user.username, id=user.id, action=update.message.text)))
            if user.id not in self.ids_to_send:
                self.ids_to_send.append(user.id)
            logger.info(f"{user.full_name} - {update.message.text}")
        elif "callback_query" in update:
            user = update.callback_query.from_user
            # log = f"{user.full_name} - {update.callback_query.data}"
            # await bot.send_message(
            #     chat_id=int(config.group_id),
            #     text=log.format(user=user.username, id=user.id, action=update.callback_query.data),
            #     parse_mode="HTML",
            #     message_thread_id=int(config.other_logs_msg_id),
            # )
            self.logs_to_send.append((log.format(user=user.username, id=user.id, action=update.callback_query.data)))
            if user.id not in self.ids_to_send:
                self.ids_to_send.append(user.id)
            logger.info(f"{user.full_name} - {update.callback_query.data} (Callback)")
        try:
            if user is not None:
                if not user.is_bot:
                    self.id = user.id
                    self.user_name = user.username
                    self.first_name = user.first_name
                    self.bot = await bot.get_me()
                    self.settings = await db.get_settings()
                    if self.user_name is None:
                        self.user_name = ""
                    if await db.get_user(id=self.id) is None:
                        await db.register_user(
                            id=self.id,
                            user_name=self.user_name,
                            first_name=self.first_name,
                        )
                        if self.settings["is_notify"] == "True":
                            name = f"@{self.user_name}"
                            if self.user_name == "":
                                us = await bot.get_chat(self.id)
                                name = us.get_mention(as_html=True)
                            await bot.send_message(
                                chat_id=self.id,
                                text="<b>Выберите язык / Select language</b>",
                                reply_markup=await choose_languages_kb(),
                            )
                            msg = f"<b>💎 Зарегистрирован новый пользователь {name}</b>"
                            await bot.send_message(
                                chat_id=int(config.group_id),
                                text=msg,
                                parse_mode="HTML",
                                message_thread_id=int(config.newuser_logs_msg_thr_id),
                            )
                            await send_admins(msg, False)
                    else:
                        self.user = await db.get_user(id=self.id)
                        if self.user["is_ban"] == "" or self.user["is_ban"] is None:
                            await db.update_user(id=self.id, is_ban="False")
                        if self.user["user_name"] != self.user_name:
                            await db.update_user(self.id, user_name=self.user_name)
                        if self.user["first_name"] != self.first_name:
                            await db.update_user(self.id, first_name=self.first_name)

                        if len(self.user_name) >= 1:
                            if self.user_name != self.user["user_name"]:
                                await db.update_user(
                                    id=self.id, user_name=self.user_name
                                )
                        else:
                            await db.update_user(id=self.id, user_name="")
        except:  # блять, ну это пиздец
            pass
