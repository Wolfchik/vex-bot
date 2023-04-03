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
import chat
import sqlite3
from fuzzywuzzy import fuzz
from memory import Memory
from disnake.ext import commands
from disnake.utils import get
from PIL import Image, ImageFont, ImageDraw
import googletrans
import string
import flask
import aiohttp
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
from boticordpy import BoticordClient
from flask import Flask, render_template, session, redirect, url_for
from threading import Thread
from bs4 import BeautifulSoup as BS
from fake_useragent import UserAgent
client = None
request = Request(proxy_url='http://логин:пароль@195.245.103.194:62986')
client = Client("токен яндекс музыки", request=request).init()
print("yandex_music: Success Connect")
translator = googletrans.Translator()
bot = commands.Bot(command_prefix="?", intents=disnake.Intents.all(), sync_commands_debug=True)

def lang(ctx, text):
    return text

lists = []

class searchError(Exception):
    pass

class VoiceStateError(Exception):
    pass

class Song(disnake.PCMVolumeTransformer):

    def __init__(self):
        self._source = "Yandex Music"

    def search_tracks(self, ctx, query):
        stats = True
        while stats:
            try:
                searcher = client.search(str(query))
                if not searcher.tracks: raise searchError("Not searched tracks")
                track_object = searcher.tracks['results'][0]
                stats = False
                text = None
                lyrics = track_object.get_supplement()
                if lyrics.lyrics: text = lyrics.lyrics.full_lyrics
                with sqlite3.connect("database.db") as db:
                    cursor = db.cursor()
                    cursor.execute("INSERT INTO songs(name, requester, author, id, albumid, lyrics, guild, image) VALUES(?, ?, ?, ?, ?, ?, ?, ?)", (track_object['title'],ctx.author.id,track_object['artists'][0]['name'],track_object['id'],track_object['albums'][0]["id"],text,ctx.guild.id,"https://" + track_object["og_image"].replace("%%", "1000x1000"),))
                return {
                "id": track_object["id"],
                "title": track_object["title"],
                "artist": track_object["artists"][0]["name"],
                "albumid": track_object["albums"][0]["id"],
                "lyrics": text,
                "image": "https://" + track_object["og_image"].replace("%%", "1000x1000")
                }
            except NetworkError:
                pass
    async def download_track(self, ctx, track):
        stats = True
        while stats:
            try:
                client.tracks(track['id'])[0].download(f"songs/{track['id']}.mp3")
                stats = False
            except NetworkError:
                pass


    async def join_channel(self, ctx):
        voice = ctx.author.voice
        if not voice: return "notChannel"
        if voice:
            await voice.channel.connect()
            for mem in voice.channel.members:
                if mem.id == 1047125592220373075:
                    try:
                        await mem.edit(deafen=True)
                    except:
                        pass
            return None

    async def leave_channel(self, ctx):
        voice_state = ctx.guild.voice_client
        if not voice_state:
            return "notState"
        if voice_state.is_connected():
            await voice_state.disconnect()
            return None
        else:
            return "notState"

    async def stop(self, ctx):
        voice_state = ctx.guild.voice_client
        if not voice_state:
            return "notState"
        if voice_state.is_connected():
            await Song.leave_channel(self, ctx)
            return None
        else:
            return "notState"

    async def my_after(self, ctx):
        #os.remove(f"songs/{ctx.guild.id}.mp3")
        if not ctx.guild:
            return
        voice_state = ctx.guild.voice_client
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
            for n, r, a, i, ai, ly, g, im, p in c.execute("SELECT * FROM songs WHERE guild = ?", (ctx.guild.id,)):
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
        if os.path.isfile("songs/{}.mp3".format(ids[0])):
            os.remove("songs/{}.mp3".format(ids[0]))
        if os.path.isfile(f"msgs/{ctx.guild.id}.txt"):
            with open(f"msgs/{ctx.guild.id}.txt", "r") as file:
                await bot.get_message(int(file.read())).delete()
        if voice_state and voice_state.is_connected():
            try:
                positions[1]
            except:
                pass
            else:
                await Song.play(self, ctx)

    def init_after(self, ctx):
        asyncio.run_coroutine_threadsafe(Song.my_after(self, ctx), bot.loop)

    async def play(self, ctx):
        voice_state = ctx.guild.voice_client
        if not voice_state:
            error = await Song.join_channel(self, ctx)
            if error:
                return error
        voice_state = ctx.guild.voice_client
        if voice_state.is_playing():
            return "alreadyPlay"
        ids = []
        names = []
        requesters = []
        alis = []
        authors = []
        positions = []
        imgs = []
        with sqlite3.connect("database.db") as db:
            c = db.cursor()
            for n, r, a, i, ai, ly, g, im, p in c.execute("SELECT * FROM songs WHERE guild = ?", (ctx.guild.id,)):
                ids.append(i)
                names.append(n)
                requesters.append(r)
                alis.append(ai)
                authors.append(a)
                positions.append(p)
                imgs.append(im)
        if not os.path.isfile(f"songs/{ids[0]}.mp3"):
            await Song.download_track(self, ctx, {'id': ids[0]})
        voice_state.play(disnake.FFmpegPCMAudio(f"songs/{ids[0]}.mp3"), after=lambda e: Song.init_after(self, ctx))
        voice_state.is_playing()
        infor = Song.now_playing(self, ctx.guild)
        embed = disnake.Embed(title=infor['name'],color=0x228b22)
        embed.add_field(name=lang(ctx,"Главный автор:"),value=infor['artist'])
        embed.add_field(name=lang(ctx,"Предложил:"),value=f"<@{infor['requester']}>")
        embed.add_field(name=lang(ctx,"Источник:"),value="<:yandexMusic:1056924402790436934> Yandex Music\n")
        embed.add_field(name=lang(ctx,"Ссылка:"),value=f"[**{lang(ctx,'Это кликабельная ссылка!')}**]({infor['uri']})")
        embed.add_field(name=lang(ctx,"Позиция:"),value=infor['pos'])
        embed.set_thumbnail(url=infor['image'])

        comps = [
        disnake.ui.Button(emoji="⏹", label="Стоп", style=disnake.ButtonStyle.danger, custom_id="stop"),
        disnake.ui.Button(emoji="⏮", label="Реплей", style=disnake.ButtonStyle.blurple, custom_id="replay"),
        disnake.ui.Button(emoji="⏸", label="Пауза", style=disnake.ButtonStyle.blurple, custom_id="pause"),
        disnake.ui.Button(emoji="⏭", label="Скип", style=disnake.ButtonStyle.blurple, custom_id="next"),
        disnake.ui.Button(emoji="📰", label="Текст", style=disnake.ButtonStyle.success, custom_id="text")
        ]

        msg = await ctx.channel.send(embed=embed, components=comps)
        with open(f"msgs/{msg.guild.id}.txt", "w") as file:
            file.write(str(msg.id))
        return None

    async def add_for_id(self, ctx, i):
        track_object = client.tracks([f"{i}"])[0]
        text = None
        lyrics = track_object.get_supplement()
        if lyrics.lyrics: text = lyrics.lyrics.full_lyrics
        with sqlite3.connect("database.db") as db:
            cursor = db.cursor()
            cursor.execute("INSERT INTO songs(name, requester, author, id, albumid, lyrics, guild, image) VALUES(?, ?, ?, ?, ?, ?, ?, ?)", (track_object['title'],ctx.author.id,track_object['artists'][0]['name'],track_object['id'],track_object['albums'][0]["id"],text,ctx.guild.id,"https://" + track_object["og_image"].replace("%%", "1000x1000"),))


    async def skip(self, ctx):
        voice_state = ctx.guild.voice_client
        if voice_state and voice_state.is_playing():
            try:
                await voice_state.stop()
            except:
                pass
            return None
        else:
            return "notState"

    def lyrics(self, ctx):
        names = []
        requesters = []
        artists = []
        ids = []
        albumids = []
        lyrics = []
        with sqlite3.connect("database.db") as db:
            c = db.cursor()
            for n, r, a, i, ai, ly, g, im, p in c.execute("SELECT * FROM songs WHERE guild = ?", (ctx.guild.id,)):
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

    def now_playing(self, guild):
        names = []
        requesters = []
        artists = []
        ids = []
        albumids = []
        positions = []
        imgs = []
        with sqlite3.connect("database.db") as db:
            c = db.cursor()
            for n, r, a, i, ai, ly, g, im, p in c.execute("SELECT * FROM songs WHERE guild = ?", (guild.id,)):
                names.append(n)
                requesters.append(r)
                artists.append(a)
                ids.append(i)
                albumids.append(ai)
                positions.append(p)
                imgs.append(im)
        return {
        "name": names[0],
        "requester": requesters[0],
        "artist": artists[0],
        "pos": positions[0],
        "uri": f"https://music.yandex.ru/album/{albumids[0]}/track/{ids[0]}",
        "image": imgs[0],
        "id": ids[0]
        }

    def construct_queue(self, guild):
        urls = []
        names = []
        positions = []
        texts = []
        with sqlite3.connect("database.db") as db:
            c = db.cursor()
            for n, r, a, i, ai, ly, g, im, p in c.execute("SELECT * FROM songs WHERE guild = ?", (guild.id,)):
                names.append(n)
                positions.append(p)
                urls.append(f"https:/music.yandex.ru/album/{ai}/track/{i}")
                texts.append(f"`{p}.` {a} - [**{n}**](https:/music.yandex.ru/album/{ai}/track/{i}) - <@{r}>")
        if texts == []: return None
        return "\n".join(list(map(str, texts)))

    def parse_queue(self, guild):
        urls = []
        names = []
        positions = []
        texts = []
        with sqlite3.connect("database.db") as db:
            c = db.cursor()
            for n, r, a, i, ai, ly, g, im, p in c.execute("SELECT * FROM songs WHERE guild = ?", (guild.id,)):
                names.append(n)
                positions.append(p)
                urls.append(f"https:/music.yandex.ru/album/{ai}/track/{i}")
                texts.append(f"{p}. {n}")
        return {
        "texts": texts,
        "urls": urls
        }


    def pause(self, ctx):
        voice_state = ctx.voice_client
        if voice_state.is_playing():
            voice_state.pause()

        else:
            raise VoiceStateError("don't playing!")

    def resume(self, ctx):
        voice_state = ctx.voice_client
        if not voice_state.is_playing():
            voice_state.resume()
        else:
            raise VoiceStateError("already Playing!")


    def get_rand_track(self, ctx):
        track = random.choice(client.users_likes_tracks()).fetch_track()
        return track

    async def replay(self, ctx):
        if os.path.isfile(f"msgs/{ctx.guild.id}.txt"):
            with open(f"msgs/{ctx.guild.id}.txt", "r") as file:
                await bot.get_message(int(file.read())).delete()
        Song.pause(self, ctx.guild)
        await Song.play(self, ctx)

    async def import_album(self, ctx, album_id: int):
        album = client.albums_with_tracks(album_id)
        tracks = []
        count = 0
        for i, volume in enumerate(album.volumes):
            tracks += volume
        for track in tracks:
            #print(track)
            await Song.add_for_id(self, ctx, track["id"])
            count += 1
        return count


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.song = Song()

    @commands.slash_command(name="join",description="Подключает бота к вашему каналу")
    async def _join(self, ctx):
        await ctx.response.defer()
        error = await self.song.join_channel(ctx)
        if error:
            if error == "notChannel": return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx,'Ошибка')}",description=lang(ctx,"Для этого необходимо войти в голосовой канал"),color=disnake.Color.red()), delete_after = 10)

        await ctx.send(embed=disnake.Embed(title=f"<:correctCheckmark:1047244074350018700> {lang(ctx,'Успешно')}",color=0x228b22))

    @commands.command(name="join", usage="?join")
    async def _join_(self, ctx):
        error = await self.song.join_channel(ctx)
        if error:
            if error == "notChannel": return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx,'Ошибка')}",description=lang(ctx,"Для этого необходимо войти в голосовой канал"),color=disnake.Color.red()), delete_after = 10)

        await ctx.send(embed=disnake.Embed(title=f"<:correctCheckmark:1047244074350018700> {lang(ctx,'Успешно')}",color=0x228b22))

    @commands.slash_command(name="stop",description="Остановить воспроизведение(внимание, очередь будет сохранена.)")
    async def _stop(self, ctx):
        await ctx.response.defer()
        error = await self.song.stop(ctx)
        if error:
            if error == "notState": return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx,'Ошибка')}",description=lang(ctx,"Я уже не подключен."),color=disnake.Color.red()), delete_after = 10)

        await ctx.send(embed=disnake.Embed(title=f"<:correctCheckmark:1047244074350018700> {lang(ctx,'Успешно')}",description=lang(ctx,"Пока-пока!"),color=0x228b22))

    @commands.command(name="stop", usage="?stop")
    async def _stop_(self, ctx):
        error = await self.song.stop(ctx)
        if error:
            if error == "notState": return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx,'Ошибка')}",description=lang(ctx,"Я уже не подключен."),color=disnake.Color.red()), delete_after = 10)

        await ctx.send(embed=disnake.Embed(title=f"<:correctCheckmark:1047244074350018700> {lang(ctx,'Успешно')}",description=lang(ctx,"Пока-пока!"),color=0x228b22))

    @commands.slash_command(name="play",description="Воспроизвести трек")
    async def _play(self, ctx, название: str = None):
        await ctx.response.defer()
        name = название
        voice_state = ctx.guild.voice_client
        if name:
            try:
                track = self.song.search_tracks(ctx, name)
            except searchError:
                return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx,'Ошибка')}",description=lang(ctx,"Ничего не нашлось :("),color=disnake.Color.red()), delete_after = 10)
        else:
            text = self.song.construct_queue(ctx.guild)
            if not text:
                return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx,'Ошибка')}",description=lang(ctx,"Очередь на этом сервере пуста, поэтому добавьте что то в неё!"),color=disnake.Color.red()), delete_after = 10)
        if voice_state:
            if voice_state.is_playing():
                pass
            else:
                error = await self.song.play(ctx)
        else:
            error = await self.song.play(ctx)
            if error:
                if error == "notChannel": return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx,'Ошибка')}",description=lang(ctx,"Зайдите в голосовой канал."),color=disnake.Color.red()), delete_after = 10)
        if name:
            await ctx.send(f"{track['title']} {lang(ctx,'успешно добавлена в очередь')}!")
        else:
            await ctx.send(f"**{self.bot.user.name}** успешно начал воспроизведение очереди!")

    @commands.command(name="play", usage="?play <название> - Добавить\n?play - Включить очередь")
    async def _play_(self, ctx, *, name: str = None):
        voice_state = ctx.guild.voice_client
        if name:
            try:
                track = self.song.search_tracks(ctx, name)
            except searchError:
                return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx,'Ошибка')}",description=lang(ctx,"Ничего не нашлось :("),color=disnake.Color.red()), delete_after = 10)
        else:
            text = self.song.construct_queue(ctx.guild)
            if not text:
                return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx,'Ошибка')}",description=lang(ctx,"Очередь на этом сервере пуста, поэтому добавьте что то в неё!"),color=disnake.Color.red()), delete_after = 10)
        if voice_state:
            if voice_state.is_playing():
                pass
            else:
                error = await self.song.play(ctx)
        else:
            error = await self.song.play(ctx)
            if error:
                if error == "notChannel": return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx,'Ошибка')}",description=lang(ctx,"Зайдите в голосовой канал."),color=disnake.Color.red()), delete_after = 10)
        if name:
            await ctx.send(f"{track['title']} {lang(ctx,'успешно добавлена в очередь')}!")
        else:
            await ctx.message.add_reaction("<:correctCheckmark:1047244074350018700>")

    @commands.slash_command(name="import-playlist", description="Импортировать плэйлист по ID")
    async def iq_(self, ctx, id: int):
        await ctx.response.defer()
        count = await self.song.import_album(ctx, id)
        if not count > 0:
            return await ctx.send("<:wrongCheckmark:1047244133078675607> Кажеться, в плейлисте ничего нет!")
        else:
            await ctx.send("<:correctCheckmark:1047244074350018700> Успешно, вы можете начать воспроизведение воспользовавшись командой `/play`")

    @commands.slash_command(name="skip",description="Пропустить трек")
    async def _skip(self, ctx):
        await ctx.response.defer()
        error = await self.song.skip(ctx)
        if error == "notState": return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx,'Ошибка')}",description=lang(ctx,"Сейчас ничего не играет!"),color=disnake.Color.red()), delete_after = 10)
        await ctx.send(embed=disnake.Embed(title=f"<:correctCheckmark:1047244074350018700> {lang(ctx,'Успешно')}",color=0x228b22))

    @commands.command(name="skip", usage="?skip")
    async def _skip_(self, ctx):
        error = await self.song.skip(ctx)
        if error == "notState": return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx,'Ошибка')}",description=lang(ctx,"Сейчас ничего не играет!"),color=disnake.Color.red()), delete_after = 10)
        await ctx.message.add_reaction("<:correctCheckmark:1047244074350018700")

    @commands.slash_command(name="lyrics",description="Получить текст от играемого прямо сейчас трека")
    async def lyri(self, ctx):
        await ctx.response.defer()
        lyrics = self.song.lyrics(ctx)
        if not lyrics['lyrics']: return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx,'Ошибка')}",description=lang(ctx,"Текст этой песни не доступен"),color=disnake.Color.red()), delete_after = 10)
        await ctx.send(embed=disnake.Embed(title=f"🔍 {lang(ctx,'Текст от трека')} **{lyrics['name']}**",description=lyrics["lyrics"]))

    @commands.command(name="lyrics", usage="?lyrics")
    async def _lyri_(self, ctx):
        lyrics = self.song.lyrics(ctx)
        if not lyrics['lyrics']: return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx,'Ошибка')}",description=lang(ctx,"Текст этой песни не доступен"),color=disnake.Color.red()), delete_after = 10)
        await ctx.send(embed=disnake.Embed(title=f"🔍 {lang(ctx,'Текст от трека')} **{lyrics['name']}**",description=lyrics["lyrics"]))

    @commands.slash_command(name="now-playing",description="Что сейчас играет?")
    async def np(self, ctx):
        await ctx.response.defer()
        voice_state = ctx.guild.voice_client
        if voice_state:
            if voice_state.is_playing():
                infor = self.song.now_playing(ctx.guild)
                embed = disnake.Embed(title=infor['name'],color=0x228b22)
                embed.add_field(name=lang(ctx,"Главный автор:"),value=infor['artist'])
                embed.add_field(name=lang(ctx,"Предложил:"),value=f"<@{infor['requester']}>")
                embed.add_field(name=lang(ctx,"Источник:"),value="<:yandexMusic:1056924402790436934> Yandex Music\n")
                embed.add_field(name=lang(ctx,"Ссылка:"),value=f"[**{lang(ctx,'Это кликабельная ссылка!')}**]({infor['uri']})")
                embed.add_field(name=lang(ctx,"Позиция:"),value=infor['pos'])
                embed.set_thumbnail(url=infor['image'])
                await ctx.send(embed=embed, delete_after = 20)
            else:
                await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx,'Ошибка!')}",description=lang(ctx,'Сейчас ничего не играет'),color=disnake.Color.red()), delete_after = 10)
        else:
            await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx,'Ошибка!')}",description=lang(ctx,"Сейчас ничего не играет"),color=disnake.Color.red()), delete_after = 10)

    @commands.command(name="now-playing", aliases=["np","now"], usage="?now-playing")
    async def _np_(self, ctx):
        voice_state = ctx.guild.voice_client
        if voice_state:
            if voice_state.is_playing():
                infor = self.song.now_playing(ctx.guild)
                embed = disnake.Embed(title=infor['name'],color=0x228b22)
                embed.add_field(name=lang(ctx,"Главный автор:"),value=infor['artist'])
                embed.add_field(name=lang(ctx,"Предложил:"),value=f"<@{infor['requester']}>")
                embed.add_field(name=lang(ctx,"Источник:"),value="<:yandexMusic:1056924402790436934> Yandex Music\n")
                embed.add_field(name=lang(ctx,"Ссылка:"),value=f"[**{lang(ctx,'Это кликабельная ссылка!')}**]({infor['uri']})")
                embed.add_field(name=lang(ctx,"Позиция:"),value=infor['pos'])
                embed.set_thumbnail(url=infor['image'])
                await ctx.send(embed=embed, delete_after = 20)
            else:
                await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx,'Ошибка!')}",description=lang(ctx,'Сейчас ничего не играет'),color=disnake.Color.red()), delete_after = 10)
        else:
            await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx,'Ошибка!')}",description=lang(ctx,"Сейчас ничего не играет"),color=disnake.Color.red()), delete_after = 10)

    @commands.slash_command(name="queue", description="Посмотреть очередь")
    async def queu(self, ctx):
        await ctx.response.defer()
        text = self.song.construct_queue(ctx.guild)
        if not text:
            return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx,'Ошибка')}",description=lang(ctx,"Очередь на этом сервере пуста!"),color=disnake.Color.red()), delete_after = 10)
        await ctx.send(embed=disnake.Embed(title=f"{lang(ctx,'Очередь сервера')} {ctx.guild.name}!",description=text, color=0x228b22))

    @commands.command(name="queue", usage="?queue")
    async def _queu_(self, ctx):
        text = self.song.construct_queue(ctx.guild)
        if not text:
            return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx,'Ошибка')}",description=lang(ctx,"Очередь на этом сервере пуста!"),color=disnake.Color.red()), delete_after = 10)
        await ctx.send(embed=disnake.Embed(title=f"{lang(ctx,'Очередь сервера')} {ctx.guild.name}!",description=text, color=0x228b22))

    @commands.slash_command(name="pause",description="Поставить воспроизведение на паузу")
    async def paus_(self, ctx):
        await ctx.response.defer()
        try:
            self.song.pause(ctx.guild)
        except VoiceStateError:
            await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx,'Ошибка')}",description=lang(ctx,"Сейчас ничего не играет"),color=disnake.Color.red()), delete_after = 10)
        else:
            await ctx.send(f"<:correctCheckmark:1047244074350018700>, {lang(ctx,'чтобы продолжить воспроизведение введите /resume')}", delete_after = 20)

    @commands.command(name="pause", usage="?pause")
    async def _paus_(self, ctx):
        try:
            self.song.pause(ctx.guild)
        except VoiceStateError:
            await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx,'Ошибка')}",description=lang(ctx,"Сейчас ничего не играет"),color=disnake.Color.red(), delete_after = 10))
        else:
            await ctx.send(f"<:correctCheckmark:1047244074350018700>, {lang(ctx,'чтобы продолжить воспроизведение введите /resume')}", delete_after = 20)

    @commands.slash_command(name="resume",description="Продолжить воспроизведение")
    async def resu_(self, ctx):
        try:
            self.song.resume(ctx.guild)
        except VoiceStateError:
            await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx,'Ошибка')}",description=lang(ctx,"Трек уже играет"),color=disnake.Color.red()), delete_after = 10)
        else:
            await ctx.message.add_reaction(f"<:correctCheckmark:1047244074350018700>")

    @commands.command(name="resume", usage="?resume")
    async def _resu_(self, ctx):
        try:
            self.song.resume(ctx.guild)
        except VoiceStateError:
            await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx,'Ошибка')}",description=lang(ctx,"Трек уже играет"),color=disnake.Color.red()), delete_after = 10)
        else:
            await ctx.message.add_reaction(f"<:correctCheckmark:1047244074350018700>")

    @commands.slash_command(name="replay",description="Воспроизвести трек с начала")
    async def re_(self, ctx):
        await ctx.response.defer()
        voice_state = ctx.guild.voice_client
        if voice_state and voice_state.is_playing():
            await self.song.replay(ctx)
            await ctx.send("<:correctCheckmark:1047244074350018700>")
        else:
            await ctx.send("<:wrongCheckmark:1047244133078675607>" + lang(ctx, "Сейчас ничего не играет чтобы начать воспроизведение заново!"), delete_after = 10)

    @commands.command(name="replay", usage="?replay")
    async def _re_(self, ctx):
        voice_state = ctx.guild.voice_client
        if voice_state and voice_state.is_playing():
            await self.song.replay(ctx)
            await ctx.message.add_reaction("<:correctCheckmark:1047244074350018700>")
        else:
            await ctx.send("<:wrongCheckmark:1047244133078675607>" + lang(ctx, "Сейчас ничего не играет чтобы начать воспроизведение заново!"), delete_after = 10)

    @commands.slash_command(name="random-track",description="Воспроизвести рандомный трек")
    async def ra_tra(self, ctx):
        await ctx.response.defer()
        voice_state = ctx.guild.voice_client
        track = self.song.get_rand_track(ctx)
        await self.song.add_for_id(ctx, track["id"])
        if voice_state:
            if voice_state.is_playing():
                #await Song.leave_channel(ctx)
                pass
            else:
                error = await self.song.play(ctx)
                if error == "notChannel": return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx,'Ошибка')}",description=lang(ctx,"Зайдите в голосовой канал."),color=disnake.Color.red()), delete_after = 20)
        else:
            error = await self.song.play(ctx)
            if error == "notChannel": return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx,'Ошибка')}",description=lang(ctx,"Зайдите в голосовой канал."),color=disnake.Color.red()), delete_after = 20)
        await ctx.send(f"Рандомный трек успешно добавлен в очередь!")

    @commands.command(name="random-track", aliases=["rtrack"], usage="?random-track")
    async def _ra_tra_(self, ctx):
        voice_state = ctx.guild.voice_client
        track = self.song.get_rand_track(ctx)
        await self.song.add_for_id(ctx, track["id"])
        if voice_state:
            if voice_state.is_playing():
                pass
            else:
                error = await self.song.play(ctx)
                if error == "notChannel": return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx,'Ошибка')}",description=lang(ctx,"Зайдите в голосовой канал."),color=disnake.Color.red()), delete_after = 10)
        else:
            error = await self.song.play(ctx)
            if error == "notChannel": return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx,'Ошибка')}",description=lang(ctx,"Зайдите в голосовой канал."),color=disnake.Color.red()), delete_after = 10)
        await ctx.message.add_reaction("<:correctCheckmark:1047244074350018700>")

