# coding=UTF-8
import disnake
import os
import asyncio
import random
import requests
import io
import json
import datetime
import calendar
import time
import sqlite3
from fuzzywuzzy import fuzz
from memory import Memory
from disnake.ext import commands
from PIL import Image, ImageFont, ImageDraw
import googletrans
import string
from gtts import gTTS
from akinator import (
    CantGoBackAnyFurther,
    InvalidAnswer,
    Akinator,
    Answer,
    Theme,
)
from yandex_music.client import Client
from yandex_music.utils.request import Request
from yandex_music.exceptions import NetworkError
client = None
request = Request(proxy_url='proxy_url')
client = Client("yandexToken", request=request).init()
print("yandex_music: Success Connect")
translator = googletrans.Translator()


lists = []

class searchError(Exception):
    pass

class VoiceStateError(Exception):
    pass

class Song(disnake.PCMVolumeTransformer):

    def search_tracks(ctx, query):
        stats = True
        while stats:
            try:
                searcher = client.search(str(query))
                if not searcher.tracks: raise searchError("Not searched tracks")
               # print(searcher.tracks['results'][0])
                track_object = searcher.tracks['results'][0]
                stats = False
                text = None
                lyrics = track_object.get_supplement()
                if lyrics.lyrics: text = lyrics.lyrics.full_lyrics
                with sqlite3.connect("database.db") as db:
                    cursor = db.cursor()
                    cursor.execute("INSERT INTO songs(name, requester, author, id, albumid, lyrics, guild) VALUES(?, ?, ?, ?, ?, ?, ?)", (track_object['title'],ctx.author.id,track_object['artists'][0]['name'],track_object['id'],track_object['albums'][0]["id"],text,ctx.guild.id,))
                    print("Success queued")
                return {
                "id": track_object["id"],
                "title": track_object["title"],
                "artist": track_object["artists"][0]["name"],
                "albumid": track_object["albums"][0]["id"],
                "lyrics": text
                }
            except NetworkError:
                pass
    def download_track(ctx, track):
        stats = True
        while stats:
            try:
                client.tracks(track['id'])[0].download(f"songs/{track['id']}.mp3")
                stats = False
            except NetworkError:
                pass


    async def join_channel(ctx):
        voice = ctx.author.voice
        if not voice: return "notChannel"
        if voice:
            await voice.channel.connect()
            return None

    async def leave_channel(ctx):
        voice_state = ctx.guild.voice_client
        if not voice_state:
            return "notState"
        if voice_state.is_connected():
            await voice_state.disconnect()
            return None
        else:
            return "notState"

    async def stop(ctx):
        voice_state = ctx.guild.voice_client
        if not voice_state:
            return "notState"
        if voice_state.is_connected():
            #await voice_state.stop()
            await Song.leave_channel(ctx)
            return None
        else:
            return "notState"


    async def my_after(ctx):
        #os.remove(f"songs/{ctx.guild.id}.mp3")
        voice_state = ctx.guild.voice_client
        if not voice_state.is_playing:
            stats = False
            names = []
            requesters = []
            artists = []
            ids = []
            albumids = []
            positions = []
            guilds = []
            lyrics = []
            with sqlite3.connect("database.db") as db:
                c = db.cursor()
                for n, r, a, i, ai, ly, g, p in c.execute("SELECT * FROM songs WHERE guild = ?", (ctx.guild.id,)):
                    positions.append(p)
                    names.append(n)
                    requesters.append(r)
                    artists.append(a)
                    guilds.append(g)
                    ids.append(i)
                    albumids.append(ai)
                    if n and not ly:
                        lyrics.append(None)
                    else:
                        lyrics.append(ly)
                c.execute("DELETE FROM songs WHERE guild = ? AND position = ?", (guilds[0], positions[0],))
                print("Success removed")
            whats = False
            try:
                whats = positions[1]
                whats = True
            except:
                whats = False
                return
            if whats:
                #Song.download_track(ctx, {"id": ids[1], "title": names[1], "artist": artists[1], "albumid": albumids[1], "lyrics": lyrics[1]})
                await Song.play(ctx)


    async def play_next(ctx):
        names = []
        requesters = []
        artists = []
        ids = []
        albumids = []
        positions = []
        guilds = []
        lyrics = []
        with sqlite3.connect("database.db") as db:
            c = db.cursor()
            for n, r, a, i, ai, ly, g, p in c.execute("SELECT * FROM songs WHERE guild = ?", (ctx.guild.id,)):
                positions.append(p)
                names.append(n)
                requesters.append(r)
                artists.append(a)
                guilds.append(g)
                ids.append(i)
                albumids.append(ai)
                if n and not ly:
                    lyrics.append(None)
                else:
                    lyrics.append(ly)
            c.execute("DELETE FROM songs WHERE guild = ? AND position = ?", (guilds[0], positions[0],))
            print("Success removed")
        try:
            gsdg = positions[1]
        except:
            return
        else:
            #Song.download_track(ctx, {"id": ids[1], "title": names[1], "artist": artists[1], "albumid": albumids[1], "lyrics": lyrics[1]})
            await Song.play(ctx)



    async def play(ctx):
        voice_state = ctx.guild.voice_client
        if not voice_state:
            error = await Song.join_channel(ctx)
            if error:
                return error
        voice_state = ctx.guild.voice_client
        if voice_state.is_playing():
            return "alreadyPlay"
        ids = []
        with sqlite3.connect("database.db") as db:
            c = db.cursor()
            for n, r, a, i, ai, ly, g, p in c.execute("SELECT * FROM songs WHERE guild = ?", (ctx.guild.id,)):
                ids.append(i)
        if not os.path.isfile(f"songs/{ids[0]}.mp3"):
            Song.download_track(ctx, {'id': ids[0]})
        # loop = asyncio.get_running_loop().create_task(Song.my_after(ctx))
        # asyncio.set_event_loop(loop)
        # loop = asyncio.new_event_loop()
        # loop.run_forever(Song.my_after(ctx, loop))
        voice_state.play(disnake.FFmpegPCMAudio(f"songs/{ids[0]}.mp3"))

        return None

    async def skip(ctx):
        voice_state = ctx.guild.voice_client
        if voice_state.is_playing():
            try:
                await voice_state.stop()
            except:
                pass
            await Song.play_next(ctx)
            return None
        else:
            return "notState"

    def lyrics(ctx):
        names = []
        requesters = []
        artists = []
        ids = []
        albumids = []
        lyrics = []
        with sqlite3.connect("database.db") as db:
            c = db.cursor()
            for n, r, a, i, ai, ly, g, p in c.execute("SELECT * FROM songs WHERE guild = ?", (ctx.guild.id,)):
                names.append(n)
                requesters.append(r)
                artists.append(a)
                ids.append(i)
                albumids.append(ai)
                if n and not ly:
                    lyrics.append(None)
                else:
                    lyrics.append(ly)

        return {
        "name": names[0],
        "lyrics": lyrics[0]
        }

    def now_playing(ctx):
        names = []
        requesters = []
        artists = []
        ids = []
        albumids = []
        positions = []
        with sqlite3.connect("database.db") as db:
            c = db.cursor()
            for n, r, a, i, ai, ly, g, p in c.execute("SELECT * FROM songs WHERE guild = ?", (ctx.guild.id,)):
                names.append(n)
                requesters.append(r)
                artists.append(a)
                ids.append(i)
                albumids.append(ai)
                positions.append(p)
        return {
        "name": names[0],
        "requester": requesters[0],
        "artist": artists[0],
        "pos": positions[0],
        "uri": f"https://music.yandex.ru/album/{ids[0]}/track/{albumids[0]}"
        }

    def construct_queue(ctx):
        urls = []
        names = []
        positions = []
        texts = []
        with sqlite3.connect("database.db") as db:
            c = db.cursor()
            for n, r, a, i, ai, ly, g, p in c.execute("SELECT * FROM songs WHERE guild = ?", (ctx.guild.id,)):
                names.append(n)
                positions.append(p)
                urls.append(f"https:/music.yandex.ru/album/{ai}/track/{i}")
                texts.append(f"`{p}.` [**{n}**](https:/music.yandex.ru/album/{ai}/track/{i})")
        if texts == []: return None
        return "\n".join(list(map(str, texts)))

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="join",description="Подключает бота к вашему каналу")
    async def _join(self, ctx):
        await ctx.response.defer()
        error = await Song.join_channel(ctx)
        if error:
            if error == "notChannel": await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка",description="Для этого необходимо войти в голосовой канал",color=disnake.Color.red()))

        await ctx.send(embed=disnake.Embed(title="<:correctCheckmark:1047244074350018700> Успешно",color=0x228b22))

    @commands.slash_command(name="stop",description="Остановить воспроизведение")
    async def _stop(self, ctx):
        await ctx.response.defer()
        error = await Song.stop(ctx)
        if error:
            if error == "notState": return await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка",description="Я уже не подключен.",color=disnake.Color.red()))

        await ctx.send(embed=disnake.Embed(title="<:correctCheckmark:1047244074350018700> Успешно",description="Пока-пока!",color=0x228b22))

    @commands.slash_command(name="play",description="Воспроизвести трек")
    async def _play(self, ctx, название: str = None):
        await ctx.response.defer()
        name = название
        if name and name.startswith("https://"):
            return await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка",description="Я не поддерживаю ссылки!",color=disnake.Color.red()))
        voice_state = ctx.guild.voice_client
        if name:
            try:
                track = Song.search_tracks(ctx, name)
            except searchError:
                return await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка",description="Ничего не нашлось :(",color=disnake.Color.red()))
        else:
            text = Song.construct_queue(ctx)
            if not text:
                return await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка",description="Очередь на этом сервере пуста, поэтому добавьте что то в неё!",color=disnake.Color.red()))
        if voice_state:
            if voice_state.is_playing():
                #await Song.leave_channel(ctx)
                pass
            else:
                error = await Song.play(ctx)
        else:
            error = await Song.play(ctx)
            if error:
                if error == "notChannel": return await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка",description="Зайдите в голосовой канал.",color=disnake.Color.red()))
        if name:
            await ctx.send(f"{track['title']} успешно добавлена в очередь!")
        else:
            await ctx.send(f"**{self.bot.user.name}** успешно начал воспроизведение очереди!")


    @commands.slash_command(name="skip",description="Пропустить трек")
    async def _skip(self, ctx):
        await ctx.response.defer()
        error = await Song.skip(ctx)
        if error == "notState": return await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка",description="Сейчас ничего не играет!",color=disnake.Color.red()))
        await ctx.send(embed=disnake.Embed(title="<:correctCheckmark:1047244074350018700> Успешно",color=0x228b22))

    @commands.slash_command(name="lyrics",description="Получить текст от играемого прямо сейчас трека")
    async def lyri(self, ctx):
        lyrics = Song.lyrics(ctx)
        if not lyrics['lyrics']: return await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка",description="Текст этой песни не доступен",color=disnake.Color.red()))
        await ctx.send(embed=disnake.Embed(title=f"🔍 Текст от трека **{lyrics['name']}**",description=lyrics["lyrics"]))

    @commands.slash_command(name="now-playing",description="Что сейчас играет?")
    async def np(self, ctx):
        voice_state = ctx.guild.voice_client
        if voice_state:
            if voice_state.is_playing():
                infor = Song.now_playing(ctx)
                embed = disnake.Embed(title=infor['name'],color=0x228b22)
                embed.add_field(name="Главный автор:",value=infor['artist'])
                embed.add_field(name="Предложил:",value=f"<@{infor['requester']}>")
                embed.add_field(name="Источник:",value="<:yandexMusic:1056924402790436934> Yandex Music\n")
                embed.add_field(name="Ссылка:",value=f"[**Это кликабельная ссылка!**]({infor['uri']})")
                embed.add_field(name="Позиция:",value=infor['pos'])
                await ctx.send(embed=embed)
            else:
                await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка!",description="Сейчас ничего не играет",color=disnake.Color.red()))
        else:
            await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка!",description="Сейчас ничего не играет",color=disnake.Color.red()))

    @commands.slash_command(name="queue", description="Посмотреть очередь")
    async def queu(self, ctx):
        text = Song.construct_queue(ctx)
        if not text:
            return await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка",description="Очередь на этом сервере пуста!",color=disnake.Color.red()))
        await ctx.send(embed=disnake.Embed(title=f"Очередь сервера {ctx.guild.name}!",description=text, color=0x228b22))

class Main(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="help",description="Список команд для ориентации.")
    async def help(self, ctx):
        #embed = disnake.Embed(title="Список моих команд", description="**🎮 Игры**\n`/guess-the-letter` - Игра в угадай букву\n`/maths-plus` - Игра в математику с сложением\n`/maths-minus` - Игра в математику с вычитанием\n`/maths-multiply` - Игра в математику с умножением\n`/tape` - Игра в рулетку\n`/truth-or-dare` - Игра в п или д\n`/heads-or-tails` - Подбросить монетку\n\n**Модерация**\n`/ban [member] <reason>` - Забанить кого-то\n`/unban [member id]` - разбанить кого то\n`/kick [member] <reason>` - Выгнать кого либо с сервера\n`/mute [member] <time>` - Заглушить кого то на сколько то минут\n`/warn [@member] <reason>` - Выдать пред\n`/warns` - Посмотреть все преды на этом сервере\n`/unwarn [номер_случая]` - Снять пред\n\n**Утилиты**\n`/profile` - Увидеть своё кол-во очков и профиль\n`/lgbt` - Делает вам ЛГБТ аватарку\n`/jail` - Делает аватарку, сидящую в тюрьме\n`/passed` - Делает на вашей аватарке надпись \"Mission Passed, respect+\"\n`/wasted` - Делает на вашей аватарке надпись \"WASTED\"\n`/pixelate` - Пиксилизирует ваш аватар\n`/triggered` - Делает на вашей аватарке надпись \"TRIGGERED\"\n`/ussr` - Накладывает на ваш аватар флаг СССР\n`/youtube-comment [коментарий]` - Делает коментарий с вашим ником, аватаром и коментарием\n`/voice [текст]` - Создаёт озвучку указаного вами текста\n`/encode [текст]` - Зашифровать текст в base64\n`/decode [base64]` - Расшифровать base64 в текст\n\n**<:dollar:1051974269296451684> Экономика**\n`/daily` - Получить ежедневную награду, может быть отключена админами\n`/work [!работа]` - Работать чтобы получить деньги, работа выбирается выпадающим списком\n`/balance` - Проверить свой или чужой баланс\n\n**Отношения**\n`/hug [участник]` - Обнять кого либо\n`/pat [участник]` - Погладить кого либо\n\n**РП**\n`/acc-register [имя]` - Создать нового персонажа\n`/acc-update-avatar [имя]` - Сменить аватар персонажу\n`/acc-send [имя] [сообщение]` - Отправить сообщение от имени персонажа\n`/acc-all` - Посмотреть список всех персонажей в этом канале\n`/acc-remove [имя]` - Удалить персонажа\n\n**⚙Настройки**\n`/set-welcome-channel [канал]` - Устанавливает канал для уведомления о новых участниках\n`/set-bye-channel [канал]` - Установить канал для уведомления о ушедших участниках\n`/set-daily [сумма] - Установить сумму ежедневного приза, 0 если отключить`\n`/set-anti-badwords` - Включить анти плохие слова\n`/disable-set [настройка]` - Отключить какую то настройку, настройка выбирается выпадающим списком\n`/ping` - Проверить работоспособность бота", color=0x228b22)
        #embed.set_footer(
        #    text="Произоидёт автоматическое удаление сообщения через 60 секунд!"
        #)
        embedmain = disnake.Embed(title="Начните нажимать на кнопки для выбор чего то.",description="<:yandexMusic:1056924402790436934> **Яндекс.Музыка**\n🎮 **Игры**\n\n<:cooldown:1047243027166539846> **Модерация**\n\n🎁**Утилиты**\n\n:dollar: **Экономика**\n\n<:pandaElf:1047241340657872948> **Отношения**\n\n<:thinks1:1047243641388793938> **РП**\n\n⚙ **Настройки**",color=0x228b22)
        await ctx.send(embed=embedmain,components=[
            disnake.ui.Button(label="Яндекс.Музыка",style=disnake.ButtonStyle.danger, custom_id="mus"),
            disnake.ui.Button(label="Игры", style=disnake.ButtonStyle.success, custom_id="games"),
            disnake.ui.Button(label="Модерация", style=disnake.ButtonStyle.danger, custom_id="mod"),
            disnake.ui.Button(label="Утилиты", style=disnake.ButtonStyle.success, custom_id="utils"),
            disnake.ui.Button(label="Экономика", style=disnake.ButtonStyle.danger, custom_id="eco"),
            disnake.ui.Button(label="Отношения", style=disnake.ButtonStyle.success, custom_id="relaship"),
            disnake.ui.Button(label="РП", style=disnake.ButtonStyle.danger, custom_id="roleplay"),
            disnake.ui.Button(label="Настройки", style=disnake.ButtonStyle.success, custom_id="setts")
        ])
        #embedyes = disnake.Embed(title="Вы нажали",description="Да",color=0x228b22)
        #embedno = disnake.Embed(title="Вы нажали",description="Нет",color=disnake.Color.red())
        
        embedmus = disnake.Embed(title="<:yandexMusic:1056924402790436934> Яндекс.Музыка",description="`/play <название>` - Начать воспроизведение в голосовом канале\n`/skip` - Пропустить трек\n`/stop` - Остановить и выйти из голосового канала\n`/join` - Пригласить бота в голосовой канал\n`/queue` - Посмотреть очередь серверва\n`/now-playing` - что сейчас играет?",color=0x228b22)
        embedgames = disnake.Embed(title="🎮 Игры", description="`/guess-the-letter` - Игра в угадай букву\n`/maths-plus` - Игра в математику с сложением\n`/maths-minus` - Игра в математику с вычитанием\n`/maths-multiply` - Игра в математику с умножением\n`/tape` - Игра в рулетку\n`/truth-or-dare` - Игра в п или д\n`/heads-or-tails` - Подбросить монетку\n`/door` - Игра 'Выбери правильную дверь.'\n`/akinator` - Сыграть в акинатора", color=0x228b22)
        embedmod = disnake.Embed(title="<:cooldown:1047243027166539846> Модерация",description="`/ban [member] <reason>` - Забанить кого-то\n`/unban [member id]` - разбанить кого то\n`/kick [member] <reason>` - Выгнать кого либо с сервера\n`/mute [member] <time>` - Заглушить кого то на сколько то минут\n`/warn [@member] <reason>` - Выдать пред\n`/warns` - Посмотреть все преды на этом сервере\n`/unwarn [номер_случая]` - Снять пред", color=0x228b22)
        embedutils = disnake.Embed(title="<:Magic:1047241900370956298> Утилиты",description="`/profile` - Увидеть своё кол-во очков и профиль\n`/lgbt` - Делает вам ЛГБТ аватарку\n`/jail` - Делает аватарку, сидящую в тюрьме\n`/passed` - Делает на вашей аватарке надпись \"Mission Passed, respect+\"\n`/wasted` - Делает на вашей аватарке надпись \"WASTED\"\n`/pixelate` - Пиксилизирует ваш аватар\n`/triggered` - Делает на вашей аватарке надпись \"TRIGGERED\"\n`/ussr` - Накладывает на ваш аватар флаг СССР\n`/youtube-comment [коментарий]` - Делает коментарий с вашим ником, аватаром и коментарием\n`/voice [текст]` - Создаёт озвучку указаного вами текста\n`/encode [текст]` - Зашифровать текст в base64\n`/decode [base64]` - Расшифровать base64 в текст\n`/joke <язык>` - Генерирует рандомную шутку(Смешная или нет зависит от АПИ)\n`/poll [sel1] [sel2] <sel...>` - Запустить голосование\n`/random [вариации]` - Рандомайзер\n`/new-year` - Через сколько дней новый год?",color=0x228b22)
        embedeco = disnake.Embed(title="<:dollar:1051974269296451684> Экономика",description="`/daily` - Получить ежедневную награду, может быть отключена админами\n`/work [!работа]` - Работать чтобы получить деньги, работа выбирается выпадающим списком\n`/balance` - Проверить свой или чужой баланс\n`/add-money [сумма] [участник]` - Выдать 'сумма' валюты пользователю 'участник'\n`/reduce-money [сумма] [участник]` - Забирает 'сумма' валюты у 'участник'а", color=0x228b22)
        embedrela = disnake.Embed(title="<:pandaElf:1047241340657872948> Отношения",description="`/hug [участник]` - Обнять кого либо.\n`/pat [участник]` - Погладить кого либо",color=0x228b22)
        embedrp = disnake.Embed(title="<:shockedThinsk4:1047243843541680229> РП",description="`/acc-register [имя]` - Создать нового персонажа\n`/acc-update-avatar [имя]` - Обновить аватар персонажу\n`/acc-all` - Посмотреть весь список персонажей\n`/acc-send [имя] [сообщения]` - Отправить сообщение от имени персонажа",color=0x228b22)
        embedsetts = disnake.Embed(title="⚙ Настройки",description="`/set-welcome-channel [канал]` - Устанавливает канал для уведомления о новых участниках\n`/set-bye-channel [канал]` - Установить канал для уведомления о ушедших участниках\n`/set-daily [сумма] - Установить сумму ежедневного приза, 0 если отключить`\n`/set-anti-badwords` - Включить анти плохие слова\n`/set-work-price [сумма]` - Установить сумму которая будет выдаваться участника за работу\n`/disable-set [настройка]` - Отключить какую то настройку, настройка выбирается выпадающим списком\n`/ping` - Проверить работоспособность бота",color=0x228b22)
        #embedtime = disnake.Embed(title="Время истекло!",description="Слишком долго не было какой либо активности с кнопками.",color=disnake.Color.red())
        status = True
        while status:
            try:
                btn = await bot.wait_for("button_click",timeout=80)
                if btn.component.custom_id == "mus":
                    await ctx.edit_original_response(embed=embedmus)
                    await btn.response.defer()
                elif btn.component.custom_id == "games":
                    await ctx.edit_original_response(embed=embedgames)
                    await btn.response.defer()
                elif btn.component.custom_id == "mod":
                    await ctx.edit_original_response(embed=embedmod)
                    await btn.response.defer()
                elif btn.component.custom_id == "utils":
                    await ctx.edit_original_response(embed=embedutils)
                    await btn.response.defer()
                elif btn.component.custom_id == "eco":
                    await ctx.edit_original_response(embed=embedeco)
                    await btn.response.defer()
                elif btn.component.custom_id == "relaship":
                    await ctx.edit_original_response(embed=embedrela)
                    await btn.response.defer()
                elif btn.component.custom_id == "roleplay":
                    await ctx.edit_original_response(embed=embedrp)
                    await btn.response.defer()
                elif btn.component.custom_id == "setts":
                    await ctx.edit_original_response(embed=embedsetts)
                    await btn.response.defer()
            except asyncio.TimeoutError:
                status = False
                return await ctx.edit_original_response(components=None)


class Games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="guess-the-letter", description="Угадай букву")
    async def gtl(self, ctx):
        quest = random.randint(0,3)
        if quest == 1:
            embed = disnake.Embed(title="Поиграем? 😏",description="**Угадай букву**\nУгадаете какая буква отсутствует?..:\n\nК О Р Е ||?|| К А")
            embedwin = disnake.Embed(title="Поиграем? 😏",description="**Угадай букву**\nУгадаете какая буква отсутствует?..:\n\nК О Р Е Ж К А")
            await ctx.send(embed=embed)
            status = True
            while status:
                wait = await bot.wait_for("message")
                if wait.content.lower() == "ж":
                    status = False
                    await ctx.send(embed=embedwin)
                else:
                    await ctx.send("Неверно")
        if quest == 2:
            embed = disnake.Embed(title="Поиграем? 😏",description="**Угадай букву**\nУгадаете какая буква отсутствует?..:\n\n||?|| Т Р А В А")
            embedwin = disnake.Embed(title="Поиграем? 😏",description="**Угадай букву**\nУгадаете какая буква отсутствует?..:\n\nО Т Р А В А")
            await ctx.send(embed=embed)
            status = True
            while status:
                wait = await bot.wait_for("message")
                if wait.content.lower() == "о":
                    status = False
                    await ctx.send(embed=embedwin)
                else:
                    await ctx.send("Неверно")
        if quest == 3:
            embed = disnake.Embed(title="Поиграем? 😏",description="**Угадай букву**\nУгадаете какая буква отсутствует?..:\n\n||?|| А Р Я Г")
            embedwin = disnake.Embed(title="Поиграем? 😏",description="**Угадай букву**\nУгадаете какая буква отсутствует?..:\n\nВ А Р Я Г")
            await ctx.send(embed=embed)
            status = True
            while status:
                wait = await bot.wait_for("message")
                if wait.content.lower() == "в":
                    status = False
                    await ctx.send(embed=embedwin)
                else:
                    await ctx.send("Неверно")

    @commands.slash_command(name="maths-minus",description="Игра в математику с вычитанием")
    async def mathsminus(self, ctx):
        first = random.randint(1, 20000)
        second = random.randint(1, 1500)
        reply = first - second
        await ctx.send(embed=disnake.Embed(title="Игра в математику",description=f"Сколько будет {first} - {second}?"))
        status = True
        while status:
            wait = await bot.wait_for("message")
            if wait.guild.id == ctx.guild.id:
                if wait.author.id == ctx.author.id:
                    user_repl = wait.content.lower()
                    try:
                        user_repl = int(user_repl)
                    except ValueError:
                        status = False
                        return await ctx.send(embed=disnake.Embed(title="Ты ответил не числом, поэтому оценка 2!",description=f"Правильным ответом было {reply}",color=disnake.Color.red()))
                    if user_repl == reply:
                        status = False
                        return await ctx.send(embed=disnake.Embed(title="Твой ответ верный!",description="Поздравляю. Оценка 5.",color=disnake.Color.green()))
                    else:
                        status = False
                        return await ctx.send(embed=disnake.Embed(title="Ты ответил не верно, поэтому оценка 2!",description=f"Правильным ответом было {reply}",color=disnake.Color.red()))

    @commands.slash_command(name="maths-plus",description="Игра в математику с сложением")
    async def mathsplus(self, ctx):
        first = random.randint(1, 1500) # Создаём первое рандомное число между 1 и 1500
        second = random.randint(1, 1500) # Тоже самое, только второе
        reply = first + second # Создаём ответ, прибавив первое и второе
        await ctx.send(embed=disnake.Embed(title="Игра в математику",description=f"Сколько будет {first} + {second}?")) #Отправляем пример
        status = True # Ставим статус на не решен.
        while status: # Создаём сессию
            wait = await bot.wait_for("message") # Ждём ответа
            if wait.guild.id == ctx.guild.id: # Если сервер равен нашему серверу
                if wait.author.id == ctx.author.id: # Если автор равен нашему автору
                    user_repl = wait.content.lower() # Получаем ответ, и убираем знаки препинания
                    try: # Пробуем ответ превратить в число
                        user_repl = int(user_repl) # Превращаем
                    except ValueError: # Если не удалось из-за того что ответ пользователя - текст
                        status = False # Завершаем сессию
                        return await ctx.send(embed=disnake.Embed(title="Ты ответил не числом, поэтому оценка 2!",description=f"Правильным ответом было {reply}",color=disnake.Color.red())) # Говорим о том что мы ответили НЕ числом
                    if user_repl == reply: # Если ответ пользователя равен ранее созданному верному ответу
                        status = False # Завершаем сессию
                        return await ctx.send(embed=disnake.Embed(title="Твой ответ верный!",description="Поздравляю. Оценка 5.",color=disnake.Color.green())) # Поздравляем с верным ответом
                    else: # Если условие выше не верно
                        status = False # Завершаем сессию
                        return await ctx.send(embed=disnake.Embed(title="Ты ответил не верно, поэтому оценка 2!",description=f"Правильным ответом было {reply}",color=disnake.Color.red())) # Говорим об неверном ответе, и говорим верный ответ

    @commands.slash_command(name="maths-multiply",description="Игра в математику с умножением")
    async def mathsmultiply(self, ctx):
        first = random.randint(1, 1000)
        second = random.randint(1, 1000)
        reply = first * second
        await ctx.send(embed=disnake.Embed(title="Игра в математику",description=f"Сколько будет {first} * {second}?"))
        status = True
        while status:
            wait = await bot.wait_for("message")
            if wait.guild.id == ctx.guild.id:
                if wait.author.id == ctx.author.id:
                    user_repl = wait.content.lower()
                    try:
                        user_repl = int(user_repl)
                    except ValueError:
                        status = False
                        return await ctx.send(embed=disnake.Embed(title="Ты ответил не числом, поэтому оценка 2!",description=f"Правильным ответом было {reply}",color=disnake.Color.red()))
                    if user_repl == reply:
                        status = False
                        return await ctx.send(embed=disnake.Embed(title="Твой ответ верный!",description="Поздравляю. Оценка 5.",color=disnake.Color.green()))
                    else:
                        status = False
                        return await ctx.send(embed=disnake.Embed(title="Ты ответил не верно, поэтому оценка 2!",description=f"Правильным ответом было {reply}",color=disnake.Color.red()))


    @commands.slash_command(name="tape", description="Крутануть рулетку на случайное кол-во баллов")
    @commands.cooldown(1, 60, commands.BucketType.user) # Ставим кулдаун
    async def tape(self, ctx): # Функция для кода
        await ctx.response.defer() # Ответ "0XB1 думает..." 
        mynum = random.randint(20, 3000) # Выбираем рандомное число между 20 и 3000
        type_of_num = "Error" # Создаём переменную для редкости
        type_color = 0xffffff
        if mynum == 20: # Если равно 20
            type_of_num = "минимальное" # Ставим редкость на минимальную
            type_color = 0xffffff # Ставим белый цвет
        if mynum > 20: # Если больше 20
            type_of_num = "редкое" # Ставим на редкую
            type_color = 0x0084ff #Ставим голубой цвет
        if mynum > 100: # Если больше ста
            type_of_num = "эпическое" # Ставим эпическую
            type_color = 0x6f00ff # Ставим фиолетовый
        if mynum > 1000: # Если больше тысячи
            type_of_num = "мифическое" # Ты уже понял
            type_color = 0xff0000 #Ставим красный
        if mynum > 2500: #Если больше 2500
            type_of_num = "ЛЕГЕНДАРНОЕ" # Легендарка
            type_color = 0xffee00 #Ставим жёлтый цвет
        #await ctx.send(f"Вам выпало {mynum}!\n Это {type_of_num} количество!") # Отправляем сообщение
        embedfortune = disnake.Embed(color=0x228b22).set_image(url="https://media.tenor.com/fJ10v8TLEi0AAAAC/wheel-of-fortune.gif")
        await ctx.send(embed=embedfortune)
        await asyncio.sleep(3)
        img = Image.new('RGBA', (400, 150), '#232529')
        idraw = ImageDraw.Draw(img)
        headline = ImageFont.truetype('comfortaa.ttf', size = 25)
        undertext = ImageFont.truetype('comfortaa.ttf', size = 15)
        idraw.text((10,15), f"Вы выиграли {mynum} очков!", font=headline)
        idraw.text((105, 40), f"Это {type_of_num} число!", font=undertext)
        idraw.text((105, 65), f"Выйгравший - {ctx.author.name}", font=undertext)
        idraw.text((10, 135), f'Vex Draw\'s', font=undertext)
        img.save("tape_result.png")
        embed = disnake.Embed(color=type_color).set_image(file=disnake.File("tape_result.png"))
        await ctx.edit_original_response(embed=embed)
        last_member_count = 0
        try:
            last_member_count = int(Memory.read(f"scope/{ctx.author.id}balls.txt")) # Получаем прошлое кол-во очков юзера
        except:
            last_member_count = 0 # Если не удалось, считаем что 0 очков

        Memory.write(f"scope/{ctx.author.id}balls.txt", last_member_count + mynum) # Прибавляем к выигранным очкам прошлое кол-во и записываем в память

    @commands.slash_command(name="truth-or-dare", description="Игра в п или д")
    async def t_or_d(self, ctx):
        truth = ["Тебя привлекают парни, или девушки?","Кого ты любишь? Назови его/её имя.","Какие языки ты знаешь? 🌎","Какое твоё хобби?","Ты выпивал когда нибудь?","Ты ходишь на какие нибудь доп. занятия?","Какой твой любимый напиток?","Какая твоя любимая пища?","Ты знаешь что то взрослое? Расскажи. (Пожалуйста, введите комнаду второй раз, если играете с детьми.)","Какой была твоя самая неловкая ситуация? Расскажи о ней.","В каком ты классе?(Или же кем работаешь)","Ты знаешь что нибудь из програмирования? Поделись этим если да.","Чтобы ты выбрал - Adidas или Nike?(не реклама)","Кем ты планируешь работать в будущем?(Если уже не работаешь)","Сколько сейчас у тебя на балансе денег? <:dollar:1051974269296451684>"]
        dare = ["Скажи тому, кого любишь о том, что ты любишь его. 💜","Найди веник, а лучше метлу, и изобрази ведьму, летающую на метле с серьёзным лицом.","Изобрази своё любимое животное","Повтори свой любимый мем.","Скажи что то на английском","Прямо сейчас без обсуждения на весь дом крикни \"ГОЛУБКИ Я ДОМА\"","Сделай ужасное селфи и поставь его себе на аватар на 3 дня.","Сними свои носки ртом(Зубами)","Поговори с подушкой 5 минут, как будто ты её любишь.","Издавай неприятные и громкие звуки в течении всего дня, когда ешь или пьёшь.","Разговаривай со всеми не закрывая рот.","Поспорь со стенкой","Подерись со стенкой","Проверь, сколько виноградин у тебя поместиться во рту.","Выйди на улицу, и прокричи \"О НЕТ! МЕНЯ УСЫНОВИЛИ(УДОЧЕРИЛИ)\""]
        await ctx.response.defer()
        questo = disnake.Embed(title="Что выбирает игрок, играющий в игру? 🎁",color=0x228b22)
        await ctx.send(embed=questo,components=[
            disnake.ui.Button(label="Правда", style=disnake.ButtonStyle.success, custom_id="truth"),
            disnake.ui.Button(label="Действие", style=disnake.ButtonStyle.danger, custom_id="dare"),
        ])

        @self.bot.listen("on_button_click")
        async def game_listener(ctx: disnake.MessageInteraction):
            if ctx.component.custom_id == "truth":
                await ctx.send(embed=disnake.Embed(description=f"{ctx.author.mention} {random.choice(truth)}",color=0x228b22))
            if ctx.component.custom_id == "dare":
                await ctx.send(embed=disnake.Embed(description=f"{ctx.author.mention} {random.choice(dare)}",color=0x228b22))

    @commands.slash_command(name="heads-or-tails",description="Народный способ решить что либо, орёл или решка?")
    async def heads_or_tail(self, ctx):
        await ctx.response.defer()
        wars = [0, 1]
        wars = random.choice(wars)
        await ctx.send(embed=disnake.Embed(color=0x228b22).set_image(url="https://cdn.glitch.global/5fcfa7e8-8436-4acd-a852-e721cd1b531e/coin-flip-20.gif?v=1669511113445"))
        await asyncio.sleep(3)
        if wars == 1:
            return await ctx.edit_original_response(embed=disnake.Embed(title="Это Орёл!",color=0x228b22).set_image(url="https://w7.pngwing.com/pngs/73/614/png-transparent-double-headed-eagle-gold-coin-gold-gold-coin-gold-material.png"))
        if wars == 0:
            return await ctx.edit_original_response(embed=disnake.Embed(title="Это Решка!",color=0x228b22).set_image(url="https://newcoin.ru/wa-data/public/shop/products/59/08/859/images/3343/3343.970.JPG"))

    @commands.slash_command(name="door",description="Игра - Выбери правильную дверь!")
    async def door(self, ctx):
        door = random.choice([1,2,3])
        components = disnake.ui.Select(placeholder="Выбирайте...", options=[
            disnake.SelectOption(label="1🚪", value = "1", description="Выбрать первую дверь"),
            disnake.SelectOption(label="2🚪", value = "2", description="Выбрать вторую дверь"),
            disnake.SelectOption(label="3🚪", value = "3", description="Выбрать третью дверь")
        ])
        await ctx.send(embed=disnake.Embed(title="Выбери правильную дверь",description="Правильная или нет, зависит от твоей удачи...",color=0x228b22), components=components)
        try:
            slct = await self.bot.wait_for("message_interaction", timeout=20) # Как я понял(т.к. нет никаких ошибок), ожидание этой строки напросто зависает.
            if slct.values[0] == str(door):
                await ctx.edit_original_response(embed=disnake.Embed(title="Вы выбрали правильную дверь!",description="Поздравляю!",color=0x228b22), components=None)
                await slct.response.defer()
            else:
                await ctx.edit_original_response(embed=disnake.Embed(title="Не верно...",description=f"Правильной дверью была {door}. В следующий раз повезёт!", color=disnake.Color.red()), components=None)
                await slct.response.defer()
        except asyncio.TimeoutError:
            await ctx.edit_original_response(embed=disnake.Embed(title="Таймаут истёк!", color=disnake.Color.red()))

    # @commands.slash_command(name="fight",description="Сразиться с другим слабаком!")
    # async def fight(self, ctx, участник: disnake.Member = commands.Param(description="С кем хотите сразиться?")):
    #     await ctx.response.defer()
    #     component = [
    #         disnake.ui.Button(label="ДА!", style=disnake.ButtonStyle.danger, custom_id="yes"),
    #         disnake.ui.Button(label="Нет... Я жалкий трусишка...", style=disnake.ButtonStyle.success, custom_id="no")
    #     ]
    #     member = участник
    #     await ctx.send(embed=disnake.Embed(title=f"**{member.name}**`({member.mention})`, готовы ли вы сразиться с **{ctx.author.name}**`({ctx.author.mention})`?",description=f"У вашего врага(`{member.name}`) есть 30 секунд чтобы сделать свой выбор.",color=0x228b22),components=component)
    #     try:
    #         def check(msg):
    #             if not msg.author.id == member.id:
    #                 await ctx.send(f"{msg.author.mention} а здорово ты это придумал, я даже в начале не понял, молодец!")
    #             return msg.author.id == member.id
    #         btn = await bot.wait_for("button_click", check=check, timeout = 30)
    #         if btn.component.custom_id == "yes":
    #             await ctx.edit_original_response(embed=disnake.Embed(title="Отлично!",description=f"{member.name} согласился на драку!",color=0x228b22),components=None)
    #         else:
    #             return await ctx.edit_original_response(embed=disnake.Embed(title=f"{member.name} оказался жалким трусом",description=f"{member} отказался от драки.",color=disnake.Color.red()),components=None)
    #     except asyncio.TimeoutError:
    #         return await ctx.edit_original_response(content=f"{member} проигнорировал запрос на драку.",embed=None,components=None)
    #     await ctx.edit_original_response(embed=disnake.Embed(title="    **ДРАКА НАЧИНАЕТСЯ!**    ",description=f"    **{member} - 100 hp**    \n    **{ctx.author} - 100hp**    ",color=0x228b22))
    #     await asyncio.sleep(3)
    #     await ctx.edit_original_response(embed=disnake.Embed(title="    **ДРАКА ИДЁТ!**    ",description="    **!**    ",color=0x228b22))
    #     await asyncio.sleep(10)
    #     text = None
    #     author = random.randint(0,55)
    #     memb = random.randint(0,55)
    #     if author > memb:
    #         text = f"**{ctx.author} ПОБЕДИЛ {member}**"
    #     elif author < memb:
    #         text = f"**{member} ПОБЕДИЛ {ctx.author}**"
    #     elif author == memb:
    #         text = f"**Что-ж... У вас ничья!**"
    #     await ctx.edit_original_response(embed=disnake.Embed(title=text, description=f"    **{ctx.author} - {author}hp**    \n    **{member} - {memb}hp**    "))
    #     try:
    #         if author > memb:
    #             ctx.author.edit(nick=f"ПОБЕДИТЕЛЬ - {ctx.author.name}")
    #         elif author < memb:
    #             member.edit(nick=f"ПОБЕДИТЕЛЬ - {member.name}")
    #     except:
    #         pass

    @commands.slash_command(name="akinator",description="Сыграйте в акинатора.")
    async def aki(self, ctx):
        await ctx.response.defer()
        aki = Akinator(
            child_mode=False,
            theme=Theme.from_str('characters')
        )
        first_queston = aki.start_game()
        stats = True
        number = 1
        component = [
            disnake.ui.Button(label="Да",style=disnake.ButtonStyle.success,custom_id="Yes"),
            disnake.ui.Button(label="Нет",style=disnake.ButtonStyle.danger,custom_id="No"),
            disnake.ui.Button(label="Я не знаю",style=disnake.ButtonStyle.blurple,custom_id="Idk"),
            disnake.ui.Button(label="Возможно", style=disnake.ButtonStyle.success,custom_id="Probably"),
            disnake.ui.Button(label="Скорее всего нет",style=disnake.ButtonStyle.danger,custom_id="Probably not"),
            disnake.ui.Button(emoji="🛑", label="Стоп", style=disnake.ButtonStyle.danger,custom_id="STOP")
        ]
        def check(msg):
            return msg.author.id == ctx.author.id
        first_queston = translator.translate(first_queston, dest="ru")
        await ctx.send(embed=disnake.Embed(title=f"Вопрос {number}",description=first_queston.text,color=0x228b22), components=component)
        while aki.progression <= 80 and stats:
            try:

                btn = await bot.wait_for("button_click", check=check, timeout=90)
                #if btn.component.custom_id
                #await asyncio.sleep(3)
                if btn.component.custom_id == "STOP":
                    win = aki.win()
                    if not win:
                        stats=False
                        await btn.response.defer()
                        return await ctx.edit_original_response(embed=disnake.Embed(title="Вы закончили игру.",color=disnake.Color.red()),components=None)
                    stats = False
                    await btn.response.defer()

                    return await ctx.edit_original_response(embed=disnake.Embed(title="Вы закончили игру.",description=f"На данный момент Акинатор считает что это {translator.translate(win.name, dest='ru').text}!",color=disnake.Color.red()),components=None)

                answer = Answer.from_str(btn.component.custom_id)
                aki.answer(answer)
                number += 1
                #await btn.response.defer()
                await ctx.edit_original_response(embed=disnake.Embed(title=f"Вопрос {number}",description=translator.translate(aki.question, dest="ru").text, color=0x228b22), components=component)
            except asyncio.TimeoutError:
                win = aki.win()
                #await ctx.send(embed=disnake.Embed(title="Игра закончена!",description=f"Вы долго не отвечали.\nЗа эти вопросы Акинатор считает что это {translator.translate(win.name, dest='ru').text}.",color=disnake.Color.red()))
                stats = False
        win = aki.win()
        if win:
            await ctx.edit_original_response(embed=disnake.Embed(title=f"Это {translator.translate(win.name, dest='ru').text}!",description=f'{translator.translate(win.description, dest="ru").text}',color=disnake.Color.red()).set_image(url = win.absolute_picture_path), components=None)
            stats = False

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="ban", description="Забанить кого либо")
    @commands.has_permissions(ban_members = True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx, member: disnake.Member, reason="Была не указана."):
        await ctx.response.defer()
        try:
            #await member.send(embed=disnake.Embed(title=f"Здравствуй, {member.name}!",description=f"Вы были забанены на сервере **{ctx.guild.name}** по причине {reason}\nВы можете попробовать обратится к пользователям того сервера\nЗа помощью, если вы были забанены по ошибке."))
            await member.ban(reason=reason)
        except:
            return await ctx.send(embed=disnake.Embed(title="Извините, ошибка",description="У меня не хватает прав\nВозможна другая причина ошибки.",color=disnake.Color.red()))
        await ctx.send(embed=disnake.Embed(title="<:correctCheckmark:1047244074350018700> Успешно",description=f"{member.name} теперь в бане",color=disnake.Color.green()))

    @commands.slash_command(name="unban", description="Разбанить кого либо.")
    @commands.has_permissions(ban_members = True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx, member_id):
        await ctx.response.defer()
        try:
            member_id = int(member_id)
        except ValueError:
            return await ctx.send(embed=disnake.Embed(title="Ошибка",description="Вы не правильно использовали команду. Правильное её использование:\n`/unban [member id]`\nПримечание: member id должен быть числом.",color=disnake.Color.red()))
        user = disnake.Object(id=member_id)
        try:
            await ctx.guild.unban(user)
        except:
            return await ctx.send(embed=disnake.Embed(title="Извините, ошибка",description="У меня не хватает прав\nВозможна другая причина.",color=disnake.Color.red()))
        await ctx.send(embed=disnake.Embed(title="<:correctCheckmark:1047244074350018700> Успешно!",description=f"{user} теперь разбанен!",color=disnake.Color.green()))
        return

    @commands.slash_command(name="kick", description="Выгнать кого с сервера.")
    @commands.has_permissions(kick_members = True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self, ctx, member: disnake.Member, reason = "не указана"):
        await ctx.response.defer()
        try:
            await member.kick()
        except:
            return await ctx.send(embed=disnake.Embed(title="Извините, ошибка",description="У меня не хватает прав\nВозможна другая причина.",color=disnake.Color.red()))
        try:
            await member.send(embed=disnake.Embed(title=f"Здравствуй, {member.name}!",description=f"Вы были выгнаны с сервера **{ctx.guild.name}** по причине {reason}\nВы можете попробовать обратится к пользователям того сервера\nЗа помощью, если вы были выгнаны по ошибке."))
        except:
            print(f"[Bot Logistic] I'm can't send kick message to {member.name}#{member.discriminator}. Sorry.")
        await ctx.send(embed=disnake.Embed(title="<:correctCheckmark:1047244074350018700> Успешно!",description=f"{member.mention} больше нет на сервере!", color=disnake.Color.green()))

    @commands.slash_command(name="mute",description="Заглушить кого либо на сервере")
    @commands.has_permissions(moderate_members = True)
    @commands.bot_has_permissions(moderate_members=True)
    async def mute(self, ctx, member: disnake.Member, time: int):
        await ctx.response.defer()
        try:
            await member.timeout(duration=datetime.timedelta(minutes=time))
        except:
            return await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка!",description="У меня не хватает прав.\nВозможна другая причина.",color=disnake.Color.red()))

        await ctx.send(embed=disnake.Embed(title="<:correctCheckmark:1047244074350018700> Успешно",description=f"Теперь {member.name} находиться в мьюте на {time} минут."))

    @commands.slash_command(name="warn",description="Выдать варн пользователю")
    @commands.has_permissions(moderate_members = True)
    async def warn(self, ctx, пользователь: disnake.Member, причина="не указана"):
        await ctx.response.defer()
        member = пользователь
        reason = причина
        special = 0
        with sqlite3.connect("database.db") as db:
            cursor = db.cursor()
            cursor.execute("INSERT INTO warns(guild_id, user_id, reason) VALUES(?, ?, ?)", (ctx.guild.id, member.id, reason))
        with sqlite3.connect("database.db") as db:
            cursor = db.cursor()
            for special_id, guild, user, reas in cursor.execute("SELECT * FROM warns"):
                if user == member.id:
                    special = special_id

        datet = datetime.datetime
        date = datet.utcnow()
        utc_time = calendar.timegm(date.utctimetuple())

        await ctx.send(embed=disnake.Embed(title="<:correctCheckmark:1047244074350018700> Успешно",description=f"Варн успешно нанесён на пользователя {member.mention}!\nПроизошло это <t:{utc_time}:R>").add_field(name="Номер случая",value=f"{special}"))

    @commands.slash_command(name="warns",description="Увидеть список варном на этом сервере")
    async def warns(self, ctx):
        await ctx.response.defer()
        message = []
        users = []
        with sqlite3.connect("database.db") as db:
            cursor = db.cursor()
            for special_id, guild, user, reas in cursor.execute("SELECT * FROM warns"):
                if guild == ctx.guild.id:
                    users.append(user)
                    message.append(f"Номер случая - {special_id}:\n    Пользователь - {self.bot.get_user(user).mention}\n    Причина - {reas}\n")
        if users == []:
            return await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка",description="На сервере ещё нет варнов.",color=disnake.Color.red()))
        embed = disnake.Embed(title="Таблица варнов🔍", description="\n".join(list(map(str, message))))
        # embed.add_field(name="Айди юзера", value="\n".join(list(map(str, user_id))))
        # embed.add_field(name="Номер случая", value="\n".join(list(map(str, specials))))
        # embed.add_field(name="Причина", value="\n".join(list(map(str, reason))))
        await ctx.send(embed=embed)

    @commands.slash_command(name="unwarn",description="Снять варн с пользователя")
    @commands.has_permissions(moderate_members = True)
    async def unwarn(self,ctx,номер_случая):
        await ctx.response.defer()
        special = номер_случая
        st = False
        try:
            special = int(special)
        except:
            return await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка",description="Номер случая должен быть числом!",color=disnake.Color.red()), ephemeral=True)
        try: #Пробуем
            with sqlite3.connect("database.db") as db: #Открываем связь с дб
                cursor = db.cursor() # Создаём курсор
                #for guild_id in cursor.execute("SELECT guild_id FROM warns WHERE special_id = ?", (int(special),)):
                    #if int(guild_id) == ctx.guild.id:
                cursor.execute("DELETE FROM warns WHERE special_id = ?", (int(special),)) # Даём запрос на удаление
                await ctx.send(embed=disnake.Embed(title="<:correctCheckmark:1047244074350018700> Успешно",description=f"Номер случая {special} был удалён из базы данных",color=0x228b22))
                    #else:
                        #return await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка",description="Этот варн с другого сервера!",color=disnake.Color.red()))
        except sqlite3.Error: #Если ошибка
            return await ctx.send("Неверный номер случая!")

    @commands.slash_command(name="purge",description="Очистить канал")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purg(self, ctx, count: int = commands.Param(description="Сколько сообщений удалить?")):
        await ctx.response.defer()
        await ctx.channel.purge(limit=int(count))
        await ctx.send(f"<:correctCheckmark:1047244074350018700> Успешно очищено {count} сообщений!", ephemeral=True)


