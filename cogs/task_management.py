from __future__ import annotations
import discord
from discord.ext import commands
from discord import app_commands
from typing import TYPE_CHECKING
from datetime import datetime
import uuid # Used for generating unique task IDs

if TYPE_CHECKING:
    from main import MyBot
    from utils.supabase_manager import SupabaseManager
    # Assuming utils/helpers.py exists and has generate_unique_id
    # from utils.helpers import generate_unique_id

# Placeholder for generate_unique_id if not explicitly imported from utils.helpers
# In a real scenario, this would be imported or defined in helpers.py
def generate_unique_id() -> str:
    """Generates a unique ID for tasks. Using a short hex string for readability."""
    return uuid.uuid4().hex[:8] # Shorten for readability, or use full hex

class TaskManagementCog(commands.Cog):
    def __init__(self, bot: MyBot):
        self.bot = bot
        self.supabase: SupabaseManager = bot.supabase

    async def _get_task_embed(self, task: dict, title_prefix: str = "") -> discord.Embed:
        """Helper to create a consistent task embed for displaying task details."""
        embed = discord.Embed(
            title=f"{title_prefix}タスク: {task.get('title', 'N/A')}",
            description=task.get('description', '説明なし'),
            color=discord.Color.blue()
        )
        embed.add_field(name="ID", value=task.get('task_id', 'N/A'), inline=True)
        embed.add_field(name="ステータス", value=task.get('status', 'N/A'), inline=True)
        embed.add_field(name="期限", value=task.get('due_date', '設定なし'), inline=True)
        
        created_by_id = task.get('created_by')
        if created_by_id:
            try:
                user = await self.bot.fetch_user(int(created_by_id))
                embed.add_field(name="作成者", value=user.mention, inline=True)
            except discord.NotFound:
                embed.add_field(name="作成者", value=f"不明なユーザー (ID: {created_by_id})", inline=True)
            except Exception:
                embed.add_field(name="作成者", value=f"エラー (ID: {created_by_id})", inline=True)
        else:
            embed.add_field(name="作成者", value="不明", inline=True)

        created_at = task.get('created_at')
        if created_at:
            try:
                # Parse ISO format string to datetime object for better display
                dt_object = datetime.fromisoformat(created_at)
                embed.add_field(name="作成日時", value=dt_object.strftime("%Y-%m-%d %H:%M UTC"), inline=True)
            except ValueError:
                embed.add_field(name="作成日時", value=created_at, inline=True) # Fallback if format is unexpected
        
        embed.set_footer(text="タスク管理ボット")
        return embed

    @app_commands.command(name="task_add", description="新しいタスクを作成します。")
    @app_commands.describe(
        title="タスクのタイトル (例: 買い物リストの作成)",
        description="タスクの詳細な説明 (例: 牛乳、パン、卵を購入する)",
        due_date="タスクの期限 (例: 2023-12-31)"
    )
    async def task_add(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str | None = None,
        due_date: str | None = None
    ):
        """新しいタスクを作成し、Supabaseに保存します。"""
        # Defer the response as Supabase operations can take time, making the bot appear responsive.
        await interaction.response.defer(ephemeral=True)

        # 1. Validate the input, especially the due_date format.
        parsed_due_date = None
        if due_date:
            try:
                # Attempt to parse the date in YYYY-MM-DD format
                parsed_due_date = datetime.strptime(due_date, "%Y-%m-%d").date()
            except ValueError:
                await interaction.followup.send(
                    "⚠️ 無効な日付形式です。期限は `YYYY-MM-DD` 形式で入力してください。",
                    ephemeral=True
                )
                return

        # 2. Generate a unique task ID.
        task_id = generate_unique_id() # Using the assumed helper or fallback uuid

        # 3. Store the new task in the Supabase database.
        try:
            task_data = {
                "task_id": task_id,
                "guild_id": str(interaction.guild_id), # Store guild ID for guild-specific tasks
                "title": title,
                "description": description,
                "due_date": parsed_due_date.isoformat() if parsed_due_date else None, # Store as ISO format string
                "created_by": str(interaction.user.id),
                "created_at": datetime.utcnow().isoformat(), # Store creation time in UTC ISO format
                "status": "pending"
            }
            
            # Insert task into Supabase via the SupabaseManager
            await self.supabase.insert_task(task_data)

            # 4. Respond with an embed confirming the task creation.
            embed = await self._get_task_embed(task_data, title_prefix="✅ 新しいタスクを作成しました")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            # 5. Handle potential errors during Supabase insertion and provide user-friendly feedback.
            self.bot.logger.error(f"Failed to add task to Supabase: {e}")
            await interaction.followup.send(
                "❌ タスクの作成中にエラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )

    @app_commands.command(name="task_list", description="タスクの一覧をEmbed形式で表示します。")
    async def task_list(
        self,
        interaction: discord.Interaction
    ):
        """現在のサーバーの保留中のタスク一覧をEmbed形式で表示します。"""
        # Defer, visible to everyone, as this command displays public information.
        await interaction.response.defer(ephemeral=False)

        try:
            # Retrieve 'pending' tasks for the current guild from Supabase.
            tasks = await self.supabase.fetch_tasks(str(interaction.guild_id), status="pending")

            if not tasks:
                await interaction.followup.send("ℹ️ 現在、保留中のタスクはありません。", ephemeral=True)
                return

            # Format the retrieved tasks into a Discord Embed.
            embed = discord.Embed(
                title="📋 保留中のタスク一覧",
                description="現在のサーバーの保留中のタスクです。",
                color=discord.Color.green()
            )

            # Add tasks to the embed, displaying key details.
            for task in tasks:
                title = task.get('title', 'タイトルなし')
                task_id = task.get('task_id', 'N/A')
                due_date = task.get('due_date', '設定なし')
                status = task.get('status', 'N/A')
                
                # Truncate title if too long for embed field name limit (256 characters)
                field_name = f"[{task_id}] {title}"
                if len(field_name) > 256:
                    field_name = field_name[:253] + "..."

                embed.add_field(
                    name=field_name,
                    value=f"期限: {due_date} | ステータス: {status}",
                    inline=False
                )
            
            embed.set_footer(text="詳細を見るには /task_detail <ID>")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            self.bot.logger.error(f"Failed to fetch task list from Supabase: {e}")
            await interaction.followup.send(
                "❌ タスクリストの取得中にエラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )

    @app_commands.command(name="task_detail", description="指定したタスクの詳細情報を表示します。")
    @app_commands.describe(
        task_id="詳細を表示するタスクのID"
    )
    async def task_detail(
        self,
        interaction: discord.Interaction,
        task_id: str
    ):
        """指定されたタスクIDの詳細情報をEmbed形式で表示します。"""
        await interaction.response.defer(ephemeral=True)

        try:
            # Retrieve the specific task from Supabase using its ID and guild ID.
            task = await self.supabase.fetch_task_by_id(task_id, str(interaction.guild_id))

            if not task:
                await interaction.followup.send(
                    f"⚠️ タスクID `{task_id}` のタスクは見つかりませんでした。",
                    ephemeral=True
                )
                return

            # Format its detailed information into a Discord Embed using the helper.
            embed = await self._get_task_embed(task, title_prefix="🔍 タスク詳細")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            self.bot.logger.error(f"Failed to fetch task detail from Supabase for ID {task_id}: {e}")
            await interaction.followup.send(
                "❌ タスク詳細の取得中にエラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )

    @app_commands.command(name="task_done", description="指定したタスクを完了ステータスにします。")
    @app_commands.describe(
        task_id="完了するタスクのID"
    )
    async def task_done(
        self,
        interaction: discord.Interaction,
        task_id: str
    ):
        """指定されたタスクを「完了」ステータスに更新します。"""
        await interaction.response.defer(ephemeral=True)

        try:
            # Retrieve the task from Supabase to check its existence and current status.
            task = await self.supabase.fetch_task_by_id(task_id, str(interaction.guild_id))

            if not task:
                await interaction.followup.send(
                    f"⚠️ タスクID `{task_id}` のタスクは見つかりませんでした。",
                    ephemeral=True
                )
                return
            
            # Prevent marking an already done task as done again.
            if task.get('status') == 'done':
                await interaction.followup.send(
                    f"ℹ️ タスクID `{task_id}` は既に完了済みです。",
                    ephemeral=True
                )
                return

            # Update its 'status' field to 'done' in Supabase.
            updated_task = await self.supabase.update_task(
                task_id,
                str(interaction.guild_id),
                {"status": "done"}
            )

            if updated_task:
                # Respond with an embed confirming the task has been marked as done.
                embed = await self._get_task_embed(updated_task, title_prefix="✅ タスクを完了しました")
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(
                    "❌ タスクの更新に失敗しました。もう一度お試しください。",
                    ephemeral=True
                )

        except Exception as e:
            self.bot.logger.error(f"Failed to mark task {task_id} as done in Supabase: {e}")
            await interaction.followup.send(
                "❌ タスクの完了中にエラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )

    @app_commands.command(name="task_edit", description="指定したタスクの情報を更新します。")
    @app_commands.describe(
        task_id="更新するタスクのID",
        title="新しいタスクのタイトル (変更しない場合は空欄)",
        description="新しいタスクの詳細な説明 (変更しない場合は空欄)",
        due_date="新しいタスクの期限 (変更しない場合は空欄)"
    )
    async def task_edit(
        self,
        interaction: discord.Interaction,
        task_id: str,
        title: str | None = None,
        description: str | None = None,
        due_date: str | None = None
    ):
        """指定されたタスクのタイトル、説明、期限を更新します。"""
        await interaction.response.defer(ephemeral=True)

        try:
            # Retrieve the specific task from Supabase to ensure it exists.
            task = await self.supabase.fetch_task_by_id(task_id, str(interaction.guild_id))

            if not task:
                await interaction.followup.send(
                    f"⚠️ タスクID `{task_id}` のタスクは見つかりませんでした。",
                    ephemeral=True
                )
                return

            update_data = {}
            if title: # Only update if title is provided and not empty
                update_data["title"] = title
            if description is not None: # Allow setting description to empty string to clear it
                update_data["description"] = description
            
            if due_date is not None: # Check if due_date argument was provided at all
                if due_date == "": # User explicitly passed an empty string to clear due_date
                    update_data["due_date"] = None
                else: # User provided a date string, attempt to parse it
                    try:
                        parsed_due_date = datetime.strptime(due_date, "%Y-%m-%d").date()
                        update_data["due_date"] = parsed_due_date.isoformat()
                    except ValueError:
                        await interaction.followup.send(
                            "⚠️ 無効な日付形式です。期限は `YYYY-MM-DD` 形式で入力してください。",
                            ephemeral=True
                        )
                        return

            if not update_data:
                await interaction.followup.send(
                    "ℹ️ 更新する情報が提供されていません。",
                    ephemeral=True
                )
                return

            # Update the task in Supabase with the provided data.
            updated_task = await self.supabase.update_task(
                task_id,
                str(interaction.guild_id),
                update_data
            )

            if updated_task:
                # Respond with an embed confirming the task update.
                embed = await self._get_task_embed(updated_task, title_prefix="📝 タスクを更新しました")
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(
                    "❌ タスクの更新に失敗しました。もう一度お試しください。",
                    ephemeral=True
                )

        except Exception as e:
            self.bot.logger.error(f"Failed to edit task {task_id} in Supabase: {e}")
            await interaction.followup.send(
                "❌ タスクの編集中にエラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )

    @app_commands.command(name="task_delete", description="指定したタスクを削除します。")
    @app_commands.describe(
        task_id="削除するタスクのID"
    )
    async def task_delete(
        self,
        interaction: discord.Interaction,
        task_id: str
    ):
        """指定されたタスクを「削除済み」ステータスに更新します（ソフトデリート）。"""
        await interaction.response.defer(ephemeral=True)

        try:
            # Retrieve the specific task from Supabase to check its existence and current status.
            task = await self.supabase.fetch_task_by_id(task_id, str(interaction.guild_id))

            if not task:
                await interaction.followup.send(
                    f"⚠️ タスクID `{task_id}` のタスクは見つかりませんでした。",
                    ephemeral=True
                )
                return
            
            # Prevent marking an already deleted task as deleted again.
            if task.get('status') == 'deleted':
                await interaction.followup.send(
                    f"ℹ️ タスクID `{task_id}` は既に削除済みです。",
                    ephemeral=True
                )
                return

            # Update its 'status' field to 'deleted' in Supabase (soft delete as per convention).
            updated_task = await self.supabase.update_task(
                task_id,
                str(interaction.guild_id),
                {"status": "deleted"}
            )

            if updated_task:
                # Respond with an embed confirming the task has been marked as deleted.
                embed = await self._get_task_embed(updated_task, title_prefix="🗑️ タスクを削除しました")
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(
                    "❌ タスクの削除に失敗しました。もう一度お試しください。",
                    ephemeral=True
                )

        except Exception as e:
            self.bot.logger.error(f"Failed to delete task {task_id} in Supabase: {e}")
            await interaction.followup.send(
                "❌ タスクの削除中にエラーが発生しました。もう一度お試しください。",
                ephemeral=True
            )

async def setup(bot: MyBot):
    await bot.add_cog(TaskManagementCog(bot))