class Main(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="help",description="Список команд для ориентации.")
    async def help(self, ctx):
        await ctx.response.defer()
        embedmain = disnake.Embed(title=lang(ctx,"Начните нажимать на кнопки для выбор чего то."),description=f"<:yandexMusic:1056924402790436934> **{lang(ctx,'Яндекс.Музыка')}**\n\n🎮 **{lang(ctx,'Игры')}**\n\n<:cooldown:1047243027166539846> **{lang(ctx,'Модерация')}**\n\n🎁**{lang(ctx,'Утилиты')}**\n\n:dollar: **{lang(ctx,'Экономика')}**\n\n<:pandaElf:1047241340657872948> **{lang(ctx,'Отношения')}**\n\n<:thinks1:1047243641388793938> **{lang(ctx,'РП')}**\n\n⚙ **{lang(ctx,'Настройки')}**",color=0x228b22)
        await ctx.send(embed=embedmain,components=[
            disnake.ui.Button(label=lang(ctx,"Яндекс.Музыка"),style=disnake.ButtonStyle.danger, custom_id="mus"),
            disnake.ui.Button(label=lang(ctx,"Игры"), style=disnake.ButtonStyle.success, custom_id="games"),
            disnake.ui.Button(label=lang(ctx,"Модерация"), style=disnake.ButtonStyle.danger, custom_id="mod"),
            disnake.ui.Button(label=lang(ctx,"Утилиты"), style=disnake.ButtonStyle.success, custom_id="utils"),
            disnake.ui.Button(label=lang(ctx,"Экономика"), style=disnake.ButtonStyle.danger, custom_id="eco"),
            disnake.ui.Button(label=lang(ctx,"Отношения"), style=disnake.ButtonStyle.success, custom_id="relaship"),
            disnake.ui.Button(label=lang(ctx,"РП"), style=disnake.ButtonStyle.danger, custom_id="roleplay"),
            disnake.ui.Button(label=lang(ctx,"Настройки"), style=disnake.ButtonStyle.success, custom_id="setts")
        ])

        embedmus = disnake.Embed(title=f"<:yandexMusic:1056924402790436934> {lang(ctx, 'Яндекс.Музыка')}",description=f"`/play <{lang(ctx, 'название')}>` - {lang(ctx, 'Начать воспроизведение в голосовом канале')}\n`/skip` - {lang(ctx, 'Пропустить трек')}\n`/stop` - {lang(ctx, 'Остановить и выйти из голосового канала')}\n`/join` - {lang(ctx, 'Пригласить бота в голосовой канал')}\n`/queue` - {lang(ctx, 'Посмотреть очередь сервера')}\n`/now-playing` - {lang(ctx, 'что сейчас играет?')}\n`/pause` - {lang(ctx,'поставить воспроизведение на паузу')}\n`/resume` - {lang(ctx, 'продолжить воспроизведение')}\n`/replay` - {lang(ctx, 'начать воспроизведение трека с самого начала')}",color=0x228b22)
        embedgames = disnake.Embed(title=f"🎮 {lang(ctx, 'Игры')}", description=f"`/maths-plus` - {lang(ctx, 'Игра в математику с сложением')}\n`/maths-minus` - {lang(ctx, 'Игра в математику с вычитанием')}\n`/maths-multiply` - {lang(ctx, 'Игра в математику с умножением')}\n`/tape` - {lang(ctx, 'Игра в рулетку')}\n`/truth-or-dare` - {lang(ctx, 'Игра в правду или действие')}\n`/heads-or-tails` - {lang(ctx, 'Подбросить монетку')}\n`/door` - {lang(ctx, 'Игра Выбери правильную дверь.')}\n`/akinator` - {lang(ctx, 'Сыграть в акинатора')}", color=0x228b22)
        embedmod = disnake.Embed(title=f"<:cooldown:1047243027166539846> {lang(ctx, 'Модерация')}",description=f"`/ban [member] <reason>` - {lang(ctx, 'Забанить кого-то')}\n`/kick [member] <reason>` - {lang(ctx, 'Выгнать кого либо с сервера')}\n`/mute [member] <time>` - {lang(ctx, 'Заглушить кого то на сколько то минут')}\n`/warn [@member] <reason>` - {lang(ctx, 'Выдать предупреждение')}\n`/warns` - {lang(ctx, 'Посмотреть все предупреждения на этом сервере')}\n`/unwarn [{lang(ctx, 'номер_случая')}]` - {lang(ctx, 'Снять пред')}", color=0x228b22)
        embedutils = disnake.Embed(title=f"<:Magic:1047241900370956298> {lang(ctx, 'Утилиты')}",description=f"`/profile` - {lang(ctx, 'Посмотреть свой профиль и информацию которую о вас сохраняет Vex')}\n`/lgbt` - {lang(ctx, 'Делает вам ЛГБТ аватарку')}\n`/jail` - {lang(ctx, 'Делает аватарку, сидящую в тюрьме')}\n`/passed` - {lang(ctx, 'Делает на вашей аватарке надпись Mission Passed, respect+')}\n`/wasted` - {lang(ctx, 'Делает на вашей аватарке надпись WASTED')}\n`/pixelate` - {lang(ctx, 'Пиксилизирует ваш аватар')}\n`/triggered` - {lang(ctx, 'Делает на вашей аватарке надпись TRIGGERED')}\n`/ussr` - {lang(ctx, 'Накладывает на ваш аватар флаг СССР')}\n`/youtube-comment [{lang(ctx, 'Коментарий')}]` - {lang(ctx, 'Делает коментарий с вашим ником, аватаром и коментарием')}\n`/voice [{lang(ctx, 'Текст')}]` - {lang(ctx, 'Создаёт озвучку указаного вами текста')}\n`/encode [{lang(ctx, 'текст')}]` - {lang(ctx, 'Зашифровать текст в base64')}\n`/decode [base64]` - {lang(ctx, 'Расшифровать base64 в текст')}\n`/joke` - {lang(ctx, 'Генерирует рандомную шутку(Смешная или нет зависит от АПИ)')}\n`/poll [sel1] [sel2] <sel...>` - {lang(ctx, 'Запустить голосование')}\n`/random [{lang(ctx, 'вариации')}]` - {lang(ctx, 'Рандомайзер')}\n`/quote` - {lang(ctx, 'Цитатыыы великииих людеей')}\n`/weather [city]` - {lang(ctx, 'Узнать погоду в городе России')}\n`/animego` - {lang(ctx, 'Искать аниме-фильмы на animego.net')}",color=0x228b22)
        embedeco = disnake.Embed(title=f"<:dollar:1051974269296451684> {lang(ctx, 'Экономика')}",description=f"`/daily` - {lang(ctx, 'Получить ежедневную награду, может быть отключена админами')}\n`/work [!{lang(ctx, 'работа')}]` - {lang(ctx, 'Работать чтобы получить деньги')}\n`/balance` - {lang(ctx, 'Проверить свой или чужой баланс')}\n`/add-money [{lang(ctx, 'сумма')}] [{lang(ctx, 'участник')}]` - {lang(ctx, 'Выдать иную сумму пользователю.')}\n`/reduce-money [{lang(ctx, 'сумма')}] [{lang(ctx, 'участник')}]` - {lang(ctx, 'забирает иную сумму у частника')}", color=0x228b22)
        embedrela = disnake.Embed(title=f"<:pandaElf:1047241340657872948> {lang(ctx, 'Отношения')}",description=f"`/hug [{lang(ctx, 'участник')}]` - {lang(ctx, 'Обнять кого либо.')}\n`/pat [{lang(ctx, 'участник')}]` - {lang(ctx, 'Погладить кого либо')}",color=0x228b22)
        embedrp = disnake.Embed(title=f"<:shockedThinsk4:1047243843541680229> {lang(ctx, 'Ролевая игра')}",description=f"`/acc-register [{lang(ctx, 'имя')}]` - {lang(ctx, 'Создать нового персонажа')}\n`/acc-update-avatar [{lang(ctx, 'имя')}]` - {lang(ctx, 'Обновить аватар персонажу')}\n`/acc-all` - {lang(ctx, 'Посмотреть весь список персонажей')}\n`/acc-send [{lang(ctx, 'имя')}] [{lang(ctx, 'сообщения')}]` - {lang(ctx, 'Отправить сообщение от имени персонажа')}",color=0x228b22)
        embedsetts = disnake.Embed(title=f"⚙ {lang(ctx, 'Настройки')}",description=f"`/set-welcome-channel [{lang(ctx, 'канал')}]` - {lang(ctx, 'Устанавливает канал для уведомления о новых участниках')}\n`/set-bye-channel [{lang(ctx, 'канал')}]` - {lang(ctx, 'Установить канал для уведомления об ушедших участниках')}\n`/set-daily [{lang(ctx, 'сумма')}] - {lang(ctx, 'Установить сумму ежедневного приза, 0 если отключить')}`\n`/set-anti-badwords` - {lang(ctx, 'Включить запрет плохих слов')}\n`/set-work-price [{lang(ctx, 'сумма')}]` - {lang(ctx, 'Установить сумму которая будет выдаваться участника за работу')}\n`/set-lang [{lang(ctx, 'язык')}]` - {lang(ctx, 'Установить новый язык')}`\n`/disable-set [{lang(ctx, 'настройка')}]` - {lang(ctx, 'Отключить какую то настройку, настройка выбирается выпадающим списком')}\n`/ping` - {lang(ctx, 'Проверить работоспособность бота')}",color=0x228b22)

        status = True
        def check(msg):
            return msg.guild.id == ctx.guild.id and msg.author.id == ctx.author.id
        while status:
            try:
                btn = await bot.wait_for("button_click",timeout=80,check=check)
                await btn.response.defer()
                await ctx.edit_original_response(content="Ожидайте...")
                if btn.component.custom_id == "mus":
                    await ctx.edit_original_response(content=None, embed=embedmus)
                elif btn.component.custom_id == "games":
                    await ctx.edit_original_response(content=None, embed=embedgames)
                elif btn.component.custom_id == "mod":
                    await ctx.edit_original_response(content=None, embed=embedmod)
                elif btn.component.custom_id == "utils":
                    await ctx.edit_original_response(content=None, embed=embedutils)
                elif btn.component.custom_id == "eco":
                    await ctx.edit_original_response(content=None, embed=embedeco)
                elif btn.component.custom_id == "relaship":
                    await ctx.edit_original_response(content=None, embed=embedrela)
                elif btn.component.custom_id == "roleplay":
                    await ctx.edit_original_response(content=None, embed=embedrp)
                elif btn.component.custom_id == "setts":
                    await ctx.edit_original_response(content=None, embed=embedsetts)
            except asyncio.TimeoutError:
                status = False
                return await ctx.edit_original_response(components=None)