class Utils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="profile",description="Проверить свой профиль")
    async def profile(self, ctx, member: disnake.Member = None):
        await ctx.response.defer()
        if not member:
            member = ctx.author
        scopes = 0
        try:
            scopes = Memory.read(f"scope/{member.id}balls.txt")
        except:
            scopes = 0
        balance = 0
        users = None
        with sqlite3.connect("database.db") as db:
            cursor = db.cursor()
            for guild, user, bal in cursor.execute("SELECT * FROM balances"):
                if guild == ctx.guild.id:
                    if user == member.id:
                        users = user
                        balance = bal
        if not users:
            with sqlite3.connect("database.db") as db:
                cursor = db.cursor()
                cursor.execute("INSERT INTO balances VALUES(?, ?, ?)", (ctx.guild.id, member.id, 0))
            balance = 0
        if not balance:
            balance = 0
        t = member.status
        if t == disnake.Status.online:
            d = "🟢 В сети"

        t = member.status
        if t == disnake.Status.offline:
            d = "⚪ Не в сети"

        t = member.status
        if t == disnake.Status.idle:
            d = "🟠 Не активен"

        t = member.status
        if t == disnake.Status.dnd:
            d = "🔴 Не беспокоить"

        img = Image.new('RGBA', (500, 170), '#000000')
        backgr = ["https://cdn.glitch.global/5fcfa7e8-8436-4acd-a852-e721cd1b531e/1614397342_47-p-temnii-multyashnii-fon-64.png?v=1670188383348","https://cdn.glitch.global/5fcfa7e8-8436-4acd-a852-e721cd1b531e/1622768497_26-phonoteka_org-p-noch-art-minimalizm-krasivo-28.png?v=1670188403979","https://cdn.glitch.global/5fcfa7e8-8436-4acd-a852-e721cd1b531e/i.png?v=1670188415480"]
        r = requests.get(random.choice(backgr), stream = True)
        r = Image.open(io.BytesIO(r.content))
        r = r.convert("RGBA")
        r = r.resize((500, 170))
        img.paste(r, (0, 0, 500, 170))
        url = str(member.avatar.url)
        r = requests.get(url, stream = True)
        r = Image.open(io.BytesIO(r.content))
        r = r.convert('RGBA')
        r = r.resize((100, 100))
        img.paste(r, (15, 15, 115, 115))
        idraw = ImageDraw.Draw(img)        
        name = member.name
        headline = ImageFont.truetype('comfortaa.ttf', size = 25)
        undertext = ImageFont.truetype('comfortaa.ttf', size = 13)
        idraw.text((125, 15), f'{name}', font=headline, fill="#ffffff")
        idraw.text((125, 50), f'#{member.discriminator}', font=undertext, fill="#ffffff")
        idraw.text((125, 70), f'ID: \n{member.id}', font = undertext, fill="#ffffff")
        idraw.text((125, 110), f'Статус: {d}', font = undertext, fill="#ffffff")
        idraw.text((125, 130), f"Кол-во очков: {scopes}", font = undertext, fill="#ffffff")
        idraw.text((125, 150), f"Баланс: {int(balance)}", font=undertext, fill="#ffffff")
        idraw.text((10, 155), f'{self.bot.user.name} Draw\'s', font=undertext, fill="#ffffff")
        img.save('user_card.png')
        await ctx.send(file=disnake.File("user_card.png"))

    @commands.slash_command(name="jacque",description="Генерирует изображение с популярным Джак Фрэско")
    async def jacque(self, ctx, текст = commands.Param(description="Что будет говорить Джак Фрэско?")):
        await ctx.response.defer()
        cent = 480 / 2
        cent = cent / len(текст)
        try:
            img = Image.new("RGBA", (480, 270), "#000000")
            r = requests.get("https://cdn.glitch.global/5fcfa7e8-8436-4acd-a852-e721cd1b531e/imgonline-com-ua-convertH9QmkkWjlGPN.jpg?v=1671019870556", stream=True)
            r = Image.open(io.BytesIO(r.content))
            r = r.convert("RGBA")
            img.paste(r, (0,0,480,270))
            draw = ImageDraw.Draw(img)
            font = ImageFont.truetype("ComicSans.ttf", size=20)
            draw.text((cent,135), f"{текст}", font=font, fill="#000000")
            draw.text((10, 240), f"{self.bot.user.name} Draw\'s", font=font, fill="#000000")
            img.save("jacque.png")
        except:
            return await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка",description="Не удалось выполнить данное действие.",color=disnake.Color.red()))
        await ctx.send(file=disnake.File("jacque.png"))

    @commands.slash_command(name="passed", description="Делает вашу аватарку в стиль GTA, миссия выполнена")
    async def passed(self, ctx, участник: disnake.Member = None):
        member = участник
        if not member:
            member = ctx.author
        await ctx.response.defer()
        request = requests.get(f"https://some-random-api.ml/canvas/overlay/passed?avatar={member.avatar.url}")
        json_load = request.url
        await ctx.send(embed=disnake.Embed(title="🔍Результат обработки").set_image(url=json_load))

    @commands.slash_command(name="wasted", description="Делает вашу аватарку в стиль GTA, миссия провалена")
    async def wasted(self, ctx, участник: disnake.Member = None):
        member = участник
        if not member:
            member = ctx.author
        await ctx.response.defer()
        request = requests.get(f"https://some-random-api.ml/canvas/overlay/wasted?avatar={member.avatar.url}")
        json_load = request.url
        await ctx.send(embed=disnake.Embed(title="🔍Результат обработки").set_image(url=json_load))

    @commands.slash_command(name="lgbt", description="Делает вам ЛГБТ аватарку")
    async def lgbt(self, ctx, участник: disnake.Member = None):
        member = участник
        if not member:
            member = ctx.author
        await ctx.response.defer()
        request = requests.get(f"https://some-random-api.ml/canvas/overlay/gay?avatar={member.avatar.url}")
        json_load = request.url
        await ctx.send(embed=disnake.Embed(title="🔍Результат обработки").set_image(url=json_load))

    @commands.slash_command(name="jail", description="Делает вам аватарку, будто вы в тюрьме")
    async def jail(self, ctx, участник: disnake.Member = None):
        member = участник
        if not member:
            member = ctx.author
        await ctx.response.defer()
        request = requests.get(f"https://some-random-api.ml/canvas/overlay/jail?avatar={member.avatar.url}")
        json_load = request.url
        await ctx.send(embed=disnake.Embed(title="🔍Результат обработки").set_image(url=json_load))

    @commands.slash_command(name="ussr", description="Переделывает вашу аватарку в стиле СССР")
    async def ussr(self, ctx, участник: disnake.Member = None):
        member = участник
        if not member:
            member = ctx.author
        await ctx.response.defer()
        request = requests.get(f"https://some-random-api.ml/canvas/overlay/comrade?avatar={member.avatar.url}")
        json_load = request.url
        await ctx.send(embed=disnake.Embed(title="🔍Результат обработки").set_image(url=json_load))

    @commands.slash_command(name="triggered", description="Делает гифку вашей аватарки в стиле TRIGGERED")
    async def triggered(self, ctx, участник: disnake.Member = None):
        member = участник
        if not member:
            member = ctx.author
        await ctx.response.defer()
        request = requests.get(f"https://some-random-api.ml/canvas/overlay/triggered?avatar={member.avatar.url}")
        json_load = request.url
        await ctx.send(embed=disnake.Embed(title="🔍Результат обработки").set_image(url=json_load))

    @commands.slash_command(name="pixelate",description="Пиксилизирует ваш аватар")
    async def pixelate(self, ctx, участник: disnake.Member = None):
        member = участник
        if not member:
            member = ctx.author
        await ctx.response.defer()
        request = requests.get(f"https://some-random-api.ml/canvas/misc/pixelate?avatar={member.avatar.url}")
        await ctx.send(embed=disnake.Embed(title="🔍Результат обработки").set_image(url=request.url))

    @commands.slash_command(name="youtube-comment",description="Делает в стиле вас коментарий с ютуба")
    async def comment(self, ctx, коментарий, ник, аватар: disnake.Member = commands.Param(description="Вы можете указать с какого участника будет взят аватар")):
        avatar = аватар
        nick = ник
        if not avatar:
            avatar = ctx.author
        await ctx.response.defer()
        comment = коментарий
        request = requests.get(f"https://some-random-api.ml/canvas/misc/youtube-comment?avatar={avatar.avatar.url}&username={nick}&comment={comment}")
        await ctx.send(embed=disnake.Embed(title="🔍Результат обработки").set_image(url=request.url))

    @commands.slash_command(name="voice",description="Создать озвучку")
    async def voice(self, ctx, текст = commands.Param(description="🔍 Какой текст озвучить?")):
        text = текст
        tts = gTTS(text=text, lang="ru")
        tts.save("voice.mp3")
        await ctx.send("🔍Результат",file=disnake.File("voice.mp3"))

    @commands.slash_command(name="encode",description="Надо зашифровать текст в base64? Легко!")
    async def encode(self, ctx, текст = commands.Param(description="Текст, который надо зашифровать")):
        request = requests.get(f"https://some-random-api.ml/others/base64?encode={текст}")
        json_load = json.loads(request.text)
        await ctx.send(embed=disnake.Embed(title="🔍Результат",description=json_load["base64"],color=0x228b22))

    @commands.slash_command(name="decode",description="Надо расшифровать текст из base64? Легко!")
    async def decode(self, ctx, текст = commands.Param(description="Текст base64")):
        request = requests.get(f"https://some-random-api.ml/others/base64?decode={текст}")
        json_load = json.loads(request.text)
        await ctx.send(embed=disnake.Embed(title="🔍Результат",description=json_load["text"],color=0x228b22))

    @commands.slash_command(name="joke",description="Возвращает шутку")
    async def joke(self, ctx, язык = commands.Param(default="ru", description="На каком языке вы хотите увидеть шутку?", choices = [disnake.OptionChoice("Русский","ru"),disnake.OptionChoice("English","en"),disnake.OptionChoice("Украiньска","uk")])):
        await ctx.response.defer()
        api_result = requests.get("https://some-random-api.ml/others/joke")
        results = json.loads(api_result.text)
        text = translator.translate(results["joke"], dest=язык)
        await ctx.send(embed=disnake.Embed(title=f"{text.text}",description="Шутка взята с сайта **None**"))

    @commands.slash_command(name="poll",description="Запустить голосование.")
    async def poll(self, ctx, заголовок, sel1, sel2, sel3 = None, sel4 = None, sel5 = None, sel6 = None, sel7 = None, sel8 = None, sel9 = None, sel10 = None):
        await ctx.response.defer()
        args_do = [sel1, sel2, sel3, sel4, sel5,sel6,sel7,sel8,sel9,sel10]
        text = []
        emojis = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
        count = 1
        lis_count = 0
        for arg in args_do:
            if arg:
                text.append(f"{count}. {arg}")
                count += 1
                lis_count += 1
        text_af = "\n".join(list(map(str, text)))
        msg = await ctx.send(embed=disnake.Embed(title=f"Пожалуйста, отправьте сообщение для голосовании",description="Я поставлю на это сообщение реакций для голосования", color=0x228b22))
        try:
            def check(msg):
                return msg.guild.id == ctx.guild.id and msg.author.id == ctx.author.id
            msg = await self.bot.wait_for("message", check=check, timeout=60)
            await ctx.edit_original_response(embed=disnake.Embed(title=заголовок,description=text_af,color=0x228b22))
            if lis_count >= 1: await msg.add_reaction("1️⃣")
            if lis_count >= 2: await msg.add_reaction("2️⃣")
            if lis_count >= 3: await msg.add_reaction("3️⃣")
            if lis_count >= 4: await msg.add_reaction("4️⃣")
            if lis_count >= 5: await msg.add_reaction("5️⃣")
            if lis_count >= 6: await msg.add_reaction("6️⃣")
            if lis_count >= 7: await msg.add_reaction("7️⃣")
            if lis_count >= 8: await msg.add_reaction("8️⃣")
            if lis_count >= 9: await msg.add_reaction("9️⃣")
            if lis_count >= 10: await msg.add_reaction("🔟")
        except asyncio.TimeoutError:
            await ctx.edit_original_response(embed=disnake.Embed(title="Вы слишком долго отправляли сообщение!",description="<:wrongCheckmark:1047244133078675607>Ошибка",color=disnake.Color.red()))

    @commands.slash_command(name="random",description="Хотите выбрать что то рандомное? Используйте команду!")
    async def rando(self, ctx, вариации = commands.Param(description="Укажите вариации через пробел.")):
        select = random.choice(вариации.split())
        await ctx.send(embed=disnake.Embed(title="Я выбираю...", color=0x228b22))
        await asyncio.sleep(3)
        await ctx.edit_original_response(embed=disnake.Embed(title="Я выбираю",description=select + "!",color=0x228b22))

    @commands.slash_command(name="new-year",description="Через сколько дней новый год?")
    async def new_year(self, ctx):
        await ctx.send(embed=disnake.Embed(title="С наступающим новым годом!🎉",description="Новый год уже <t:1672520400:R>",color=0x4500ff))

    @commands.slash_command(name="donate",description="Поддержать создателей бота")
    async def donate(self, ctx):
        await ctx.send(embed=disnake.Embed(title="Мы будем бесконечно благодарны даже 10 рублям!",description="DonationAlerts - [**нажмите**](https://www.donationalerts.com/r/tjma)\nВозможно будет добавлена оплата через наш сайт.",color=0x228b22), ephemeral=True)

