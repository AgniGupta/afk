from .. import loader, utils

import logging
import datetime
import time

from telethon import types

logger = logging.getLogger(name)


@loader.tds
class AFKMod(loader.Module):
    """Provides a message saying that you are unavailable"""

    strings = {
        "name": "AFK",
        "gone": "<b>😭 Мой сенпай в афк 😭</b>",
        "back": "<b>😊 Мой сейпай больше не в афк 😊</b>",
        "afk": "<b>🥺 Мой сенпай сейчас в афк (уже {}). 🥺</b>",
        "afk_reason": "<b>🥺 Мой сенпай сейчас в афк (уже {}). 🥺\nНо он просил передать:</b> <i>{}</i>",
    }

    async def client_ready(self, client, db):
        self._db = db
        self._me = await client.get_me()

    async def afk2cmd(self, message):
        """.afk [message]"""
        if utils.get_args_raw(message):
            self._db.set(name, "afk", utils.get_args_raw(message))
        else:
            self._db.set(name, "afk", True)
        self._db.set(name, "gone", time.time())
        self._db.set(name, "ratelimit", [])
        await self.allmodules.log("afk", data=utils.get_args_raw(message) or None)
        await utils.answer(message, self.strings("gone", message))

    async def unafk2cmd(self, message):
        """Remove the AFK status"""
        self._db.set(name, "afk", False)
        self._db.set(name, "gone", None)
        self._db.set(name, "ratelimit", [])
        await self.allmodules.log("unafk")
        await utils.answer(message, self.strings("back", message))

    async def watcher(self, message):
        if not isinstance(message, types.Message):
            return
        if message.mentioned or getattr(message.to_id, "user_id", None) == self._me.id:
            afk_state = self.get_afk()
            if not afk_state:
                return
            logger.debug("tagged!")
            ratelimit = self._db.get(name, "ratelimit", [])
            if utils.get_chat_id(message) in ratelimit:
                return
            else:
                self._db.setdefault(name, {}).setdefault("ratelimit", []).append(
                    utils.get_chat_id(message)
                )
                self._db.save()
            user = await utils.get_user(message)
            if user.is_self or user.bot or user.verified:
                logger.debug("User is self, bot or verified.")
                return
            if self.get_afk() is False:
                return
            now = datetime.datetime.now().replace(microsecond=0)
            gone = datetime.datetime.fromtimestamp(
                self._db.get(name, "gone")
            ).replace(microsecond=0)
            diff = now - gone
            if afk_state is True:
                ret = self.strings("afk", message).format(diff)
            elif afk_state is not False:
                ret = self.strings("afk_reason", message).format(diff, afk_state)
            await utils.answer(message, ret, reply_to=message)

    def get_afk(self):
        return self._db.get(name, "afk", False)