class Games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.slash_command(name="maths-minus",description="Игра в математику с вычитанием")
    async def mathsminus(self, ctx):
        await ctx.response.defer()
        first = random.randint(1, 20000)
        second = random.randint(1, 1500)
        reply = first - second
        await ctx.send(embed=disnake.Embed(title=lang(ctx,"Игра в математику"),description=lang(ctx,f"Сколько будет {first} - {second}?")))
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
                        return await ctx.send(embed=disnake.Embed(title=lang(ctx,"Ты ответил не числом!"),description=lang(ctx,f"Правильным ответом было {reply}"),color=disnake.Color.red()), delete_after = 10)
                    if user_repl == reply:
                        status = False
                        return await ctx.send(embed=disnake.Embed(title=lang(ctx,"Твой ответ верный!"),description=lang(ctx,"Поздравляю!"),color=disnake.Color.green()), delete_after = 20)
                    else:
                        status = False
                        return await ctx.send(embed=disnake.Embed(title=lang(ctx,"Ты ответил не верно!"),description=lang(ctx,f"Правильным ответом было {reply}"),color=disnake.Color.red()), delete_after = 10)

    @commands.command(name="maths-minus", usage="?maths-minus")
    async def _mathsminus_(self, ctx):
        first = random.randint(1, 20000)
        second = random.randint(1, 1500)
        reply = first - second
        await ctx.send(embed=disnake.Embed(title=lang(ctx,"Игра в математику"),description=lang(ctx,f"Сколько будет {first} - {second}?")))
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
                        return await ctx.send(embed=disnake.Embed(title=lang(ctx,"Ты ответил не числом!"),description=lang(ctx,f"Правильным ответом было {reply}"),color=disnake.Color.red()), delete_after = 10)
                    if user_repl == reply:
                        status = False
                        return await ctx.send(embed=disnake.Embed(title=lang(ctx,"Твой ответ верный!"),description=lang(ctx,"Поздравляю!"),color=disnake.Color.green()), delete_after = 20)
                    else:
                        status = False
                        return await ctx.send(embed=disnake.Embed(title=lang(ctx,"Ты ответил не верно!"),description=lang(ctx,f"Правильным ответом было {reply}"),color=disnake.Color.red()), delete_after = 10)

    @commands.slash_command(name="maths-plus",description="Игра в математику с сложением")
    async def mathsplus(self, ctx):
        await ctx.response.defer()
        first = random.randint(1, 1500)
        second = random.randint(1, 1500)
        reply = first + second
        await ctx.send(embed=disnake.Embed(title=lang(ctx,"Игра в математику"),description=lang(ctx,f"Сколько будет {first} + {second}?"))) #Отправляем пример
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
                        return await ctx.send(embed=disnake.Embed(title=lang(ctx,"Ты ответил не числом, поэтому оценка 2!"),description=lang(ctx,f"Правильным ответом было {reply}"),color=disnake.Color.red()), delete_after = 10) # Говорим о том что мы ответили НЕ числом
                    if user_repl == reply:
                        status = False
                        return await ctx.send(embed=disnake.Embed(title=lang(ctx,"Твой ответ верный!"),description=lang(ctx,"Поздравляю. Оценка 5."),color=disnake.Color.green()), delete_after = 20) # Поздравляем с верным ответом
                    else:
                        status = False
                        return await ctx.send(embed=disnake.Embed(title=lang(ctx,"Ты ответил не верно, поэтому оценка 2!"),description=lang(ctx,f"Правильным ответом было {reply}"),color=disnake.Color.red()), delete_after = 10) # Говорим об неверном ответе, и говорим верный ответ

    @commands.command(name="maths-plus", usage="?maths-plus")
    async def _mathsplus_(self, ctx):
        first = random.randint(1, 1500)
        second = random.randint(1, 1500)
        reply = first + second
        await ctx.send(embed=disnake.Embed(title=lang(ctx,"Игра в математику"),description=lang(ctx,f"Сколько будет {first} + {second}?"))) #Отправляем пример
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
                        return await ctx.send(embed=disnake.Embed(title=lang(ctx,"Ты ответил не числом, поэтому оценка 2!"),description=lang(ctx,f"Правильным ответом было {reply}"),color=disnake.Color.red()), delete_after = 10) # Говорим о том что мы ответили НЕ числом
                    if user_repl == reply:
                        status = False
                        return await ctx.send(embed=disnake.Embed(title=lang(ctx,"Твой ответ верный!"),description=lang(ctx,"Поздравляю. Оценка 5."),color=disnake.Color.green()), delete_after = 20) # Поздравляем с верным ответом
                    else:
                        status = False
                        return await ctx.send(embed=disnake.Embed(title=lang(ctx,"Ты ответил не верно, поэтому оценка 2!"),description=lang(ctx,f"Правильным ответом было {reply}"),color=disnake.Color.red()), delete_after = 10) # Говорим об неверном ответе, и говорим верный ответ

    @commands.slash_command(name="maths-multiply",description="Игра в математику с умножением")
    async def mathsmultiply(self, ctx):
        await ctx.response.defer()
        first = random.randint(1, 1000)
        second = random.randint(1, 1000)
        reply = first * second
        await ctx.send(embed=disnake.Embed(title=lang(ctx,"Игра в математику"),description=lang(ctx,f"Сколько будет {first} * {second}?")))
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
                        return await ctx.send(embed=disnake.Embed(title=lang(ctx,"Ты ответил не числом, поэтому оценка 2!"),description=lang(ctx,f"Правильным ответом было {reply}"),color=disnake.Color.red()), delete_after = 10)
                    if user_repl == reply:
                        status = False
                        return await ctx.send(embed=disnake.Embed(title=lang(ctx,"Твой ответ верный!"),description=lang(ctx,"Поздравляю. Оценка 5."),color=disnake.Color.green()), delete_after = 20)
                    else:
                        status = False
                        return await ctx.send(embed=disnake.Embed(title="Ты ответил не верно..."),description=f"Правильным ответом было {reply}",color=disnake.Color.red(), delete_after = 10)


    @commands.slash_command(name="tape", description="Крутануть рулетку на случайное кол-во баллов")
    @commands.cooldown(1, 60, commands.BucketType.user) # Ставим кулдаун
    async def tape(self, ctx):
        await ctx.response.defer()
        mynum = random.randint(20, 3000)
        type_of_num = "Error"
        type_color = 0xffffff
        if mynum == 20:
            type_of_num = "минимальное"
            type_color = 0xffffff
        if mynum > 20:
            type_of_num = "редкое"
            type_color = 0x0084ff
        if mynum > 100:
            type_of_num = "эпическое"
            type_color = 0x6f00ff
        if mynum > 1000:
            type_of_num = "мифическое"
            type_color = 0xff0000
        if mynum > 2500:
            type_of_num = "ЛЕГЕНДАРНОЕ"
            type_color = 0xffee00
        embedfortune = disnake.Embed(color=0x228b22).set_image(url="https://media.tenor.com/fJ10v8TLEi0AAAAC/wheel-of-fortune.gif")
        await ctx.send(embed=embedfortune, delete_after = 23)
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
                await ctx.send(embed=disnake.Embed(description=f"{ctx.author.mention} {random.choice(truth)}",color=0x228b22), delete_after = 10)
            if ctx.component.custom_id == "dare":
                await ctx.send(embed=disnake.Embed(description=f"{ctx.author.mention} {random.choice(dare)}",color=0x228b22), delete_after = 10)

    @commands.slash_command(name="heads-or-tails",description="Народный способ решить что либо, орёл или решка?")
    async def heads_or_tail(self, ctx):
        await ctx.response.defer()
        wars = [0, 1]
        wars = random.choice(wars)
        await ctx.send(embed=disnake.Embed(color=0x228b22).set_image(url="https://cdn.glitch.global/5fcfa7e8-8436-4acd-a852-e721cd1b531e/coin-flip-20.gif?v=1669511113445"), delete_after = 23)
        await asyncio.sleep(3)
        if wars == 1:
            return await ctx.edit_original_response(embed=disnake.Embed(title="Это Орёл!",color=0x228b22).set_image(url="https://w7.pngwing.com/pngs/73/614/png-transparent-double-headed-eagle-gold-coin-gold-gold-coin-gold-material.png"))
        if wars == 0:
            return await ctx.edit_original_response(embed=disnake.Embed(title="Это Решка!",color=0x228b22).set_image(url="https://newcoin.ru/wa-data/public/shop/products/59/08/859/images/3343/3343.970.JPG"))

    @commands.slash_command(name="door",description="Игра - Выбери правильную дверь!")
    async def door(self, ctx):
        await ctx.response.defer()
        door = random.choice([1,2,3])
        components = disnake.ui.Select(placeholder="Выбирайте...", options=[
            disnake.SelectOption(label="1🚪", value = "1", description="Выбрать первую дверь"),
            disnake.SelectOption(label="2🚪", value = "2", description="Выбрать вторую дверь"),
            disnake.SelectOption(label="3🚪", value = "3", description="Выбрать третью дверь")
        ])
        await ctx.send(embed=disnake.Embed(title="Выбери правильную дверь",description="Правильная или нет, зависит от твоей удачи...",color=0x228b22), components=components, delete_after = 30)
        try:
            slct = await self.bot.wait_for("message_interaction", timeout=20)
            if slct.values[0] == str(door):
                await ctx.edit_original_response(embed=disnake.Embed(title="Вы выбрали правильную дверь!",description="Поздравляю!",color=0x228b22), components=None)
                await slct.response.defer()
            else:
                await ctx.edit_original_response(embed=disnake.Embed(title="Не верно...",description=f"Правильной дверью была {door}. В следующий раз повезёт!", color=disnake.Color.red()), components=None)
                await slct.response.defer()
        except asyncio.TimeoutError:
            await ctx.edit_original_response(embed=disnake.Embed(title="Таймаут истёк!", color=disnake.Color.red()))

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
        await ctx.send(embed=disnake.Embed(title=f"Вопрос {number}",description=translator.translate(first_queston, dest="ru").text,color=0x228b22), components=component)
        while aki.progression <= 90 and stats:
            try:

                btn = await bot.wait_for("button_click", check=check, timeout=90)
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
                await ctx.edit_original_response(embed=disnake.Embed(title=f"Вопрос {number}",description=translator.translate(aki.question, dest="ru").text, color=0x228b22), components=component)
            except asyncio.TimeoutError:
                win = aki.win()
                stats = False
        win = aki.win()
        if win:
            await ctx.edit_original_response(embed=disnake.Embed(title=f"Это {win.name}!",description=f'{translator.translate(win.description, dest="ru")}',color=disnake.Color.red()).set_image(url = win.absolute_picture_path), components=None)
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
            await member.ban(reason=reason)
        except:
            return await ctx.send(embed=disnake.Embed(title=lang(ctx,"Извините, ошибка"),description=lang(ctx,"У меня не хватает прав\nВозможна другая причина ошибки."),color=disnake.Color.red()), delete_after = 10)
        await ctx.send(embed=disnake.Embed(title=f"<:correctCheckmark:1047244074350018700> {lang(ctx,'Успешно')}",description=f"{member.name} {lang(ctx,'теперь в бане')}",color=disnake.Color.green()), delete_after = 20)

    @commands.slash_command(name="kick", description="Выгнать кого с сервера.")
    @commands.has_permissions(kick_members = True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self, ctx, member: disnake.Member, reason = "не указана"):
        await ctx.response.defer()
        try:
            await member.kick()
        except:
            return await ctx.send(embed=disnake.Embed(title=lang(ctx,"Извините, ошибка"),description=lang(ctx,"У меня не хватает прав\nВозможна другая причина."),color=disnake.Color.red()), delete_after = 10)
        await ctx.send(embed=disnake.Embed(title=f"<:correctCheckmark:1047244074350018700> {lang(ctx,'Успешно!')}",description=f"{member.mention} {lang(ctx,'больше нет на сервере!')}", color=disnake.Color.green()), delete_after = 20)

    @commands.slash_command(name="mute",description="Заглушить кого либо на сервере")
    @commands.has_permissions(moderate_members = True)
    @commands.bot_has_permissions(moderate_members=True)
    async def mute(self, ctx, member: disnake.Member, time: int):
        await ctx.response.defer()
        try:
            await member.timeout(duration=datetime.timedelta(minutes=time))
        except:
            return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx,'Ошибка')}!",description=lang(ctx,"У меня не хватает прав.\nВозможна другая причина."),color=disnake.Color.red()), delete_after = 10)

        await ctx.send(embed=disnake.Embed(title=f"<:correctCheckmark:1047244074350018700> Успешно",description=f"Теперь {member.name} находиться в мьюте на {time} минут."), delete_after = 20)

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

        await ctx.send(embed=disnake.Embed(title=f"<:correctCheckmark:1047244074350018700> {lang(ctx,'Успешно')}",description=f"{lang(ctx,'Варн успешно нанесён на пользователя')} {member.mention}!\n{lang(ctx,'Произошло это')} <t:{utc_time}:R>").add_field(name=lang(ctx,"Номер случая"),value=f"{special}"), delete_after = 20)

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
                    message.append(f"{lang(ctx,'Номер случая')} - {special_id}:\n{lang(ctx,'Пользователь')} - {self.bot.get_user(user).mention}\n{lang(ctx,'Причина')} - {reas}\n")
        if users == []:
            return await ctx.send(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Ошибка",description="На сервере ещё нет варнов.",color=disnake.Color.red()), delete_after = 10)
        embed = disnake.Embed(title=lang(ctx,"Варн таблица🔍"), description="\n".join(list(map(str, message))))
        await ctx.send(embed=embed, delete_after = 40)

    @commands.slash_command(name="unwarn",description="Снять варн с пользователя")
    @commands.has_permissions(moderate_members = True)
    async def unwarn(self,ctx,номер_случая):
        await ctx.response.defer()
        special = номер_случая
        st = False
        try:
            special = int(special)
        except:
            return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx,'Ошибка')}",description=lang("Номер случая должен быть числом!"),color=disnake.Color.red()), delete_after = 10)
        try: #Пробуем
            with sqlite3.connect("database.db") as db:
                cursor = db.cursor()
                cursor.execute("DELETE FROM warns WHERE special_id = ?", (int(special),)) # Даём запрос на удаление
                await ctx.send(embed=disnake.Embed(title=f"<:correctCheckmark:1047244074350018700> {lang(ctx,'Успешно')}",description=lang(ctx,f"Номер случая {special} был удалён из базы данных"),color=0x228b22), delete_after = 20)
        except sqlite3.Error:
            return await ctx.send(lang(ctx,"Неверный номер случая!"), delete_after = 10)

    @commands.slash_command(name="purge",description="Очистить канал")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purg(self, ctx, count: int = commands.Param(description="Сколько сообщений удалить?")):
        await ctx.response.defer()
        await ctx.channel.purge(limit=int(count))
        await ctx.channel.send(f"<:correctCheckmark:1047244074350018700> {lang(ctx,f'Успешно очищено {count} сообщений!')}", delete_after = 20)


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
            d = "В сети"

        t = member.status
        if t == disnake.Status.offline:
            d = "Не в сети"

        t = member.status
        if t == disnake.Status.idle:
            d = "Не активен"

        t = member.status
        if t == disnake.Status.dnd:
            d = "Не беспокоить"

        img = Image.new('RGBA', (1000, 340), '#000000')
        backgr = ["https://cdn.glitch.global/5fcfa7e8-8436-4acd-a852-e721cd1b531e/1614397342_47-p-temnii-multyashnii-fon-64.png?v=1670188383348","https://cdn.glitch.global/5fcfa7e8-8436-4acd-a852-e721cd1b531e/1622768497_26-phonoteka_org-p-noch-art-minimalizm-krasivo-28.png?v=1670188403979","https://cdn.glitch.global/5fcfa7e8-8436-4acd-a852-e721cd1b531e/i.png?v=1670188415480"]
        r = requests.get(random.choice(backgr), stream = True)
        r = Image.open(io.BytesIO(r.content))
        r = r.convert("RGBA")
        r = r.resize((1000, 340))
        img.paste(r, (0, 0, 1000, 340))
        url = str(member.avatar.url)
        r = requests.get(url, stream = True)
        r = Image.open(io.BytesIO(r.content))
        r = r.convert('RGBA')
        r = r.resize((200, 200))
        img.paste(r, (30, 30, 230, 230))
        idraw = ImageDraw.Draw(img)
        name = member.name
        headline = ImageFont.truetype('gagalin.otf', size = 60)
        undertext = ImageFont.truetype('gagalin.otf', size = 36)
        idraw.text((250, 30), f'{name}', font=headline, fill="#ffffff")
        idraw.text((250, 100), f'#{member.discriminator}', font=undertext, fill="#ffffff")
        idraw.text((250, 140), f'ID: \n{member.id}', font = undertext, fill="#ffffff")
        idraw.text((250, 220), f'Статус: {d}', font = undertext, fill="#ffffff")
        idraw.text((250, 260), f"Кол-во очков: {scopes}", font = undertext, fill="#ffffff")
        idraw.text((250, 300), f"Баланс: {int(balance)}", font=undertext, fill="#ffffff")
        idraw.text((20, 290), f'{self.bot.user.name} Draw\'s', font=undertext, fill="#ffffff")
        img.save('user_card.png')
        await ctx.send(file=disnake.File("user_card.png"), delete_after = 50)

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
            return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx,'Ошибка')}",description=lang(ctx,"Не удалось выполнить данное действие."),color=disnake.Color.red()), delete_after = 10)
        await ctx.send(file=disnake.File("jacque.png"), delete_after = 50)

    @commands.slash_command(name="passed", description="Делает вашу аватарку в стиль GTA, миссия выполнена")
    async def passed(self, ctx, участник: disnake.Member = None):
        member = участник
        if not member:
            member = ctx.author
        await ctx.response.defer()
        request = requests.get(f"https://some-random-api.ml/canvas/overlay/passed?avatar={member.avatar.url}")
        json_load = request.url
        await ctx.send(embed=disnake.Embed(title=lang(ctx,"🔍Результат обработки")).set_image(url=json_load), delete_after = 20)

    @commands.slash_command(name="wasted", description="Делает вашу аватарку в стиль GTA, миссия провалена")
    async def wasted(self, ctx, участник: disnake.Member = None):
        member = участник
        if not member:
            member = ctx.author
        await ctx.response.defer()
        request = requests.get(f"https://some-random-api.ml/canvas/overlay/wasted?avatar={member.avatar.url}")
        json_load = request.url
        await ctx.send(embed=disnake.Embed(title=lang(ctx,"🔍Результат обработки")).set_image(url=json_load), delete_after = 20)

    @commands.slash_command(name="lgbt", description="Делает вам ЛГБТ аватарку")
    async def lgbt(self, ctx, участник: disnake.Member = None):
        member = участник
        if not member:
            member = ctx.author
        await ctx.response.defer()
        request = requests.get(f"https://some-random-api.ml/canvas/overlay/gay?avatar={member.avatar.url}")
        json_load = request.url
        await ctx.send(embed=disnake.Embed(title=lang(ctx,"🔍Результат обработки")).set_image(url=json_load), delete_after = 20)

    @commands.slash_command(name="jail", description="Делает вам аватарку, будто вы в тюрьме")
    async def jail(self, ctx, участник: disnake.Member = None):
        member = участник
        if not member:
            member = ctx.author
        await ctx.response.defer()
        request = requests.get(f"https://some-random-api.ml/canvas/overlay/jail?avatar={member.avatar.url}")
        json_load = request.url
        await ctx.send(embed=disnake.Embed(title=lang(ctx,"🔍Результат обработки")).set_image(url=json_load), delete_after = 20)

    @commands.slash_command(name="ussr", description="Переделывает вашу аватарку в стиле СССР")
    async def ussr(self, ctx, участник: disnake.Member = None):
        member = участник
        if not member:
            member = ctx.author
        await ctx.response.defer()
        request = requests.get(f"https://some-random-api.ml/canvas/overlay/comrade?avatar={member.avatar.url}")
        json_load = request.url
        await ctx.send(embed=disnake.Embed(title=lang(ctx,"🔍Результат обработки")).set_image(url=json_load), delete_after = 20)

    @commands.slash_command(name="triggered", description="Делает гифку вашей аватарки в стиле TRIGGERED")
    async def triggered(self, ctx, участник: disnake.Member = None):
        member = участник
        if not member:
            member = ctx.author
        await ctx.response.defer()
        request = requests.get(f"https://some-random-api.ml/canvas/overlay/triggered?avatar={member.avatar.url}")
        json_load = request.url
        await ctx.send(embed=disnake.Embed(title=lang(ctx,"🔍Результат обработки")).set_image(url=json_load), delete_after = 20)

    @commands.slash_command(name="pixelate",description="Пиксилизирует ваш аватар")
    async def pixelate(self, ctx, участник: disnake.Member = None):
        member = участник
        if not member:
            member = ctx.author
        await ctx.response.defer()
        request = requests.get(f"https://some-random-api.ml/canvas/misc/pixelate?avatar={member.avatar.url}")
        await ctx.send(embed=disnake.Embed(title=lang(ctx,"🔍Результат обработки")).set_image(url=request.url), delete_after = 20)

    @commands.slash_command(name="youtube-comment",description="Делает в стиле вас коментарий с ютуба")
    async def comment(self, ctx, коментарий, ник, аватар: disnake.Member = commands.Param(description="Вы можете указать с какого участника будет взят аватар")):
        avatar = аватар
        nick = ник
        if not avatar:
            avatar = ctx.author
        await ctx.response.defer()
        comment = коментарий
        request = requests.get(f"https://some-random-api.ml/canvas/misc/youtube-comment?avatar={avatar.avatar.url}&username={nick}&comment={comment}")
        await ctx.send(embed=disnake.Embed(title=lang(ctx,"🔍Результат обработки")).set_image(url=request.url), delete_after = 50)

    @commands.slash_command(name="voice",description="Создать озвучку")
    async def voice(self, ctx, текст = commands.Param(description="🔍 Какой текст озвучить?")):
        text = текст
        tts = gTTS(text=text, lang="ru")
        tts.save("voice.mp3")
        await ctx.send(lang(ctx,"🔍Результат"),file=disnake.File("voice.mp3"), delete_after = 50)

    @commands.slash_command(name="encode",description="Надо зашифровать текст в base64? Легко!")
    async def encode(self, ctx, текст = commands.Param(description="Текст, который надо зашифровать")):
        request = requests.get(f"https://some-random-api.ml/others/base64?encode={текст}")
        json_load = json.loads(request.text)
        await ctx.send(embed=disnake.Embed(title=lang(ctx,"🔍Результат"),description=json_load["base64"],color=0x228b22), delete_after = 20)

    @commands.slash_command(name="decode",description="Надо расшифровать текст из base64? Легко!")
    async def decode(self, ctx, текст = commands.Param(description="Текст base64")):
        request = requests.get(f"https://some-random-api.ml/others/base64?decode={текст}")
        json_load = json.loads(request.text)
        await ctx.send(embed=disnake.Embed(title=lang(ctx,"🔍Результат"),description=json_load["text"],color=0x228b22), delete_after = 20)

    @commands.slash_command(name="joke",description="Возвращает шутку")
    async def joke(self, ctx, язык = commands.Param(default="ru", description="На каком языке вы хотите увидеть шутку?", choices = [disnake.OptionChoice("Русский","ru"),disnake.OptionChoice("English","en"),disnake.OptionChoice("Украiньска","uk")])):
        await ctx.response.defer()
        api_result = requests.get("https://some-random-api.ml/others/joke")
        results = json.loads(api_result.text)
        text = translator.translate(results["joke"], dest=язык)
        await ctx.send(embed=disnake.Embed(title=f"{text.text}",description=lang(ctx,"Шутка взята с сайта **None**")), delete_after = 20)

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
        msg = await ctx.send(embed=disnake.Embed(title=lang(ctx,f"Пожалуйста, отправьте сообщение для голосовании"),description=lang(ctx,"Я поставлю на это сообщение реакций для голосования"), color=0x228b22))
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
            await ctx.edit_original_response(embed=disnake.Embed(title=lang(ctx,"Вы слишком долго отправляли сообщение!"),description=f"<:wrongCheckmark:1047244133078675607>{lang(ctx,'Ошибка')}",color=disnake.Color.red()))

    @commands.slash_command(name="random",description="Хотите выбрать что то рандомное? Используйте команду!")
    async def rando(self, ctx, вариации = commands.Param(description="Укажите вариации через пробел.")):
        select = random.choice(вариации.split())
        await ctx.response.defer()
        await ctx.send(embed=disnake.Embed(title=lang(ctx,"Я выбираю..."), color=0x228b22))
        await asyncio.sleep(3)
        await ctx.edit_original_response(embed=disnake.Embed(title=lang(ctx,"Я выбираю"),description=select + "!",color=0x228b22), delete_after = 20)

    @commands.slash_command(name="donate",description="Поддержать создателей бота")
    async def donate(self, ctx):
        await ctx.send(embed=disnake.Embed(title=lang(ctx,"Мы будем бесконечно благодарны даже 10 рублям!"),description=f"DonationAlerts - [**нажмите**](https://www.donationalerts.com/r/tjma)\n{lang(ctx,'Возможно будет добавлена оплата через наш сайт.')}",color=0x228b22), ephemeral=True)

    @commands.slash_command(name="quote",description="Цитатыыы великииих людеей")
    async def quote(self, ctx):
        await ctx.response.defer()
        r = requests.get("https://some-random-api.ml/animu/quote")
        r = json.loads(r.text)["sentence"]
        await ctx.send(embed=disnake.Embed(title=lang(ctx,"Цитата"),description=lang(ctx,r),color=0x228b22))

    @commands.slash_command(name="send",description="Отправить что то от имени бота")
    async def sen(self, ctx, текст = commands.Param(description="Что отправим?")):
        await ctx.channel.send(текст)
        await ctx.send("<:correctCheckmark:1047244074350018700>",ephemeral=True)

    @commands.slash_command(name="animego",description="Поиск аниме-фильмов на animego.net")
    async def anigo(self, ctx, название = commands.Param(description="Введите название вашего аниме")):
        await ctx.response.defer()
        name = название
        title = None
        uri = None
        description = None
        img = None
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://animego.org/search/all?q={name}", headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 YaBrowser/22.11.5.715 Yowser/2.5 Safari/537.36"}) as response:
                    r = await aiohttp.StreamReader.read(response.content)
                    soup = BS(r, "html.parser")
                    item = soup.find_all("div", {"class": "h5 font-weight-normal mb-2 card-title text-truncate"})
                    title = item[0].find("a").text.strip()
                    uri = item[0].find("a").get("href")
                async with session.get(uri, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 YaBrowser/22.11.5.715 Yowser/2.5 Safari/537.36"}) as response:
                    r = await aiohttp.StreamReader.read(response.content)
                    soup = BS(r, "html.parser")
                    description = soup.find("div", {"class": "description pb-3"}).text.strip()
                    img = soup.find("div", {"class": "anime-poster position-relative cursor-pointer"})
                    img = img.find("img").get("src")
        except IndexError:
            return await ctx.send(f"<:wrongCheckmark:1047244133078675607> {lang(ctx, f'Не удалось найти аниме с названием {name}')}")
        await ctx.send(embed=disnake.Embed(
            title = lang(ctx, title),
            description = lang(ctx, description) + f"\n\n[**{lang(ctx, 'Ссылка для просмотра')}**]({uri})",
            color = 0x228b22
        ).set_thumbnail(url = img), delete_after = 30)


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
            return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx, 'Ошибка')}",description=lang(ctx, "Кажеться, я не могу отправлять сообщения в этот канал"),color=disnake.Color.red()), delete_after = 10)
        else:
            await message.delete()
        try:
            Memory.write(f"channels/{ctx.guild.id}welcomechannel.txt", channel.id)
        except:
            return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx, 'Ошибка')}",description=lang(ctx, "Не удалось записать канал в память\nОбратитесь на наш сервер за помощью."), color=disnake.Color.red()), delete_after = 10)
        await ctx.send(embed=disnake.Embed(title=f"<:correctCheckmark:1047244074350018700> {lang(ctx, 'Успешно')}",description=lang(ctx, f"Теперь уведомления о зашедших участниках будут приходить в <#{channel.id}>"),color=0x228b22), delete_after = 20)

    @commands.slash_command(name="set-bye-channel", description="[АДМИН] Устанавливает канал для прощальных сообщений")
    @commands.has_permissions(manage_guild = True)
    async def bye_channel(self, ctx, канал: disnake.TextChannel):
        await ctx.response.defer()
        channel = канал

        try:
            message = await channel.send("https://tenor.com/view/harry-potter-funny-harrypotter-voldemort-gif-19286790")
        except:
            return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx, 'Ошибка')}",description=lang(ctx, "Кажеться, я не могу отправлять сообщения в этот канал"),color=disnake.Color.red()), delete_after = 10)
        else:
            await message.delete()
        try:
            Memory.write(f"channels/{ctx.guild.id}byechannel.txt", channel.id)
        except:
            return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx, 'Ошибка')}",description=lang(ctx, "Не удалось записать канал в память\nОбратитесь на наш сервер за помощью."), color=disnake.Color.red()), delete_after = 10)
        await ctx.send(embed=disnake.Embed(title=f"<:correctCheckmark:1047244074350018700> {lang(ctx, 'Успешно')}",description=lang(ctx, f"Теперь уведомления о ушедших участниках будут приходить в <#{channel.id}>"),color=0x228b22), delete_after = 20)

    @commands.slash_command(name="set-daily",description="[АДМИН] Установить ежедневный бонус")
    @commands.has_permissions(manage_guild = True)
    async def set_daily(self, ctx, сумма):
        await ctx.response.defer()
        summ = сумма
        try:
            summ = int(summ)
        except:
            return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx, 'Ошибка')}",description=lang(ctx, "Вы указали **НЕ** число"), color=disnake.Color.red()), delete_after = 10)
        try:
            Memory.write(f"daily/{ctx.guild.id}summ-of-daily.txt", str(summ))
        except:
            return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx, 'Ошибка')}",description=lang(ctx, "Не удалось записать число в память."),color=disnake.Color.red()), delete_after = 10)

        await ctx.send(embed=disnake.Embed(title=f"<:correctCheckmark:1047244074350018700> {lang(ctx, 'Успешно')}",description=lang(ctx, "Теперь каждый день участникам по ихнему желанию будет даваться эта сумма.")), delete_after = 20)

    @commands.slash_command(name="set-anti-badwords",description="Включить/выключить преды за плохие слова.")
    @commands.has_permissions(manage_guild = True)
    async def set_anti_badwords(self, ctx):
        await ctx.response.defer()
        if not ctx.guild:
            return await ctx.send(lang(ctx, "Удивительные факты: Я не могу включить поиск плохих слов в ЛС."),ephemeral=True)

        Memory.write(f"badwords/{ctx.guild.id}.txt", "you")
        await ctx.send(embed=disnake.Embed(title=f"<:correctCheckmark:1047244074350018700> {lang(ctx, 'Успешно')}",description=lang(ctx, "Теперь пользователям за плохие слова будут выдаваться преды."),color=0x228b22), delete_after = 20)

    @commands.slash_command(name="set-work-price",description="Установить получаемую сумму за работу, 0 если отключить")
    @commands.has_permissions(manage_guild = True)
    async def set_work_price(self, ctx, сумма: int = commands.Param(description="Какую сумму будут получать участники?")):
        await ctx.response.defer()
        Memory.write(f"works/{ctx.guild.id}.txt", сумма)
        await ctx.send(embed=disnake.Embed(title=f"<:correctCheckmark:1047244074350018700> {lang(ctx, 'Успешно')}",description=lang(ctx, "Теперь за работу будет выдаваться эта сумма.")), delete_after = 20)



    @commands.slash_command(name="disable-set", description="[АДМИН] Отключить какие либо настройки.")
    @commands.has_permissions(manage_guild = True)
    async def disable_sets(self, ctx, настройка = commands.Param(description="Укажите, какую настройку надо отключить", choices=[disnake.OptionChoice(name="Уведомления об зашедших",value="welcome_messages"),disnake.OptionChoice(name="Уведомления об ушедших",value="bye_messages"),disnake.OptionChoice(name="Варны за плохие слова",value="badwords")])):
        await ctx.response.defer()
        setting = настройка
        if setting == "welcome_messages":
            if os.path.isfile(f"channels/{ctx.guild.id}welcomechannel.txt"):
                os.remove(f"channels/{ctx.guild.id}welcomechannel.txt")
            else:
                return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx, 'Ошибка')}",description=lang(ctx, "Уведомления о пришедших участниках уже были отключены."), color=disnake.Color.red()), delete_after = 10)
            await ctx.send(embed=disnake.Embed(title=f"<:correctCheckmark:1047244074350018700> {lang(ctx, 'Успешно')}",description=lang(ctx, f"Уведомления об пришедших участниках больше не будут приходить."), color=0x228b22), delete_after = 20)
        if setting == "bye_messages":
            if os.path.isfile(f"channels/{ctx.guild.id}byechannel.txt"):
                os.remove(f"channels/{ctx.guild.id}byechannel.txt")
            else:
                return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx, 'Ошибка')}",description=lang(ctx, "Уведомления об ушедших участниках уже были отключены."), color=disnake.Color.red()), delete_after = 10)
            await ctx.send(embed=disnake.Embed(title=f"<:correctCheckmark:1047244074350018700> {lang(ctx, 'Успешно')}",description=lang(ctx, f"Уведомления об ушедших участниках больше не будут приходить."), color=0x228b22), delete_after = 20)
        if setting == "badwords":
            if os.path.isfile(f"badwords/{ctx.guild.id}.txt"):
                os.remove(f"badwords/{ctx.guild.id}.txt")
            else:
                return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx, 'Ошибка')}",description=lang(ctx, "Варны за плохие слова уже были отключены."), color=disnake.Color.red()), delete_after = 10)
            await ctx.send(embed=disnake.Embed(title=f"<:correctCheckmark:1047244074350018700> {lang(ctx, 'Успешно')}",description=lang(ctx, f"Варны за плохие слова больше не будут выдаваться."), color=0x228b22), delete_after = 20)



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

        await ctx.send(embed=disnake.Embed(title=f"{lang(ctx, 'Баланс пользователя')} **{member.name}**",description=f"{lang(ctx, 'Баланс')}: **{bals}**<:dollar:1051974269296451684>",color=0x228b22), delete_after = 20)

    @commands.slash_command(name="work",description="Пойти работать")
    @commands.cooldown(1, 120, commands.BucketType.user)
    async def work(self, ctx):
        await ctx.response.defer()
        work_price = 0
        try:
            work_price = Memory.read(f"works/{ctx.guild.id}.txt")
        except:
            return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx, 'Ошибка')}",description=lang(ctx, "Разработчики не установили цену, а для меня это значит что они отключили экономику\nЕсли вы считаете, что на сервере должна присутствовать экономика, обратитесь к администраций сервера"),color=disnake.Color.red()), delete_after = 10)
        work_price = int(work_price)
        if work_price == 0:
            return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx, 'Ошибка')}",description=lang(ctx, "На сервере отключена экономика."),color=disnake.Color.red()), delete_after = 10)
        await ctx.send(embed=disnake.Embed(title=lang(ctx, "Работаем..."),color=0x228b22), delete_after = 30)
        await asyncio.sleep(10)
        with sqlite3.connect("database.db") as db:
            cursor = db.cursor()
            cursor.execute("UPDATE balances SET user_balance = user_balance + ? WHERE guild_id = ? AND user_id = ?", (work_price, ctx.guild.id, ctx.author.id))
        await ctx.edit_original_response(embed=disnake.Embed(title=f"<:correctCheckmark:1047244074350018700> {lang(ctx, 'Успешно')}",description=f"{lang(ctx, f'Вы получили {work_price}')}<:dollar:1051974269296451684>",color=0x228b22))

    @commands.slash_command(name="daily",description="Ежедневная награда")
    @commands.cooldown(1, 72000, commands.BucketType.user)
    async def daily(self, ctx):
        await ctx.response.defer()
        summ = 0
        work_price = 0
        try:
            summ = Memory.read(f"daily/{ctx.guild.id}summ-of-daily.txt")
        except:
            return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>Ошибка",description=lang(ctx, "Разработчики не указывали сумму ни разу, и да бы не создать им проблем, я вам откажу."),color=disnake.Color.red()), delete_after = 10)
        try:
            work_price = Memory.read(f"works/{ctx.guild.id}.txt")
        except:
            return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>Ошибка",description="На этом сервере отключена экономика"), delete_after = 10)
        summ = int(summ)
        if summ == 0:
            return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>Ошибка",description="Ежедневная награда на этом сервере отсутствует",color=disnake.Color.red()), delete_after = 10)
        with sqlite3.connect("database.db") as db:
            cursor = db.cursor()
            cursor.execute("UPDATE balances SET user_balance = user_balance + ? WHERE guild_id = ? AND user_id = ?", (summ, ctx.guild.id, ctx.author.id))
        await ctx.send(embed=disnake.Embed(title=f"<:correctCheckmark:1047244074350018700> Успешно",description="Вы получили свой ежедневный бонус, следующий бонус вы получите через 72000 секунд(20ч)!",color=0x228b22), delete_after = 20)

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

        await ctx.send(embed=disnake.Embed(title=f"<:correctCheckmark:1047244074350018700> Успешно",description=f"Теперь у участника {summ} <:dollar:1051974269296451684>!",color=0x228b22), delete_after = 20)

    @commands.slash_command(name="reduce-money", description="Убавить деньги со счёта какого либо пользователя")
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
        await ctx.send(embed=disnake.Embed(title=f"<:correctCheckmark:1047244074350018700> Успешно",description=f"Теперь у пользователя {suma} <:dollar:1051974269296451684>!", color=0x228b22), delete_after = 20)

    @commands.slash_command(name="pay",description="Перевести деньги кому либо.")
    async def pay(self, ctx, участник: disnake.Member = commands.Param(description="Какому участнику хотите отправить (command.Args.summ) валюты?"), сумма: int = commands.Param(description="Какую сумму хотите отправить участнику?")):
        await ctx.response.defer()
        member = участник
        summ = сумма
        with sqlite3.connect("database.db") as db:
            cursor = db.cursor()
            for guild, user, balance in cursor.execute("SELECT * FROM balances WHERE user_id = ? AND guild_id = ?",(ctx.author.id, ctx.guild.id,)):
                if int(balance) < int(summ):
                    return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>Ошибка",description="У вас мало денег на счету",color=disnake.Color.red()), delete_after = 10)
            cursor.execute("UPDATE balances SET user_balance = user_balance - ? WHERE guild_id = ? AND user_id = ?", (summ, ctx.guild.id, ctx.author.id,))
            cursor.execute("UPDATE balances SET user_balance = user_balance + ? WHERE guild_id = ? AND user_id = ?", (summ, ctx.guild.id, member.id,))
        await ctx.send("<:correctCheckmark:1047244074350018700>", delete_after = 20)

    @commands.slash_command(name="ping",description="Проверка на работоспособность бота.")
    async def ping(self, ctx):
        await ctx.response.defer()
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
        await ctx.send(embed=disnake.Embed(title="Понг!",description=f"Моя задержка в связи: {ping}ms\nЭто {st}",color=col), delete_after = 20)

    @commands.slash_command(name="guilds-list",description="-", guild_ids=[1047126198330859580])
    async def guilds_list(self, ctx):

        if ctx.author.id == 1047108944721616916 or ctx.author.id == 848551340925517914 or ctx.author.id == 767076912023207938:
            await ctx.send(embed=disnake.Embed(title="Сервера, на которых я нахожусь",description=f"{self.bot.guilds}"), ephemeral=True)
        else:
            await ctx.send("А куда мы лезем?))",ephemeral=True)

    @commands.slash_command(name="users-cash",description="-", guild_ids=[1047126198330859580])
    async def users_cash(self, ctx):
        if ctx.author.id == 1047108944721616916 or ctx.author.id == 848551340925517914 or ctx.author.id == 767076912023207938:
            print(self.bot.users)
            await ctx.send("Информация выведена в консоль.", ephemeral=True)
        else:
            await ctx.send("А куда мы лезем?))",ephemeral=True)

    @commands.slash_command(name="voice-clients",description="-", guild_ids=[1047126198330859580])
    async def voice_clients(self, ctx):
        if ctx.author.id == 1047108944721616916 or ctx.author.id == 848551340925517914 or ctx.author.id == 767076912023207938:
            await ctx.send(f"Сейчас бот воспроизводит треки в {len(self.bot.voice_clients)} каналах!",ephemeral=True)
        else:
            await ctx.send("А куда мы лезем?))",ephemeral=True)