class BotSettings(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(name="set-welcome-channel", description="[АДМИН] Устанавливает канал для приветствеующих сообщений")
    @commands.has_permissions(manage_guild = True)
    async def welcome_channel(self, ctx, канал: disnake.TextChannel):
        await ctx.response.defer()
        channel = канал
        try:
            message = await channel.send("https://tenor.com/view/harry-potter-funny-harrypotter-voldemort-gif-19286790")
        except:
            return await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка",description="Кажеться, я не могу отправлять сообщения в этот канал",color=disnake.Color.red()))
        else:
            await message.delete()
        try:
            Memory.write(f"channels/{ctx.guild.id}welcomechannel.txt", channel.id)
        except:
            return await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка",description="Не удалось записать канал в память\nОбратитесь на наш сервер за помощью.", color=disnake.Color.red()))
        await ctx.send(embed=disnake.Embed(title="<:correctCheckmark:1047244074350018700> Успешно",description=f"Теперь уведомления о зашедших участниках будут приходить в <#{channel.id}>\nОбразец сообщения, которое будет отправляться:\n**Ещё не сделано...**\n[Подробнее о том, как отключить это.](https://0xb1.glitch.me/docs/1927.html)",color=0x228b22))

    @commands.slash_command(name="set-bye-channel", description="[АДМИН] Устанавливает канал для прощальных сообщений")
    @commands.has_permissions(manage_guild = True)
    async def bye_channel(self, ctx, канал: disnake.TextChannel):
        await ctx.response.defer()
        channel = канал
        try:
            message = await channel.send("https://tenor.com/view/harry-potter-funny-harrypotter-voldemort-gif-19286790")
        except:
            return await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка",description="Кажеться, я не могу отправлять сообщения в этот канал",color=disnake.Color.red()))
        else:
            await message.delete()
        try:
            Memory.write(f"channels/{ctx.guild.id}byechannel.txt", channel.id)
        except:
            return await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка",description="Не удалось записать канал в память\nОбратитесь на наш сервер за помощью.", color=disnake.Color.red()))
        await ctx.send(embed=disnake.Embed(title="<:correctCheckmark:1047244074350018700> Успешно",description=f"Теперь уведомления о ушедших участниках будут приходить в <#{channel.id}>\nОбразец сообщения, которое будет отправляться:\n**Ещё не сделано...**\n[Подробнее о том, как отключить это.](https://0xb1.glitch.me/docs/1927.html)",color=0x228b22))

    @commands.slash_command(name="set-daily",description="[АДМИН] Установить ежедневный бонус")
    @commands.has_permissions(manage_guild = True)
    async def set_daily(self, ctx, сумма):
        await ctx.response.defer()
        summ = сумма
        try:
            summ = int(summ)
        except:
            return await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка",description="Вы указали **НЕ** число", color=disnake.Color.red()))
        try:
            Memory.write(f"daily/{ctx.guild.id}summ-of-daily.txt", str(summ))
        except:
            return await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка",description="Не удалось записать число в память.",color=disnake.Color.red()))

        await ctx.send(embed=disnake.Embed(title="<:correctCheckmark:1047244074350018700> Успешно",description="Теперь каждый день участникам по ихнему желанию будет даваться эта сумма."))
    
    @commands.slash_command(name="set-anti-badwords",description="Включить/выключить преды за плохие слова.")
    @commands.has_permissions(manage_guild = True)
    async def set_anti_badwords(self, ctx):
        await ctx.response.defer()
        if not ctx.guild:
            return await ctx.send("Удивительные факты: Я не могу включить поиск плохих слов в ЛС.",ephemeral=True)

        Memory.write(f"badwords/{ctx.guild.id}.txt", "you")
        await ctx.send(embed=disnake.Embed(title="<:correctCheckmark:1047244074350018700> Успешно",description="Теперь пользователям за плохие слова будут выдаваться преды.",color=0x228b22))

    @commands.slash_command(name="set-work-price",description="Установить получаемую сумму за работу, 0 если отключить")
    @commands.has_permissions(manage_guild = True)
    async def set_work_price(self, ctx, сумма: int = commands.Param(description="Какую сумму будут получать участники?")):
        Memory.write(f"works/{ctx.guild.id}.txt", сумма)
        await ctx.send(embed=disnake.Embed(title="<:correctCheckmark:1047244074350018700> Успешно",description="Теперь за работу будет выдаваться эта сумма."))

    @commands.slash_command(name="disable-set", description="[АДМИН] Отключить какие либо настройки.")
    @commands.has_permissions(manage_guild = True)
    async def disable_sets(self, ctx, настройка = commands.Param(description="Укажите, какую настройку надо отключить", choices=[disnake.OptionChoice(name="Уведомления об зашедших",value="welcome_messages"),disnake.OptionChoice(name="Уведомления об ушедших",value="bye_messages"),disnake.OptionChoice(name="Варны за плохие слова",value="badwords")])):
        await ctx.response.defer()
        setting = настройка
        if setting == "welcome_messages":
            if os.path.isfile(f"channels/{ctx.guild.id}welcomechannel.txt"):
                os.remove(f"channels/{ctx.guild.id}welcomechannel.txt")
            else:
                return await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка",description="Уведомления о пришедших участниках уже были отключены.", color=disnake.Color.red()))
            await ctx.send(embed=disnake.Embed(title=f"<:correctCheckmark:1047244074350018700> Успешно",description=f"Уведомления об пришедших участниках больше не будут приходить.", color=0x228b22))
        if setting == "bye_messages":
            if os.path.isfile(f"channels/{ctx.guild.id}byechannel.txt"):
                os.remove(f"channels/{ctx.guild.id}byechannel.txt")
            else:
                return await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка",description="Уведомления об ушедших участниках уже были отключены.", color=disnake.Color.red()))
            await ctx.send(embed=disnake.Embed(title=f"<:correctCheckmark:1047244074350018700> Успешно",description=f"Уведомления об ушедших участниках больше не будут приходить.", color=0x228b22))
        if setting == "badwords":
            if os.path.isfile(f"badwords/{ctx.guild.id}.txt"):
                os.remove(f"badwords/{ctx.guild.id}.txt")
            else:
                return await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка",description="Варны за плохие слова уже были отключены.", color=disnake.Color.red()))
            await ctx.send(embed=disnake.Embed(title=f"<:correctCheckmark:1047244074350018700> Успешно",description=f"Варны за плохие слова больше не будут выдаваться.", color=0x228b22))



class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="balance",description="Посмотреть свой баланс")
    async def balance(self, ctx, member: disnake.Member = None):
        await ctx.response.defer()
        if not member: member = ctx.author
        users = 0
        bals = 0
        with sqlite3.connect("database.db") as db:
            cursor = db.cursor()
            for guild, user, bal in cursor.execute("SELECT * FROM balances"):
                if guild == ctx.guild.id:
                    if user == member.id:
                        users = user
                        bals = bal

        if not users:
            with sqlite3.connect("database.db") as db:
                cursor = db.cursor()
                cursor.execute("INSERT INTO balances VALUES(?, ?, ?)", (ctx.guild.id, member.id, 0))
            bals = 0
        if not bals:
            bals = 0

        await ctx.send(embed=disnake.Embed(title=f"Баланс пользователя **{member.name}**",description=f"Баланс: **{bals}**<:dollar:1051974269296451684>",color=0x228b22))

    @commands.slash_command(name="work",description="Пойти работать")
    @commands.cooldown(1, 120, commands.BucketType.user)
    async def work(self, ctx):
        await ctx.response.defer()
        work_price = 0
        try:
            work_price = Memory.read(f"works/{ctx.guild.id}.txt")
        except:
            return await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка",description="Разработчики не установили цену, а для меня это значит что они отключили экономику\nЕсли вы считаете, что на сервере должна присутствовать экономика, обратитесь к администраций сервеа",color=disnake.Color.red()))
        work_price = int(work_price)
        if work_price == 0:
            return await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка",description="На сервере отключена экономика.",color=disnake.Color.red()))
        await ctx.send(embed=disnake.Embed(title="Работаем...",color=0x228b22))
        await asyncio.sleep(10)
        with sqlite3.connect("database.db") as db:
            cursor = db.cursor()
            cursor.execute("UPDATE balances SET user_balance = user_balance + ? WHERE guild_id = ? AND user_id = ?", (work_price, ctx.guild.id, ctx.author.id))
        await ctx.edit_original_response(embed=disnake.Embed(title="<:correctCheckmark:1047244074350018700> Успешно",description=f"Вы получили {work_price}<:dollar:1051974269296451684>",color=0x228b22))

    @commands.slash_command(name="daily",description="Ежедневная награда")
    @commands.cooldown(1, 72000, commands.BucketType.user)
    async def daily(self, ctx):
        await ctx.response.defer()
        summ = 0
        work_price = 0
        try:
            summ = Memory.read(f"daily/{ctx.guild.id}summ-of-daily.txt")
        except:
            return await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка",description="Разработчики не указывали сумму ни разу, и да бы не создать им проблем, я вам откажу.",color=disnake.Color.red()))
        try:
            work_price = Memory.read(f"works/{ctx.guild.id}.txt")
        except:
            return await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка",description="На этом сервере отключена экономика"))
        summ = int(summ)
        if summ == 0:
            return await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка",description="Ежедневная награда на этом сервере отсутствует",color=disnake.Color.red()))
        with sqlite3.connect("database.db") as db:
            cursor = db.cursor()
            cursor.execute("UPDATE balances SET user_balance = user_balance + ? WHERE guild_id = ? AND user_id = ?", (summ, ctx.guild.id, ctx.author.id))
        await ctx.send(embed=disnake.Embed(title="<:correctCheckmark:1047244074350018700> Успешно",description="Вы получили свой ежедневный бонус, следующий бонус вы получите через 72000 секунд(20ч)!",color=0x228b22))

    @commands.slash_command(name="add-money", description="Добавить деньги на счёт какого либо пользователя")
    @commands.has_permissions(moderate_members = True)
    async def add_money(self, ctx, участник: disnake.Member, сумма: int):
        await ctx.response.defer()
        summ = 0
        with sqlite3.connect("database.db") as db:
            cursor = db.cursor()
            cursor.execute("UPDATE balances SET user_balance = user_balance + ? WHERE guild_id = ? AND user_id = ?", (сумма, ctx.guild.id, участник.id))
            for guild, user, suma in cursor.execute("SELECT * FROM balances WHERE guild_id = ? AND user_id = ?", (ctx.guild.id, участник.id)):
                if guild == ctx.guild.id:
                    if user == участник.id:
                        summ = suma

        await ctx.send(embed=disnake.Embed(title="<:correctCheckmark:1047244074350018700> Успешно",description=f"Теперь у участника {summ}<:dollar:1051974269296451684>!",color=0x228b22))

    @commands.slash_command(name="reduce-money", description="Убавить деньги со счёта какого либо пользователя либо всего сервера.")
    @commands.has_permissions(moderate_members = True)
    async def reduce_money(self, ctx, сумма: int = commands.Param(description="Какую сумму хотите забрать?"), участник: disnake.Member = commands.Param(description="Укажите у какого участника, не указывайте если у всего сервера")):
        await ctx.response.defer()
        summ = 0
        with sqlite3.connect("database.db") as db:
            cursor = db.cursor()
            cursor.execute("UPDATE balances SET user_balance = user_balance - ? WHERE guild_id = ? AND user_id = ?", (сумма, ctx.guild.id, участник.id))
            for guild, user, suma in cursor.execute("SELECT * FROM balances WHERE guild_id = ? AND user_id = ?", (ctx.guild.id, участник.id)):
                if guild == ctx.guild.id:
                    if user == участник.id:
                        summ = suma
        await ctx.send(embed=disnake.Embed(title="<:correctCheckmark:1047244074350018700> Успешно",description="Теперь у пользователя {} <:dollar:1051974269296451684>!".format(suma), color=0x228b22))

    @commands.slash_command(name="pay",description="Перевести деньги кому либо.")
    async def pay(self, ctx, участник: disnake.Member = commands.Param(description="Какому участнику хотите отправить (command.Args.summ) валюты?"), сумма: int = commands.Param(description="Какую сумму хотите отправить участнику?")):
        member = участник
        summ = сумма
        with sqlite3.connect("database.db") as db:
            cursor = db.cursor()
            for guild, user, balance in cursor.execute("SELECT * FROM balances WHERE user_id = ? AND guild_id = ?",(ctx.author.id, ctx.guild.id)):
                if int(balance) < int(summ):
                    return await ctx.send(embed=disnake.Embed(title="Ошибка",description="У вас мало денег нет счету"))
            cursor.execute("UPDATE balances SET user_balance = user_balance - ? WHERE guild_id = ? AND user_id = ?", (summ, ctx.guild.id, ctx.author.id))
            cursor.execute("UPDATE balances SET user_balance = user_balance + ? WHERE guild_id = ? AND user_id = ?", (summ, ctx.guild.id, member.id))
        await ctx.send(embed=disnake.Embed(title="<:correctCheckmark:1047244074350018700> Успешно",description=f"Вы перевели свои **{summ}** <:dollar:1051974269296451684> пользователю {member.mention}!",color=0x228b22))

    @commands.slash_command(name="ping",description="Проверка на работоспособность бота.")
    async def ping(self, ctx):
        ping = int(self.bot.latency * 1000)
        st = "Не определено"
        col = 0xffffff
        if ping > 1:
            st = "Отлично!"
            col = 0x00bd19
        if ping > 70:
            st = "Очень хорошо!"
            col = 0x61bd00
        if ping > 140:
            st = 'Нормально.'
            col = 0x9dbd00
        if ping > 210:
            st = "Плохо."
            col = 0xbdaa00
        if ping > 280:
            st = "Довольно плохо."
            col = 0xffaa00
        if ping > 350:
            st = "ОЧЕНЬ ПЛОХО"
            col = 0xff0000
        await ctx.send(embed=disnake.Embed(title="Понг!",description=f"Моя задержка в связи: {ping}ms\nЭто {st}",color=col))

    @commands.slash_command(name="guilds-list",description="Пускай только админы знают что делает эта команда...", guild_ids=[1047126198330859580])
    async def guilds_list(self, ctx):
        if ctx.author.id == 1047108944721616916 or ctx.author.id == 848551340925517914 or ctx.author.id == 767076912023207938:
            await ctx.send(embed=disnake.Embed(title="Сервера, на которых я нахожусь",description=f"{bot.guilds}"), ephemeral=True)
        else:
            await ctx.send("А куда мы лезем?))",ephemeral=True)

