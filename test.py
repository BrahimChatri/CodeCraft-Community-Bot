import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
import os, json
from dotenv import load_dotenv
from discord.ext import tasks
import asyncio
from datetime import datetime, timedelta, timezone

# Define the bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
load_dotenv()

TOKEN = os.getenv("TEST_TOKEN")
POLL_DATA_FILE = "polls.json"

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    synced = await bot.tree.sync()
    print(f"synced {len(synced)} commands")
    try:
        # Removed the logic for checking and processing expired polls after restart

        activity = discord.Activity(type=discord.ActivityType.watching, name="CodeCraft community")
        await bot.change_presence(activity=activity)

    except Exception as e:
        print(f"Error during on_ready: {e}")


# Load existing polls from file
def load_polls():
    if os.path.exists(POLL_DATA_FILE):
        with open(POLL_DATA_FILE, "r") as file:
            return json.load(file)
    return {}


# Save polls to file
def save_polls(polls):
    with open(POLL_DATA_FILE, "w") as file:
        json.dump(polls, file, indent=4)


# Initialize polls
polls = load_polls()


# Create the slash command for the poll with customizable options and duration
@bot.tree.command(name="vote", description="Start a voting poll with results and duration!")
@app_commands.describe(question="The question for the poll", options="Comma-separated list of options ex: yes, no, maybe ....", duration="Duration in seconds for the poll")
async def vote(interaction: discord.Interaction, question: str, options: str, duration: int):
    options_list = options.split(",")
    guild = bot.get_guild(interaction.guild_id)
    icon_url = guild.icon.url if guild else None

    if len(options_list) < 2:
        await interaction.response.send_message("Please provide at least two options for the poll!", ephemeral=True)
        return
    end_time_utc = datetime.now(timezone.utc) + timedelta(seconds=duration)  # Poll ends in UTC
    unix_timestamp_utc = int(end_time_utc.timestamp())  # Convert to UNIX timestamp for Discord
    vote_counts = {i: 0 for i in range(len(options_list))}
    polls[str(interaction.id)] = {
        "question": question,
        "options": options_list,
        "vote_counts": vote_counts,
        "duration": duration,
        "channel_id": interaction.channel_id,
        "message_id": None,
        "end_time": unix_timestamp_utc,  # Store the end time for reference
        "guild_name": interaction.guild.name  # Ensure guild name is saved here
    }

    save_polls(polls)

    embed = discord.Embed(
        title="Voting pool",
        description=question,
        color=discord.Color.random()
    )
    embed.add_field(name="Options", value="React with the buttons Below to Vote!", inline=False)
    embed.add_field(name="Poll Ends", value=f"<t:{unix_timestamp_utc}:R>", inline=False)  # Relative time

    embed.set_footer(text=f"{interaction.guild.name}")
    if icon_url:
        embed.set_thumbnail(url=icon_url)

    vote_buttons = View(timeout=None)
    for i, option in enumerate(options_list, start=1):
        button = Button(label=f"{option.strip()}", style=discord.ButtonStyle.success, custom_id=f"{interaction.id}_vote_{i}")
        vote_buttons.add_item(button)

    await interaction.response.send_message(embed=embed, view=vote_buttons)
    message = await interaction.original_response()

    # Update poll data with message ID
    polls[str(interaction.id)]["message_id"] = message.id
    save_polls(polls)

    @tasks.loop(seconds=10)
    async def poll_timer():
        await asyncio.sleep(duration)  # Use asyncio.sleep instead of blocking sleep
        poll_data = polls.pop(str(interaction.id), None)
        save_polls(polls)
        if poll_data:
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

    poll_timer.start()


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


# Run the bot
bot.run(TOKEN)