class Relationships(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="hug",description="Обнимашки с другим человеком")
    async def hug(self, ctx, участник: disnake.Member = commands.Param(description="Кого хотите обнять?")):
        await ctx.response.defer()
        if ctx.author.id == участник.id:
            return await ctx.send("Ты не можешь обнять сам себя.",ephemeral=True)
        request = requests.get("https://some-random-api.ml/animu/hug")
        json_load = json.loads(request.text)
        await ctx.send(embed=disnake.Embed(title=f"**{ctx.author.name}** обнял **{участник.name}**",color=0x228b22).set_image(url=json_load["link"]))

    @commands.slash_command(name="pat",description="Погладить другого человека")
    async def pat(self, ctx, участник: disnake.Member = commands.Param(description="Кого хотите погладить? <:Magic:1047241900370956298>")):
        await ctx.response.defer()
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
                return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>Ошибка",description="Такой персонаж уже вроде существует, не?",color=disnake.Color.red()), delete_after = 20)
        try:
            webhook = await ctx.channel.create_webhook(name=имя)
        except disnake.errors.HTTPException:
            await ctx.send(lang(ctx, "Слишком много HTTP запросов на данный момент, простите..."), delete_after = 20)
        else:
            await ctx.send("<:correctCheckmark:1047244074350018700>", delete_after = 20)

    @commands.slash_command(name="acc-send",description="Отправить что то от имени персонажа")
    @commands.bot_has_permissions(manage_webhooks = True)
    async def acc_send(self, ctx, имя = commands.Param(description="Напомните мне имя вашего персонажа..."), сообщение = commands.Param(description="Что хотите отправить?")):
        channel_webhooks = await ctx.channel.webhooks()
        my_webhook = None
        avatar_url = None
        for webhook in channel_webhooks:
            if webhook.user == bot.user and webhook.name == имя:
                my_webhook = webhook
        if not my_webhook:
            return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>Ошибка",description="Такого персонажа не существует!",color=disnake.Color.red()), ephemeral=True)
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
            await ctx.send("Слишком много HTTP запросов на данный момент, простите...", delete_after = 20)
        else:
            await ctx.send(f"<:correctCheckmark:1047244074350018700>",ephemeral=True)

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
            return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>Ошибка",description="Такого персонажа не существует!",color=disnake.Color.red()), ephemeral=True)
        await ctx.send(embed=disnake.Embed(title="Пожалуйста, отправьте сюда изображение",description="Это изображение будет поставлено как аватар",color=0xffff00), delete_after = 20)
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
                        return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>Ошибка",description="Вы не приложили никаких изображений, введите команду и отправьте мне сообщение с вложением",color=disnake.Color.red()), delete_after = 20)
        Memory.write(f"avatars/{ctx.channel.id}{имя}webhook.txt", url)
        await ctx.send("<:correctCheckmark:1047244074350018700>", delete_after = 20)

    @commands.slash_command(name="acc-remove",description="Удалить персонажа")
    @commands.has_permissions(manage_webhooks = True)
    @commands.bot_has_permissions(manage_webhooks = True)
    async def acc_rem(self, ctx, имя = commands.Param(description="Какого персонажа удаляем?")):
        await ctx.response.defer()
        my_webhook = None
        channel_webhooks = await ctx.channel.webhooks()
        for webhook in channel_webhooks:
            if webhook.user == bot.user and webhook.name == имя:
                my_webhook = webhook
        if not my_webhook:
            return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>Ошибка",description="Такого персонажа не существует!",color=disnake.Color.red()), delete_after = 10)
        try:
            await my_webhook.delete()
            if os.path.isfile(f"avatars/{ctx.channel.id}{имя}webhook.txt"):
                os.remove(f"avatars/{ctx.channel.id}{имя}webhook.txt")

        except disnake.errors.HTTPException:
            await ctx.send(lang(ctx, "Слишком много HTTP запросов на данный момент, простите..."), delete_after = 20)
        else:
            await ctx.send("<:correctCheckmark:1047244074350018700>", delete_after = 20)


    @commands.slash_command(name="acc-all",description="Посмотреть всех существующих персонажей в канале")
    async def acc_all(self, ctx):
        await ctx.response.defer()
        my_webhooks = []
        channel_webhooks = await ctx.channel.webhooks()
        for webhook in channel_webhooks:
            if webhook.user == bot.user:
                my_webhooks.append(webhook.name)

        await ctx.send(embed=disnake.Embed(title="Все ваши персонажи в этом канале",description="\n".join(list(map(str, my_webhooks))), color=0x228b22), delete_after = 20)