class Relationships(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="hug",description="Обнимашки с другим человеком")
    async def hug(self, ctx, участник: disnake.Member = commands.Param(description="Кого хотите обнять?")):
        if ctx.author.id == участник.id:
            return await ctx.send("Ты не можешь обнять сам себя.",ephemeral=True)
        request = requests.get("https://some-random-api.ml/animu/hug")
        json_load = json.loads(request.text)
        await ctx.send(embed=disnake.Embed(title=f"**{ctx.author.name}** обнял **{участник.name}**",color=0x228b22).set_image(url=json_load["link"]))

    @commands.slash_command(name="pat",description="Погладить другого человека")
    async def pat(self, ctx, участник: disnake.Member = commands.Param(description="Кого хотите погладить? <:Magic:1047241900370956298>")):
        if ctx.author.id == участник.id:
            return await ctx.send("Ты не можешь погладить сам себя.",ephemeral=True)
        request = requests.get("https://some-random-api.ml/animu/pat")
        json_load = json.loads(request.text)
        await ctx.send(embed=disnake.Embed(title=f"**{ctx.author.name}** гладит **{участник.name}**",color=0x228b22).set_image(url = json_load["link"]))



class RolePlayHelps(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="acc-register", description="Создать нового персонажа для рп")
    @commands.bot_has_permissions(manage_webhooks = True)
    async def acc_reg(self, ctx, имя = commands.Param(description="Какое имя будет у персонажа?")):
        await ctx.response.defer()
        channel_webhooks = await ctx.channel.webhooks()
        for webhook in channel_webhooks:
            if webhook.user == bot.user and webhook.name == имя:
                return await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка",description="Такой персонаж уже вроде существует, не?",color=disnake.Color.red()))
        try:
            webhook = await ctx.channel.create_webhook(name=имя)
        except disnake.errors.HTTPException:
            await ctx.send("Слишком много HTTP запросов на данный момент, простите...")
        else:
            await ctx.send(embed=disnake.Embed(title="<:correctCheckmark:1047244074350018700> Успешно",description="Теперь используя никнейм персонажа, вы можете отправлять сообщения от его имени в этом канале!",color=0x228b22))

    @commands.slash_command(name="acc-send",description="Отправить что то от имени персонажа")
    @commands.bot_has_permissions(manage_webhooks = True)
    async def acc_send(self, ctx, имя = commands.Param(description="Напомните мне имя вашего персонажа..."), сообщение = commands.Param(description="Что хотите отправить?")):
        #await ctx.response.defer()
        channel_webhooks = await ctx.channel.webhooks()
        my_webhook = None
        avatar_url = None
        for webhook in channel_webhooks:
            if webhook.user == bot.user and webhook.name == имя:
                my_webhook = webhook
        if not my_webhook:
            return await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка",description="Такого персонажа не существует!",color=disnake.Color.red()), ephemeral=True)
        try:
            try:
                avatar_url = Memory.read(f"avatars/{ctx.channel.id}{имя}webhook.txt")
            except:
                avatar_url = None
            if not avatar_url:
                await my_webhook.send(content = сообщение)
            else:
                await my_webhook.send(content=сообщение, avatar_url=avatar_url)
        except disnake.errors.HTTPException:
            await ctx.send("Слишком много HTTP запросов на данный момент, простите...")
        else:
            await ctx.send(embed=disnake.Embed(title="<:correctCheckmark:1047244074350018700> Успешно",description="Вы отправили своё сообщение от имени персонажа!",color=0x228b22),ephemeral=True)

    @commands.slash_command(name="acc-update-avatar",description="Изменить аватар персонажу")
    @commands.has_permissions(manage_webhooks = True)
    async def acc_upd_atar(self, ctx, имя = commands.Param(description="Какому персонажа меняем аватар?")):
        await ctx.response.defer()
        channel_webhooks = await ctx.channel.webhooks()
        my_webhook = None
        for webhook in channel_webhooks:
            if webhook.user == bot.user and webhook.name == имя:
                my_webhook = webhook
        if not my_webhook:
            return await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка",description="Такого персонажа не существует!",color=disnake.Color.red()), ephemeral=True)
        await ctx.send(embed=disnake.Embed(title="Пожалуйста, отправьте сюда изображение",description="Это изображение будет поставлено как аватар",color=0xffff00))
        status = True
        url = None
        while status:
            msg = await bot.wait_for("message")
            if msg.guild.id == ctx.guild.id:
                if msg.author.id == ctx.author.id:
                    if msg.attachments:
                        status = False
                        url = msg.attachments[0].url
                    else:
                        status = False
                        return await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка",description="Вы не приложили никаких изображений, введите команду и отправьте мне сообщение с вложением",color=disnake.Color.red()))
        Memory.write(f"avatars/{ctx.channel.id}{имя}webhook.txt", url)
        await ctx.send(embed=disnake.Embed(title="<:correctCheckmark:1047244074350018700> Успешно",description="Аватар я запомнил, пора придумывать рп!").add_field(name="Ссылка",value=f"[**Клик**]({Memory.read(f'avatars/{ctx.channel.id}{имя}webhook.txt')})"))

    @commands.slash_command(name="acc-remove",description="Удалить персонажа")
    @commands.has_permissions(manage_webhooks = True)
    @commands.bot_has_permissions(manage_webhooks = True)
    async def acc_rem(self, ctx, имя = commands.Param(description="Какого персонажа удаляем?")):
        my_webhook = None
        channel_webhooks = await ctx.channel.webhooks()
        for webhook in channel_webhooks:
            if webhook.user == bot.user and webhook.name == имя:
                my_webhook = webhook
        if not my_webhook:
            return await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка",description="Такого персонажа не существует!",color=disnake.Color.red()), ephemeral=True)
        try:
            await my_webhook.delete()
            if os.path.isfile(f"avatars/{ctx.channel.id}{имя}webhook.txt"):
                os.remove(f"avatars/{ctx.channel.id}{имя}webhook.txt")

        except disnake.errors.HTTPException:
            await ctx.send("Слишком много HTTP запросов на данный момент, простите...")
        else:
            await ctx.send(embed=disnake.Embed(title="<:correctCheckmark:1047244074350018700> Успешно",description="Этого персонажа больше нет в этом канале!"))


    @commands.slash_command(name="acc-all",description="Посмотреть всех существующих персонажей в канале")
    async def acc_all(self, ctx):
        my_webhooks = []
        channel_webhooks = await ctx.channel.webhooks()
        for webhook in channel_webhooks:
            if webhook.user == bot.user:
                my_webhooks.append(webhook.name)

        await ctx.send(embed=disnake.Embed(title="Все ваши персонажи в этом канале",description="\n".join(list(map(str, my_webhooks))), color=0x228b22))

