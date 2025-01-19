import discord
from discord.ext import commands
import asyncio, os
from dotenv import load_dotenv
from organized.local_commands import roles_embed, ButtonsView, show_data, help 
from organized.local_commands import polls, save_polls, guess, fact, joke, python_hangman, send_embed, cardgame # import commands from commands.py


bot = commands.Bot(command_prefix="!" ,intents=discord.Intents.all())
load_dotenv()

#TOKEN = os.getenv("TOKEN") # Main Bot Token
TOKEN= os.getenv("TEST_TOKEN") # Test Bot Token
POLL_DATA_FILE = "polls.json"
TARGET_CHANNEL_ID: str | None = int(os.getenv("TARGET_CHANNEL_ID")) # to change its name to members count


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    try:
        synced = await bot.tree.sync()
        print(f"synced {len(synced)} commands")
        bot.loop.create_task(update_member_count())
        activity = discord.Activity(type=discord.ActivityType.watching, name="CodeCraft community")
        await bot.change_presence(activity=activity)
        bot.add_view(ButtonsView())

    except Exception as e:
        print(e)


async def update_member_count():
    await bot.wait_until_ready()
    while not bot.is_closed():
        for guild in bot.guilds:
            target_channel = guild.get_channel(TARGET_CHANNEL_ID)
            if target_channel and target_channel.type == discord.ChannelType.voice:
                total_members = len(guild.members)
                new_name = f"Members: {total_members}"
                await target_channel.edit(name=new_name)
        await asyncio.sleep(300)  # Wait for 5 minutes (300 seconds)


@bot.event
async def on_interaction(interaction: discord.Interaction):
    try:
        # Your interaction handling code here
        if "component_type" in interaction.data and interaction.data["component_type"] == 2:
            if "_vote_" in interaction.data.get("custom_id", ""):
                interaction_id, _, option_id = interaction.data["custom_id"].split("_")
                option_id = int(option_id) - 1
                user_id = str(interaction.user.id)

                if interaction_id in polls:
                    poll_data = polls[interaction_id]

                    # Check if user already voted
                    if "user_votes" not in poll_data:
                        poll_data["user_votes"] = {}

                    if user_id in poll_data["user_votes"]:
                        previous_vote = poll_data["user_votes"][user_id]
                        if previous_vote != option_id:
                            poll_data["vote_counts"][previous_vote] -= 1

                    # Add the new vote
                    poll_data["vote_counts"][option_id] += 1
                    poll_data["user_votes"][user_id] = option_id
                    save_polls(polls)

                    await interaction.response.send_message(
                        f"**Your vote has been updated to: __{poll_data['options'][option_id]}__**",
                        ephemeral=True,
                    )

    except Exception as e:
        print(f"Error handling interaction: {e}")
        # Log full stack trace
        import traceback
        traceback.print_exc()


async def send_poll_results(poll_data):
    total_votes = sum(poll_data["vote_counts"].values())
    results_embed = discord.Embed(
        title="Poll Results",
        description=poll_data["question"],
        color=discord.Color.green()
    )
    results_embed.set_footer(text=f"{poll_data.get('guild_name', 'Unknown Guild')}")  # Add fallback if missing

    for i, option in enumerate(poll_data["options"], start=1):
        votes = poll_data["vote_counts"][i - 1]
        percentage = (votes / total_votes * 100) if total_votes > 0 else 0
        results_embed.add_field(name=f"{i}. {option.strip()}", value=f"Votes: {votes} ({percentage:.2f}%)", inline=False)

    channel = bot.get_channel(poll_data["channel_id"])
    if channel:
        message = await channel.fetch_message(poll_data["message_id"])
        await message.edit(embed=results_embed, view=None)
        await channel.send("Poll has ended! Results are revealed.")

# Add commands to the bot
bot.tree.add_command(roles_embed)
bot.tree.add_command(guess)
bot.tree.add_command(python_hangman)
bot.tree.add_command(joke)
bot.tree.add_command(fact)
bot.tree.add_command(cardgame)
bot.tree.add_command(send_embed)
bot.tree.add_command(show_data)
bot.tree.add_command(help)

if __name__ == '__main__':
    bot.run(TOKEN)