class Oauth:
    client_id = "1047125592220373075"
    client_secret = "qxXOHwHOJAdQApwn4LNCDWi3Gy8Dwitr"
    redirect_uri = "http://de4.bot-hosting.net:7259/save_me"
    scope = "identify%20guilds%20email"
    discord_login_url = f"https://discord.com/api/oauth2/authorize?client_id=1047125592220373075&redirect_uri=http%3A%2F%2Fde4.bot-hosting.net%3A7259%2Fsave_me&response_type=code&scope=identify%20guilds%20email"
    discord_token_url = "https://discord.com/api/oauth2/token"
    discord_api_url = "https://discord.com/api"


    @staticmethod
    def get_access_token(code):
        payload = {
            "client_id": Oauth.client_id,
            "client_secret": Oauth.client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": Oauth.redirect_uri,
            "scope": Oauth.scope
        }

        access_token = requests.post(url = Oauth.discord_token_url, data = payload).json()
        return access_token.get("access_token")


    @staticmethod
    def get_user_json(access_token):
        url = f"{Oauth.discord_api_url}/users/@me"
        headers = {"Authorization": f"Bearer {access_token}"}

        user_object = requests.get(url = url, headers = headers).json()
        return user_object

app = Flask(__name__)
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
app.config["SECRET_KEY"] = "Туалет_взломает_тебя_ночью_если_не_добавишь_моего_бота"