bot = commands.Bot(command_prefix="xb!", intents=disnake.Intents.all(), sync_commands_debug=True)
bot.remove_command("help")
bot.add_cog(Music(bot))
bot.add_cog(Utils(bot))
bot.add_cog(Moderation(bot))
bot.add_cog(Games(bot))
bot.add_cog(Main(bot))
bot.add_cog(BotSettings(bot))
bot.add_cog(Economy(bot))
bot.add_cog(Relationships(bot))
bot.add_cog(RolePlayHelps(bot))

@bot.user_command(name="Инфо о пользователе")
async def infouser(ctx, member: disnake.User):
    #await ctx.send(embed=disnake.Embed(title=f"Инфо о пользователе **{user.name}**",description=f"Никнеим: **{user.name}#{user.discriminator}**\nID: **{user.id}**"))
    await ctx.response.defer()
    scopes = 0
    try:
        scopes = Memory.read(f"scope/{member.id}balls.txt")
    except:
        scopes = 0
    balance = 0
    users = None
    with sqlite3.connect("database.db") as db:
        cursor = db.cursor()
        for guild, user, bal in cursor.execute("SELECT * FROM balances"):
            if guild == ctx.guild.id:
                if user == member.id:
                    users = user
                    balance = bal
    if not users:
        with sqlite3.connect("database.db") as db:
            cursor = db.cursor()
            cursor.execute("INSERT INTO balances VALUES(?, ?, ?)", (ctx.guild.id, member.id, 0))
        balance = 0
    if not balance:
        balance = 0
    t = member.status
    if t == disnake.Status.online:
        d = "🟢 В сети"

    t = member.status
    if t == disnake.Status.offline:
        d = "⚪ Не в сети"

    t = member.status
    if t == disnake.Status.idle:
        d = "🟠 Не активен"

    t = member.status
    if t == disnake.Status.dnd:
        d = "🔴 Не беспокоить"

    img = Image.new('RGBA', (500, 170), '#000000')
    backgr = ["https://cdn.glitch.global/5fcfa7e8-8436-4acd-a852-e721cd1b531e/1614397342_47-p-temnii-multyashnii-fon-64.png?v=1670188383348","https://cdn.glitch.global/5fcfa7e8-8436-4acd-a852-e721cd1b531e/1622768497_26-phonoteka_org-p-noch-art-minimalizm-krasivo-28.png?v=1670188403979","https://cdn.glitch.global/5fcfa7e8-8436-4acd-a852-e721cd1b531e/i.png?v=1670188415480"]
    r = requests.get(random.choice(backgr), stream = True)
    r = Image.open(io.BytesIO(r.content))
    r = r.convert("RGBA")
    r = r.resize((500, 170))
    img.paste(r, (0, 0, 500, 170))
    url = str(member.avatar.url)
    r = requests.get(url, stream = True)
    r = Image.open(io.BytesIO(r.content))
    r = r.convert('RGBA')
    r = r.resize((100, 100))
    img.paste(r, (15, 15, 115, 115))
    idraw = ImageDraw.Draw(img)        
    name = member.name
    headline = ImageFont.truetype('comfortaa.ttf', size = 25)
    undertext = ImageFont.truetype('comfortaa.ttf', size = 13)
    idraw.text((125, 15), f'{name}', font=headline, fill="#ffffff")
    idraw.text((125, 50), f'#{member.discriminator}', font=undertext, fill="#ffffff")
    idraw.text((125, 70), f'ID: \n{member.id}', font = undertext, fill="#ffffff")
    idraw.text((125, 110), f'Статус: {d}', font = undertext, fill="#ffffff")
    idraw.text((125, 130), f"Кол-во очков: {scopes}", font = undertext, fill="#ffffff")
    idraw.text((125, 150), f"Баланс: {int(balance)}", font=undertext, fill="#ffffff")
    idraw.text((10, 155), f'{bot.user.name} Draw\'s', font=undertext, fill="#ffffff")
    img.save('user_card.png')
    await ctx.send(file=disnake.File("user_card.png"))

