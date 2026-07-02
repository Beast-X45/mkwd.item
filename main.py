import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import datetime
import asyncio
import discord
from discord.ext import commands
from discord import app_commands

# ==================================================
# 1. 軽量ダミーサーバー（Renderの24時間維持用）
# ==================================================
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
        
    def log_message(self, format, *args):
        return

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()


# ==================================================
# 2. Discord Botの初期設定
# ==================================================
INTENTS = discord.Intents.default()
INTENTS.message_content = True  # 「!1.7.0」の検知に必須

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=INTENTS)

    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot()

# 【修正点】拡張子を .wav に変更しました
PLAY_SCHEDULE = [
    {"delay": 23.0, "file": "sound1.wav"},
    {"delay": 28.0, "file": "sound2.wav"},
    {"delay": 33.0, "file": "sound3.wav"},
    {"delay": 43.0, "file": "sound4.wav"}
]


# ==================================================
# 3. 機能実装部分
# ==================================================

# ① /join コマンド（スラッシュコマンド）
@bot.tree.command(name="join", description="実行者が参加しているボイスチャンネルに参加します")
async def join(interaction: discord.Interaction):
    if interaction.user.voice is None or interaction.user.voice.channel is None:
        await interaction.response.send_message("エラー: 先にボイスチャンネルに参加してください！", ephemeral=True)
        return

    voice_channel = interaction.user.voice.channel
    voice_client = interaction.guild.voice_client

    if voice_client is None:
        await voice_channel.connect()
        await interaction.response.send_message(f"**{voice_channel.name}** に参加しました。")
    else:
        await voice_client.move_to(voice_channel)
        await interaction.response.send_message(f"**{voice_channel.name}** に移動しました。")


# ② 「!1.7.0」メッセージ検知 ＆ 4連続タイマー再生
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content == "!1.7.0":
        voice_client = message.guild.voice_client

        if voice_client is not None and voice_client.is_connected():
            
            sent_time = message.created_at
            
            # ログ用（日本時間）
            jst_timezone = datetime.timezone(datetime.timedelta(hours=9))
            sent_time_jst = sent_time.astimezone(jst_timezone).strftime('%H:%M:%S.%f')[:-3]
            print(f"\n[Log] --- タイマー開始 ---")
            print(f"[Log] メッセージ送信時刻: {sent_time_jst}")

            for task in PLAY_SCHEDULE:
                target_delay = task["delay"]
                audio_file = task["file"]

                target_time = sent_time + datetime.timedelta(seconds=target_delay)
                
                now = datetime.datetime.now(datetime.timezone.utc)
                remaining_time = (target_time - now).total_seconds()

                if remaining_time > 0:
                    await asyncio.sleep(remaining_time)

                if voice_client is not None and voice_client.is_connected():
                    # タイミング遵守のため、前の音が残っていれば強制停止
                    if voice_client.is_playing():
                        voice_client.stop()

                    if os.path.exists(audio_file):
                        source = discord.FFmpegPCMAudio(audio_file)
                        voice_client.play(source)
                        
                        play_time_jst = datetime.datetime.now(datetime.timezone.utc).astimezone(jst_timezone).strftime('%H:%M:%S.%f')[:-3]
                        print(f"[Log] 再生成功: {audio_file} (時刻: {play_time_jst} / 送信から {target_delay}秒後)")
                    else:
                        await message.channel.send(f"エラー: 音声ファイル `{audio_file}` が見つかりません。")
                else:
                    print("[Error] 再生直前にボイスチャンネルから切断されていました。")
                    break

            print(f"[Log] --- タイマー終了 ---\n")
        else:
            await message.channel.send("エラー: Botがボイスチャンネルに参加していません。先に `/join` を使用してください。")

    await bot.process_commands(message)


# 起動確認用
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    print("----------------")


# ==================================================
# 4. Botの起動処理
# ==================================================
if __name__ == "__main__":
    TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("Error: DISCORD_BOT_TOKEN が環境変数に設定されていません。")
