from __future__ import annotations
import discord
from discord.ext import commands
from discord import app_commands
from utils.supabase_manager import SupabaseManager
import os


class AdminCog(commands.Cog):
    """管理者権限を持つユーザー向けのサーバー設定コマンドを管理するCog。"""

    def __init__(self, bot: commands.Bot, supabase_manager: SupabaseManager) -> None:
        self.bot = bot
        self.supabase_manager = supabase_manager

    class ConfigModal(discord.ui.Modal, title="サーバー設定"):
        """サーバー固有の設定を管理するためのモーダルUI。"""
        def __init__(self, supabase_manager: SupabaseManager, guild_id: int):
            super().__init__()
            self.supabase_manager = supabase_manager
            self.guild_id = guild_id

            # 通知チャンネルID入力フィールド
            self.notification_channel_id_input = discord.ui.TextInput(
                label="通知チャンネルID (任意)",
                placeholder="タスク通知を送信するチャンネルのIDを入力してください。",
                required=False,
                max_length=20, # DiscordチャンネルIDは通常18-19桁
                style=discord.TextStyle.short
            )
            self.add_item(self.notification_channel_id_input)

        async def on_submit(self, interaction: discord.Interaction) -> None:
            """モーダルが送信されたときに設定を保存する処理。"""
            channel_id_str = self.notification_channel_id_input.value.strip()
            notification_channel_id = None

            # チャンネルIDのバリデーション
            if channel_id_str:
                try:
                    notification_channel_id = int(channel_id_str)
                    # 指定されたIDが現在のギルド内のテキストチャンネルであるかを確認
                    channel = interaction.guild.get_channel(notification_channel_id)
                    if not isinstance(channel, discord.TextChannel):
                        await interaction.response.send_message("⚠️ 指定されたチャンネルIDはテキストチャンネルではありません。", ephemeral=True)
                        return
                except ValueError:
                    await interaction.response.send_message("⚠️ 無効なチャンネルIDです。数字を入力してください。", ephemeral=True)
                    return

            try:
                # 既存のサーバー設定を取得
                existing_config = await self.supabase_manager.get_config(self.guild_id)

                if existing_config:
                    # 既存の設定を更新
                    update_data = {"notification_channel_id": notification_channel_id}
                    await self.supabase_manager.update_config(self.guild_id, update_data)
                    await interaction.response.send_message("✅ サーバー設定を更新しました。", ephemeral=True)
                else:
                    # 新しい設定を挿入
                    # add_configはguild_idとnotification_channel_idを直接受け取ることを想定
                    await self.supabase_manager.add_config(self.guild_id, notification_channel_id=notification_channel_id)
                    await interaction.response.send_message("✅ サーバー設定を新規作成しました。", ephemeral=True)

            except Exception as e:
                # データベース操作中のエラーを捕捉し、ユーザーに通知
                print(f"Error updating/adding config for guild {self.guild_id}: {e}")
                await interaction.response.send_message(f"❌ 設定の保存中にエラーが発生しました: {e}", ephemeral=True)

        async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
            """モーダル処理中にエラーが発生した場合のハンドラ。"""
            await interaction.response.send_message(f"❌ モーダル処理中にエラーが発生しました: {error}", ephemeral=True)

    @app_commands.command(name="config", description="サーバー固有のBot設定を行います（管理者のみ）。")
    @app_commands.checks.has_permissions(administrator=True)
    async def config(self, interaction: discord.Interaction) -> None:
        """サーバー管理者がBotの動作設定を行うためのコマンド。"""
        # 設定用のモーダルUIを作成
        modal = self.ConfigModal(self.supabase_manager, interaction.guild_id)

        # 現在の設定を読み込み、モーダルに初期値を設定
        try:
            current_config = await self.supabase_manager.get_config(interaction.guild_id)
            if current_config and current_config.get("notification_channel_id") is not None:
                # 現在の通知チャンネルIDがあれば、入力フィールドにデフォルト値として設定
                modal.notification_channel_id_input.default_value = str(current_config["notification_channel_id"])
        except Exception as e:
            # 設定の読み込みに失敗しても、モーダルは表示を続行
            print(f"Error loading current config for guild {interaction.guild_id}: {e}")
            # ユーザーにはエラーを直接通知せず、モーダルを表示

        # 設定モーダルをユーザーに送信
        try:
            await interaction.response.send_modal(modal)
        except Exception as e:
            # モーダルの送信自体に失敗した場合、エラーメッセージを送信
            print(f"Error sending config modal for guild {interaction.guild_id}: {e}")
            await interaction.response.send_message(f"❌ 設定モーダルの表示中にエラーが発生しました: {e}", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    """AdminCogをボットにセットアップする関数。"""
    # 環境変数からSupabaseのURLとキーを取得
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    # 環境変数が設定されているか確認
    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL or SUPABASE_KEY environment variables are not set.")
        # 環境変数が不足している場合は、ボットの起動を停止するために例外を発生させる
        raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY environment variables.")

    # SupabaseManagerのインスタンスを作成
    supabase_manager = SupabaseManager(supabase_url, supabase_key)

    # AdminCogを初期化し、ボットに追加
    await bot.add_cog(AdminCog(bot, supabase_manager))