@bot.user_command(name="Поприветствовать")
async def infouser(ctx, member: disnake.User):
    await ctx.response.defer()
    sents = [f"На сервере объявился {member.mention}. Попросите его заказать пиццу для сервера **{member.guild.name}**!",f"У нас новенький, {member.mention}, представься, пускай тебя узнает сервер **{member.guild.name}**!",f"{member.mention} пришёл на сервер, познакомься со сервером **{member.guild.name}**"]
    await ctx.send(random.choice(sents))

@bot.event
async def on_ready():
    await bot.change_presence(status=disnake.Status.dnd, activity=disnake.Activity(type=disnake.ActivityType.streaming, url="https://www.twitch.tv/tjma_",name=f"С новым годом! [{len(bot.guilds)}]"))
    with sqlite3.connect("database.db") as db:
        cursor = db.cursor()

        cursor.execute("CREATE TABLE IF NOT EXISTS warns(special_id INTEGER PRIMARY KEY, guild_id INTEGER, user_id INTEGER, reason TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS balances(guild_id INTEGER, user_id INTEGER, user_balance INTEGER)")
        cursor.execute("CREATE TABLE IF NOT EXISTS sugestions(guild_id INTEGER, sugestion TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS songs(name VARCHAR, requester INTEGER, author VARCHAR, id INTEGER, albumId INTEGER, lyrics TEXT, guild INTEGER, position INTEGER PRIMARY KEY)")
        #db.execute('SET NAMES warns;')
        #db.execute('SET CHARACTER SET balances;')
    print("---------------------------\n•Всё готово\n•Версия кода 1.6.2\n•Python Engine•\n---------------------------")