@bot.command(name="test", usage="?test <int:count>")
async def tst(ctx, count: int):
    await ctx.send(count, delete_after=5)

@bot.command(name="create-verify-interface")
async def cvi(ctx):
    if not ctx.guild.id == 1047126198330859580:
        return
    await ctx.message.delete()
    await ctx.channel.send("А это верификация <3\nЕсли ты прочитал все правила выше, а также согласен соблюдать их, нажми кнопку ниже 👇", components = [disnake.ui.Button(emoji="🟩", style=disnake.ButtonStyle.success, custom_id="verify")])

@bot.user_command(name="Инфо о пользователе")
async def infouser(ctx, member: disnake.User):
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
            d = lang(ctx,"В сети")

        t = member.status
        if t == disnake.Status.offline:
            d = lang(ctx,"Не в сети")

        t = member.status
        if t == disnake.Status.idle:
            d = lang(ctx,"Не активен")

        t = member.status
        if t == disnake.Status.dnd:
            d = lang(ctx,"Не беспокоить")

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
        idraw.text((125, 110), f'{lang(ctx,"Статус")}: {d}', font = undertext, fill="#ffffff")
        idraw.text((125, 130), f"{lang(ctx,'Кол-во очков')}: {scopes}", font = undertext, fill="#ffffff")
        idraw.text((125, 150), f"{lang(ctx,'Баланс')}: {int(balance)}", font=undertext, fill="#ffffff")
        idraw.text((10, 155), f'{bot.user.name} Draw\'s', font=undertext, fill="#ffffff")
        img.save('user_card.png')
        await ctx.send(file=disnake.File("user_card.png"))

