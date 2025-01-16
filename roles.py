import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

load_dotenv()

alx_backend_role_id = int(os.getenv("alx_backend_role_id"))
alx_frontend_role_id = int(os.getenv("alx_frontend_role_id"))

class RoleButton(discord.ui.Button):
    def __init__(self, role_id: int, label: str, style: discord.ButtonStyle, custom_id: str):
        super().__init__(label=label, style=style, custom_id=custom_id)  # Add custom_id here
        self.role_id = role_id

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        role = guild.get_role(self.role_id)
        member = interaction.user

        if role in member.roles:
            await member.remove_roles(role)
            await interaction.response.send_message(f"Role **{role.name}** removed!", ephemeral=True)
        else:
            await member.add_roles(role)
            await interaction.response.send_message(f"Role **{role.name}** added!", ephemeral=True)

class ButtonsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # Set timeout to None for persistence
        # Add buttons with unique custom_ids
        self.add_item(RoleButton(role_id=alx_backend_role_id, label="Back-end", style=discord.ButtonStyle.success, custom_id="backend_button"))
        self.add_item(RoleButton(role_id=alx_frontend_role_id, label="Front-end", style=discord.ButtonStyle.success, custom_id="frontend_button"))

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    synced = await bot.tree.sync()
    print(f"Bot synced with {len(synced)}")

    # Re-add persistent views
    bot.add_view(ButtonsView())
    print("Persistent views have been added!")

@bot.tree.command(name="roles_embed", description="Send embed message to react for roles")
async def roles_embed(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    # Create embed
    embed = discord.Embed(
        title="React to get a role",
        description="Click on the buttons below to add roles.",
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"{interaction.guild.name}")

    # Send the embed with the view
    await interaction.response.send_message(embed=embed, view=ButtonsView())


__all__=["roles_embed", "ButtonsView"]
