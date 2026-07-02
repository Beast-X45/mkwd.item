import os
import asyncio

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# サーバーごとの状態
guild_data = {}


# ----------------------------
# 起動
# ----------------------------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")


# ----------------------------
# /join
# ----------------------------
@bot.tree.command(name="join", description="ボイスチャンネルに参加します")
async def join(interaction: discord.Interaction):

    if interaction.user.voice is None:
        await interaction.response.send_message(
            "先にボイスチャンネルへ参加してください。",
            ephemeral=True
        )
        return

    voice_channel = interaction.user.voice.channel

    if interaction.guild.voice_client:
        await interaction.guild.voice_client.move_to(voice_channel)
        voice = interaction.guild.voice_client
    else:
        voice = await voice_channel.connect()

    guild_data[interaction.guild.id] = {
        "text_channel": interaction.channel.id,
        "is_playing": False
    }

    await interaction.response.send_message(
        f"{voice_channel.name} に参加しました。"
    )


# ----------------------------
# /leave
# ----------------------------
@bot.tree.command(name="leave", description="ボイスチャンネルから退出します")
async def leave(interaction: discord.Interaction):

    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()

    guild_data.pop(interaction.guild.id, None)

    await interaction.response.send_message("退出しました。")


# ----------------------------
# 音声再生
# ----------------------------
async def play_sound(voice_client, file_path):

    finished = asyncio.Event()

    def after(error):
        if error:
            print(error)

        bot.loop.call_soon_threadsafe(finished.set)

    source = discord.FFmpegPCMAudio(file_path)

    voice_client.play(source, after=after)

    await finished.wait()


# ----------------------------
# シーケンス再生
# ----------------------------
async def play_sequence(message):

    guild = message.guild
    voice = guild.voice_client

    if voice is None:
        return

    guild_data[guild.id]["is_playing"] = True

    schedule = [
        (23, "assets/sound1.wav"),
        (28, "assets/sound2.wav"),
        (33, "assets/sound3.wav"),
        (44, "assets/sound4.wav"),
    ]

    start = asyncio.get_running_loop().time()

    for target_time, file in schedule:

        now = asyncio.get_running_loop().time()
        wait = target_time - (now - start)

        if wait > 0:
            await asyncio.sleep(wait)

        if not voice.is_connected():
            break

        await play_sound(voice, file)

    guild_data[guild.id]["is_playing"] = False


# ----------------------------
# メッセージ監視
# ----------------------------
@bot.event
async def on_message(message):

    await bot.process_commands(message)

    if message.author.bot:
        return

    if message.guild is None:
        return

    if message.guild.id not in guild_data:
        return

    data = guild_data[message.guild.id]

    # /joinしたチャンネル以外は無効
    if message.channel.id != data["text_channel"]:
        return

    if message.content != "!1.7.0":
        return

    # 再生中なら無視
    if data["is_playing"]:
        return

    if message.guild.voice_client is None:
        return

    asyncio.create_task(play_sequence(message))


# ----------------------------
# 全員VC退出
# ----------------------------
@bot.event
async def on_voice_state_update(member, before, after):

    voice = member.guild.voice_client

    if voice is None:
        return

    channel = voice.channel

    humans = [
        m
        for m in channel.members
        if not m.bot
    ]

    if len(humans) == 0:

        await voice.disconnect()

        guild_data.pop(member.guild.id, None)


bot.run(TOKEN)