@bot.user_command(name="Поприветствовать")
async def infouser(ctx, member: disnake.User):
    await ctx.response.defer()
    sents = [f"На сервере объявился {member.mention}. Попросите его заказать пиццу для сервера **{member.guild.name}**!",f"У нас новенький, {member.mention}, представься, пускай тебя узнает сервер **{member.guild.name}**!",f"{member.mention} пришёл на сервер, познакомься со сервером **{member.guild.name}**"]
    await ctx.send(lang(ctx, random.choice(sents)))

@bot.event
async def on_ready():
    await bot.change_presence(status=disnake.Status.dnd, activity=disnake.Activity(type=disnake.ActivityType.streaming, url="https://www.twitch.tv/tjma_",name=f"de4.bot-hosting.net:7259 [{len(bot.guilds)}]"))
    with sqlite3.connect("database.db") as db:
        cursor = db.cursor()

        cursor.execute("CREATE TABLE IF NOT EXISTS warns(special_id INTEGER PRIMARY KEY, guild_id INTEGER, user_id INTEGER, reason TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS balances(guild_id INTEGER, user_id INTEGER, user_balance INTEGER)")
        cursor.execute("CREATE TABLE IF NOT EXISTS sugestions(guild_id INTEGER, sugestion TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS songs(name VARCHAR, requester INTEGER, author VARCHAR, id INTEGER, albumId INTEGER, lyrics TEXT, guild INTEGER, image TEXT,position INTEGER PRIMARY KEY)")
        cursor.execute("CREATE TABLE IF NOT EXISTS langs(lang VARCHAR, guild INTEGER)")
        cursor.execute("CREATE TABLE IF NOT EXISTS userlikes(user INTEGER, trackName VARCHAR, trackId INTEGER)")

        #db.execute('SET NAMES warns;')
        #db.execute('SET CHARACTER SET balances;')
    with sqlite3.connect("db.db") as db:
        c = db.cursor()

        c.execute("CREATE TABLE IF NOT EXISTS intents(ini TEXT, outi TEXT)")
    try:
        asyncio.get_running_loop()
    except:
        print("Creating loop")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

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
    await bot.change_presence(status=disnake.Status.dnd, activity=disnake.Activity(type=disnake.ActivityType.streaming, url="https://www.twitch.tv/tjma_",name=f"de4.bot-hosting.net:7259 [{len(bot.guilds)}]"))