@bot.event
async def on_guild_join(guild):
    channel = 0
    embed = disnake.Embed(title="Я приветствую вас!",description="Вы добавили меня на этот сервер, и за это я вам благодарен\n\n\n❗ Я работаю на slash-командах, префикса у меня нет.\n\nЧто делать если нет slash команд?\nУбедитесь что при добавлений у вас была галочка: https://media.discordapp.net/attachments/1043105245556899850/1043131358555418696/image.png?width=302&height=158\n\n\nЕсли её не было, удалите меня и добавьте заново\n\n\n\nМой сервер где вы можете предложить идею, спросить что либо - ||https://discord.gg/NgKCsFbGty||\n\n💜 Мы желаем вам добра и удачи 💜",color=0x228b22)
    success = True
    chann = None
    while success:
        try:
            chann = guild.text_channels[channel]
            await chann.send(embed=embed)
            success = False
        except:
            channel = channel + 1
            if channel > 60: success = False

    for member in guild.members:
        if member.id == 1047108944721616916:
            await chann.send(f"Привет, мой хозяин <@1047108944721616916> ! 😊")
    await bot.change_presence(status=disnake.Status.dnd, activity=disnake.Activity(type=disnake.ActivityType.streaming, url="https://www.twitch.tv/tjma_",name=f"С новым годом! [{len(bot.guilds)}]"))

