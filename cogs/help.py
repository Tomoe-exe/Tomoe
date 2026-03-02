import os
import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
from dotenv import load_dotenv

load_dotenv("bot.env")
GUILD_IDS_RAW = os.getenv("GUILD_IDS", "")
GUILD_IDS = [int(gid.strip()) for gid in GUILD_IDS_RAW.split(",") if gid.strip()]

COG_PATH = "cogs"

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.language_selection = {}  # user_id -> language ("en"/"de")

    def get_localized(self, key: str, lang: str) -> str:
        translations = {
            "choose_language": {
                "en": "Please select your language:",
                "de": "Bitte wähle deine Sprache aus:",
            },
            "folder_overview": {
                "en": "Available Categories",
                "de": "Verfügbare Kategorien",
            },
            "back": {
                "en": "⬅️ Back",
                "de": "⬅️ Zurück",
            },
            "no_commands": {
                "en": "No commands you can use in this category.",
                "de": "Keine Befehle, die du in dieser Kategorie verwenden kannst.",
            },
        }
        return translations.get(key, {}).get(lang, key)

    def get_cog_folders(self):
        folders = []
        for entry in os.scandir(COG_PATH):
            if entry.is_dir():
                for root, _, files in os.walk(os.path.join(COG_PATH, entry.name)):
                    for file in files:
                        if file.endswith(".py") and not file.startswith("__"):
                            folders.append(entry.name)
                            break
        return folders

    async def get_visible_commands(self, interaction: discord.Interaction, folder: str):
        visible = []
        for cmd in self.bot.tree.walk_commands():
            if cmd.module and cmd.module.startswith(f"cogs.{folder}"):
                try:
                    if await cmd._check_can_run(interaction):
                        visible.append(cmd)
                except:
                    pass
        return visible

    class LanguageSelect(discord.ui.View):
        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog

        @discord.ui.button(label="English", style=discord.ButtonStyle.primary)
        async def english(self, interaction: discord.Interaction, button: discord.ui.Button):
            await self.cog.show_categories(interaction, lang="en")

        @discord.ui.button(label="Deutsch", style=discord.ButtonStyle.secondary)
        async def german(self, interaction: discord.Interaction, button: discord.ui.Button):
            await self.cog.show_categories(interaction, lang="de")

    async def send_language_prompt(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="❓ Help | Hilfe",
            description="🇺🇸 Please select your language:\n🇩🇪 Bitte wähle deine Sprache aus:",
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=embed, view=self.LanguageSelect(self), ephemeral=True)

    async def show_categories(self, interaction: discord.Interaction, lang: Literal["en", "de"]):
        folders = []
        for folder in self.get_cog_folders():
            commands = await self.get_visible_commands(interaction, folder)
            if commands:
                folders.append((folder, commands))

        embed = discord.Embed(
            title=f"📂 {self.get_localized('folder_overview', lang)}",
            description="\n".join(f"📁 `{folder}`" for folder, _ in folders),
            color=discord.Color.green()
        )

        view = discord.ui.View(timeout=None)

        for folder, commands in folders:
            async def folder_callback(inter: discord.Interaction, f=folder, cmds=commands):
                await self.show_commands(inter, f, cmds, lang)
            button = discord.ui.Button(label=folder, style=discord.ButtonStyle.blurple)
            button.callback = folder_callback
            view.add_item(button)

        async def back_callback(inter: discord.Interaction):
            await self.send_language_prompt(inter)

        back_button = discord.ui.Button(label=self.get_localized("back", lang), style=discord.ButtonStyle.gray)
        back_button.callback = back_callback
        view.add_item(back_button)

        await interaction.response.edit_message(embed=embed, view=view)

    async def show_commands(self, interaction: discord.Interaction, folder: str, commands, lang: str):
        if not commands:
            embed = discord.Embed(
                title=f"📁 {folder}",
                description=self.get_localized("no_commands", lang),
                color=discord.Color.red()
            )
        else:
            embed = discord.Embed(
                title=f"📁 {folder}",
                description="\n".join(f"• `/{cmd.name}` – {cmd.description}" for cmd in commands),
                color=discord.Color.blurple()
            )

        view = discord.ui.View(timeout=None)

        async def back_callback(inter: discord.Interaction):
            await self.show_categories(inter, lang)

        back_button = discord.ui.Button(label=self.get_localized("back", lang), style=discord.ButtonStyle.gray)
        back_button.callback = back_callback
        view.add_item(back_button)

        await interaction.response.edit_message(embed=embed, view=view)

    @app_commands.guilds(*[discord.Object(id=gid) for gid in GUILD_IDS])
    @app_commands.command(name="help", description="Shows help menu")
    async def help(self, interaction: discord.Interaction):
        await self.send_language_prompt(interaction)

async def setup(bot):
    await bot.add_cog(Help(bot))