@bot.event
async def on_guild_remove(guild):
    await bot.change_presence(status=disnake.Status.dnd, activity=disnake.Activity(type=disnake.ActivityType.streaming, url="https://www.twitch.tv/tjma_",name=f"de4.bot-hosting.net:7259 [{len(bot.guilds)}]"))


@bot.event
async def on_slash_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f'Повтори попытку через {round(error.retry_after, 2)} секунд.',ephemeral=True)
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>Ошибка",description="У вас недостаточно прав.",color=disnake.Color.red()),ephemeral=True)
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>Ошибка",description="У меня недостаточно прав.",color=disnake.Color.red()), ephemeral=True)
    elif isinstance(error, commands.errors.NSFWChannelRequired):
        await ctx.send("<:wrongCheckmark:1047244133078675607> повторите команду, но только в nsfw канале!")
    else:
        print(error)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.send(embed=disnake.Embed(title="Использование команды:",description=f"```{ctx.command.usage}```\nВы не указали какой то аргумент.",color=disnake.Color.red()), delete_after=15)
    elif isinstance(error, commands.errors.BadArgument):
        await ctx.send(embed=disnake.Embed(title="Использование команды:",description=f"```{ctx.command.usage}```\nВы указали какой то из аргументов неправильно.",color=disnake.Color.red()), delete_after=15)
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
    messages = [f"Пользователь {member.mention}, пиццу так и никто не получил...",f"{member.mention} покинул нас!",f"{member.mention} ушёл от нас..."]
    await channel.send(embed=disnake.Embed(description=random.choice(messages),color=0x228b22).set_image(url=request.url))

@bot.event
async def on_button_click(ctx):
    ki = ctx.component.custom_id
    if ki == "next":
        try:
            error = await Song().skip(ctx)
        except AttributeError:
            pass
        if error == "notState": return await ctx.send("<:wrongCheckmark:1047244133078675607>Сейчас ничего не играет!",ephemeral=True)
        await ctx.response.defer()
    elif ki == "stop":
        error = await Song().stop(ctx)
        if error == "notState": return await ctx.send("<:wrongCheckmark:1047244133078675607>Сейчас ничего не играет!",ephemeral=True)
        await ctx.response.defer()
    elif ki == "replay":
        voice_state = ctx.guild.voice_client
        if voice_state and voice_state.is_playing():
            await Song().replay(ctx)
        else:
            await ctx.send("<:wrongCheckmark:1047244133078675607>Сейчас ничего не играет!",ephemeral=True)
    elif ki == "pause":
        voice_state = ctx.guild.voice_client
        if voice_state and voice_state.is_playing():
            Song().pause(ctx.guild)
        elif voice_state and not voice_state.is_playing():
            Song().resume(ctx.guild)
        else:
           await ctx.send("<:wrongCheckmark:1047244133078675607>Сейчас ничего не играет!",ephemeral=True)
        await ctx.response.defer()
    elif ki == "text":
        lyrics = Song().lyrics(ctx)
        if not lyrics['lyrics']: return await ctx.send(embed=disnake.Embed(title=f"<:wrongCheckmark:1047244133078675607>{lang(ctx,'Ошибка')}",description=lang(ctx,"Текст этой песни не доступен"),color=disnake.Color.red()))
        await ctx.send(embed=disnake.Embed(title=f"🔍 {lang(ctx,'Текст от трека')} **{lyrics['name']}**",description=lyrics["lyrics"]))
    elif ki == "verify":
        await ctx.author.add_roles(ctx.guild.get_role(1072833325661700096))
        await ctx.send("Ты подтверждён.", ephemeral=True)

@bot.event
async def on_message(msg):
    if msg.author.bot:
        return
    #return await msg.reply(embed=disnake.Embed(title="<:wrongCheckmark:1047244133078675607>Неизвестная ошибка",description="Обратитесь к администраций",color=disnake.Color.red()))
    await bot.process_commands(msg)
    if bot.user.mentioned_in(msg): #если бот упомянут
        await msg.reply(await chat.get_receive_async(msg.content))


    content = msg.content.lower()
    for_check = content.translate(str.maketrans('', '', string.punctuation))
    bad_words = ["сука","ёбаный","блять","пидор","пидора","бля","ебать","нахуй","хуй","заебал","заебись","ахуенно","ахуено","пиздюк","нахуя","хуйня","ёбаный","ебаный","лошара","лох","пиздец","пздц","пизда","педик","канаве","мудила","мудак","конченный","конченый","кончаю","конча","шлюха","гей","лесби","лесбиянка","трах","трахаться","сосаться","ебаться","доёбываться","залупа","хуя","блядина","гавнозалупа","пенис","рукожоп","хуярище","боданище","ебланище","ебал","хуйло","еблан","ебало","ебальник","ебанный","херня","похуй","ахуенна"]
    words_content = for_check.split()
    try:
        Memory.read(f"badwords/{msg.guild.id}.txt")
    except:
        pass
    else:
        if msg.author.id == 966494653375475762 or msg.author.id == 1047108944721616916 or msg.author.id == 1014167436481806346:
            pass
        else:
            for word in words_content:
                if word in bad_words:
                    member = msg.author
                    reason = "Автомод: Плохие слова"
                    with sqlite3.connect("database.db") as db:
                        cursor = db.cursor()
                        cursor.execute("INSERT INTO warns(guild_id, user_id, reason) VALUES(?, ?, ?)", (msg.guild.id, member.id, reason))
                    try:
                        await msg.delete()
                    except:
                        pass
                    finally:
                        await msg.channel.send(f"<:policePanda:1047242230651437077> {msg.author.mention} На этом сервере запрещены плохие слова! Вам вынесен варн в виде наказания.")
    webhooks = None
    try:
        webhooks = await msg.channel.webhooks()
    except:
        pass
    else:
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
                        pass

async def get_stats():
    return {"servers": len(bot.guilds), "shards": 0, "users": len(bot.users)}


async def on_success_posting():
    print("stats posting successfully")

boticord_client = BoticordClient("9d37e475-5e30-401d-a7f9-c4e2ffe75e7a", version=2)
autopost = (
    boticord_client.autopost()
    .init_stats(get_stats)
    .on_success(on_success_posting)
    .start()
)

@app.route("/")
def index():
    if "id" in session:
        usr_id = session.get("id")
        user = bot.get_user(int(usr_id))
        return render_template("index.html",bot_name=bot.user.name,servers=len(bot.guilds),users=len(bot.users),user=user)
    else:
        return render_template("index.html",bot_name=bot.user.name,servers=len(bot.guilds),users=len(bot.users),user=None)

@app.route("/login")
def log_in():
    if not "id" in session:
        return redirect("https://discord.com/api/oauth2/authorize?client_id=1047125592220373075&redirect_uri=http%3A%2F%2Fde4.bot-hosting.net%3A7259%2Fsave_me&response_type=code&scope=identify%20guilds%20email")
    else:
        return redirect(url_for("profile"))

@app.route("/save_me")
def save_me():
    code = flask.request.args.get("code")
    at = Oauth.get_access_token(code)

    user = Oauth.get_user_json(at)
    session["id"] = user.get("id")
    return redirect("http://de4.bot-hosting.net:7259/profile")

@app.route("/profile")
def profile():
    if not "id" in session:
        return redirect("https://discord.com/api/oauth2/authorize?client_id=1047125592220373075&redirect_uri=http%3A%2F%2Fde4.bot-hosting.net%3A7259%2Fsave_me&response_type=code&scope=identify%20guilds%20email")
    uid = session.get("id")
    user = bot.get_user(int(uid))
    scopes = 0
    try:
        scopes = Memory.read(f"scope/{uid}balls.txt")
    except:
        scopes = 0
    return render_template("profile.html", user=user, bot=bot, scope_count=scopes)

@app.route("/dashboard")
def dashboard():
    if not "id" in session:
        return redirect("https://discord.com/api/oauth2/authorize?client_id=1047125592220373075&redirect_uri=http%3A%2F%2Fde4.bot-hosting.net%3A7259%2Fsave_me&response_type=code&scope=identify%20guilds%20email")
    uid = session.get("id")
    user = bot.get_user(int(uid))
    user_guilds = []
    for guild in bot.guilds:
        if guild.owner_id == user.id:
            user_guilds.append(guild)
    return render_template("guilds.html", guilds=user_guilds)

@app.route("/dashboard/<int:guild>", methods = ["get","post"])
def dash(guild):
    if not "id" in session:
        return redirect("https://discord.com/api/oauth2/authorize?client_id=1047125592220373075&redirect_uri=http%3A%2F%2Fde4.bot-hosting.net%3A7259%2Fsave_me&response_type=code&scope=identify%20guilds%20email")
    uid = session.get("id")
    user = bot.get_user(int(uid))
    server = bot.get_guild(int(guild))
    if flask.request.method == "GET":
        if not server:
            return redirect(url_for("dashboard"))
        if not server.owner_id == user.id:
            return redirect(url_for("dashboard"))
        return render_template("dashboard.html", guild=server, text_count=len(server.text_channels), voice_count=len(server.voice_channels))

@app.route("/dashboard/welcome/<int:guild>", methods = ["get","post"])
def welcome_messages(guild):
    if not "id" in session:
        return redirect("https://discord.com/api/oauth2/authorize?client_id=1047125592220373075&redirect_uri=http%3A%2F%2Fde4.bot-hosting.net%3A7259%2Fsave_me&response_type=code&scope=identify%20guilds%20email")
    uid = session.get("id")
    user = bot.get_user(int(uid))
    server = bot.get_guild(int(guild))
    if flask.request.method == "GET":
        if not server:
            return redirect(url_for("dashboard"))
        if not server.owner_id == user.id:
            return redirect(url_for("dashboard"))
        return render_template("welcome_messages.html", guild=server)
    else:
        welc = flask.request.form.get("welcome")
        bye = flask.request.form.get("bye")
        if welc == "None":
            if os.path.isfile(f"channels/{server.id}welcomechannel.txt"):
                os.remove(f"channels/{server.id}welcomechannel.txt")
        else:
            Memory.write(f"channels/{server.id}welcomechannel.txt", int(welc))

        if bye == "None":
            if os.path.isfile(f"channels/{server.id}byechannel.txt"):
                os.remove(f"channels/{server.id}byechannel.txt")
        else:
            Memory.write(f"channels/{server.id}byechannel.txt", int(bye))
        return render_template("welcome_messages.html", guild=server)

@app.route("/dashboard/music/<int:guild>")
def music_queue(guild):
    if not "id" in session:
        return redirect("https://discord.com/api/oauth2/authorize?client_id=1047125592220373075&redirect_uri=http%3A%2F%2Fde4.bot-hosting.net%3A7259%2Fsave_me&response_type=code&scope=identify%20guilds%20email")
    uid = session.get("id")
    user = bot.get_user(int(uid))
    server = bot.get_guild(int(guild))
    if not server:
        return redirect(url_for("dashboard"))
    if not server.owner_id == user.id:
        return redirect(url_for("dashboard"))
    if server.voice_client and server.voice_client.is_playing():
        pass
    else:
        return render_template("music_queue.html", guild=server, guild_queue_text=[],track_title="Сейчас ничего не играет!")
    trak = Song.now_playing(server)
    queue = Song.parse_queue(server)
    return render_template("music_queue.html", guild=server, guild_queue_text=queue["texts"],track_title=trak["name"], track_url=trak["uri"],track_artist=trak["artist"],requester=trak["requester"],track_pos=trak["pos"])

def run_flask():
    app.run(host="0.0.0.0", port=7259)

Thread(target=run_flask).start()
bot.run("Писька бобра") # Запуск бота
