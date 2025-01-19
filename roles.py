import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

load_dotenv()

DATA_FILE = "polls.json"
ALLOWED_USER_ID = 615903606914416660
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
            embed = discord.Embed(
                title=f"Role {role.name}",
                description=f" ❌ You have successfully removed the role **{role.name}**.",
                color=discord.Color.red()
            )
            embed.set_thumbnail(url=interaction.guild.icon.url)
            embed.set_footer(text=f"{interaction.guild.name}", icon_url=interaction.guild.icon.url)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await member.add_roles(role)
            embed = discord.Embed(
                title=f"Role {role.name}",
                description=f" ✅ You have successfully added the role **{role.name}**.",
                color=discord.Color.red()
            )
            embed.set_thumbnail(url=interaction.guild.icon.url)
            embed.set_footer(text=f"{interaction.guild.name}", icon_url=interaction.guild.icon.url)
            await interaction.response.send_message(embed=embed, ephemeral=True)

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

    embed = discord.Embed(
        title="React to get a role",
        description="Click on the buttons below to add roles.",
        color=discord.Color.brand_green()
    )
    embed.set_thumbnail(url=interaction.guild.icon.url)
    embed.set_footer(text=f"{interaction.guild.name}", icon_url=interaction.guild.icon.url)

    # Send the embed with the view
    await interaction.response.send_message(embed=embed, view=ButtonsView())

@bot.tree.command(name="file", description="This command is restricted to the Owner !!")  
async def show_data(interaction: discord.Interaction):
    guild = interaction.guild
    member = guild.get_member(interaction.user.id)
    
    # Check if the user is allowed to use this command
    if member and member.id == ALLOWED_USER_ID:
        try:
            # Defer the response to handle delays
            await interaction.response.defer(ephemeral=True)
            
            # Open and send the file
            with open(DATA_FILE, 'rb') as file:
                await interaction.followup.send(
                    content="**__Here is your file:__**",
                    file=discord.File(file)
                )
        except FileNotFoundError:
            await interaction.followup.send(
                content="An error occurred: File not found.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                content=f"An error occurred: {str(e)}",
                ephemeral=True
            )
    else:
        await interaction.response.send_message(
            content="You don't have permission to use this command. Only the Owner can use it.",
            ephemeral=True
        )

__all__=["roles_embed", "ButtonsView"]