@bot.event
async def on_guild_remove(guild):
    await bot.change_presence(status=disnake.Status.dnd, activity=disnake.Activity(type=disnake.ActivityType.streaming, url="https://www.twitch.tv/tjma_",name=f"С новым годом! [{len(bot.guilds)}]"))

@bot.event
async def on_slash_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f'Повтори попытку через {round(error.retry_after, 2)} секунд.',ephemeral=True)
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка",description="У вас недостаточно прав.",color=disnake.Color.red()),ephemeral=True)
    if isinstance(error, commands.BotMissingPermissions):
        await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка",description="У меня недостаточно прав.",color=disnake.Color.red()), ephemeral=True)
    else:
        print(error)

@bot.event
async def on_member_join(member):
    channel_id = 0
    try:
        channel_id = Memory.read(f"channels/{member.guild.id}welcomechannel.txt")
    except:
        channel_id = 0
        return
    request = requests.get(f"https://some-random-api.ml/canvas/misc/namecard?avatar={member.avatar.url}&username={member.name}&birthday=-.-&description=зашёл на сервер {member.guild.name}!")
    channel = bot.get_channel(int(channel_id))
    messages = [f"На сервере объявился {member.mention}. Попросите его заказать пиццу для сервера **{member.guild.name}**!",f"У нас новенький, {member.mention}, представься, пускай тебя узнает сервер **{member.guild.name}**!",f"{member.mention} пришёл на сервер, познакомься со сервером **{member.guild.name}**"]
    await channel.send(embed=disnake.Embed(description=random.choice(messages),color=0x228b22).set_image(url=request.url))

@bot.event
async def on_member_leave(member):
    channel_id = 0
    try:
        channel_id = Memory.read(f"channels/{member.guild.id}byechannel.txt")
    except:
        channel_id = 0
        return
    request = requests.get(f"https://some-random-api.ml/canvas/misc/namecard?avatar={member.avatar.url}&username={member.name}&birthday=-.-&description=покинул сервер {member.guild.name}...")
    channel = bot.get_channel(int(channel_id))
    messages = [f"Пользователь {member.mention}, пиццу так и никто не получил...",f"{member.mention} покинул нас!",f"{member.mention} ушёл от нас..."]
    await channel.send(embed=disnake.Embed(description=random.choice(messages),color=0x228b22).set_image(url=request.url))

@bot.event
async def on_member_remove(member):
    channel_id = 0
    try:
        channel_id = Memory.read(f"channels/{member.guild.id}byechannel.txt")
    except:
        channel_id = 0
        return
    request = requests.get(f"https://some-random-api.ml/canvas/misc/namecard?avatar={member.avatar.url}&username={member.name}&birthday=-.-&description=покинул сервер {member.guild.name}...")
    channel = bot.get_channel(int(channel_id))
    messages = [f"Пользователь {member.mention} ушёл, пиццу так и никто не получил...",f"{member.mention} покинул нас!",f"{member.mention} ушёл от нас..."]
    await channel.send(embed=disnake.Embed(description=random.choice(messages),color=0x228b22).set_image(url=request.url))

@bot.event
async def on_message(msg):
    if msg.author.bot:
        return
    #return await msg.reply(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Неизвестная ошибка",description="Обратитесь к администраций",color=disnake.Color.red()))
    await bot.process_commands(msg)
    content = msg.content.lower()
    for_check = content.translate(str.maketrans('', '', string.punctuation))
    bad_words = ["сука","ёбаный","блять","пидор","пидора","бля","ебать","нахуй","хуй","заебал","заебись","ахуенно","ахуено","пиздюк","нахуя","хуйня","ёбаный","ебаный","лошара","лох","пиздец","пздц","пизда","педик","канаве","мудила","мудак","конченный","конченый","кончаю","конча","шлюха","гей","лесби","лесбиянка","трах","трахаться","сосаться","ебаться","доёбываться","залупа","хуя","блядина","гавнозалупа","пенис","рукожоп","хуярище","боданище","ебланище"]
    words_content = for_check.split()
    try:
        Memory.read(f"badwords/{msg.guild.id}.txt")
    except:
        pass
    else:
        for word in words_content:
            if word in bad_words:
                member = msg.author
                reason = "Автомод: Плохие слова"
                with sqlite3.connect("database.db") as db:
                    cursor = db.cursor()
                    cursor.execute("INSERT INTO warns(guild_id, user_id, reason) VALUES(?, ?, ?)", (msg.guild.id, member.id, reason))
                await msg.delete()
                await msg.channel.send(f"<:policePanda:1047242230651437077> {msg.author.mention} На этом сервере запрещены плохие слова! Вам вынесен варн в виде наказания.")
        verotnst = fuzz.ratio(words_content, bad_words)
        if verotnst > 50:
            member = msg.author
            reason = "Автомод: Плохие слова"
            with sqlite3.connect("database.db") as db:
                cursor = db.cursor()
                cursor.execute("INSERT INTO warns(guild_id, user_id, reason) VALUES(?, ?, ?)", (msg.guild.id, member.id, reason))
            await msg.delete()
            await msg.channel.send(f"<:policePanda:1047242230651437077> {msg.author.mention} На этом сервере запрещены плохие слова! Вам вынесен варн в виде наказания.")
    webhooks = await msg.channel.webhooks()
    for webhook in webhooks:
        if webhook.user == bot.user:
            if msg.content.startswith(webhook.name):
                try:
                    url = None
                    try:
                        url = Memory.read(f"avatars/{msg.channel.id}{webhook.name}webhook.txt")
                    except:
                        await webhook.send(content = msg.content[len(webhook.name) + 1:])
                        await msg.delete()
                    else:
                        await webhook.send(content = msg.content[len(webhook.name) + 1:], avatar_url=url)
                        await msg.delete()
                except disnake.errors.HTTPException:
                    await msg.reply("Слишком много HTTPS запросов на данный момент, простите...")


bot.run("Discord Token Here")
