from discord import app_commands
import discord
from discord.ext import commands, tasks
from discord.ui import  Button, View
import random
import asyncio
import os, json
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone 


bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())
load_dotenv()
TOKEN = os.getenv("TOKEN") # Main Bot Token
#TOKEN= os.getenv("TEST_TOKEN") # Test Bot Token
POLL_DATA_FILE = "polls.json"
TARGET_CHANNEL_ID = 1328815353651925142 # to change its name to members count



@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    try:
        synced = await bot.tree.sync()
        print(f"synced {len(synced)} commands")
        bot.loop.create_task(update_member_count())
        activity = discord.Activity(type=discord.ActivityType.watching, name="CodeCraft community")
        await bot.change_presence(activity=activity)

    except Exception as e:
        print(e)


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

class EmbedModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title='Create an Embed')
        self.title_input = discord.ui.TextInput(label='Title', required=True)
        self.description_input = discord.ui.TextInput(label='Description', style=discord.TextStyle.paragraph, required=True)
        self.image_url_input = discord.ui.TextInput(label='Image URL', required=False)
        self.thumbnail = discord.ui.TextInput(label='"yes" To set server icon as Thumbnail', required=False)
        self.fields_input = discord.ui.TextInput(label='Fields (name:value,...)', style=discord.TextStyle.paragraph, required=False)

        self.add_item(self.title_input)
        self.add_item(self.description_input)
        self.add_item(self.thumbnail)
        self.add_item(self.image_url_input)
        self.add_item(self.fields_input)

    async def on_submit(self, interaction: discord.Interaction):
        # Create the embed
        embed = discord.Embed(
            title=self.title_input.value,
            description=self.description_input.value,
            color=discord.Color.dark_gold()
        )
        if self.thumbnail.value.lower() == "yes" :
            embed.set_thumbnail(url=interaction.guild.icon.url)
        embed.set_footer(text="CodeCraft Community",icon_url=interaction.guild.icon.url)

        if self.image_url_input.value:
            embed.set_image(url=self.image_url_input.value)

        if self.fields_input.value:
            field_pairs = self.fields_input.value.split(',')
            for pair in field_pairs:
                name, value = pair.split(':', 1)
                embed.add_field(name=name.strip(), value=value.strip(), inline=False)

        # Send the embed
        await interaction.response.send_message(embed=embed)

        

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


@bot.tree.command(name="help", description="Get some help!")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Help",
        description="Here is how to enteract with the bot : ",
        color=discord.Color.dark_gold()
    )
    embed.add_field(name="`/guess`",value="To play the guessing game", inline=False)
    embed.add_field(name="`python_hangman`",value="Play a Python-themed Hangman game", inline=False)
    embed.add_field(name="`/cardgame`",value="To play Card Guessing Game", inline=False)
    embed.add_field(name="`/fact`",value="To see cool fact about programming", inline=False)
    embed.add_field(name="`/joke`",value="To see a cool joke about programming", inline=False)
    embed.add_field(name="`/vote`",value="Start a voting poll with results and duration!", inline=False)
    embed.add_field(name="`send_embed`",value="To send an embed (for administrators only )", inline=False)
    embed.add_field(name="`help`",value="To show this message)", inline=False)
    embed.set_thumbnail(url=interaction.guild.icon.url)
    embed.set_footer(text=interaction.guild.name ,icon_url=interaction.guild.icon.url)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="send_embed", description="Send a customized embed message")
async def send_embed(interaction: discord.Interaction):
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return # Exit the command

    await interaction.response.send_modal(EmbedModal())

@bot.tree.command(name="guess", description="Play the Number Guessing Game")
async def play_guess(interaction: discord.Interaction):
    await interaction.response.send_message(f"Welcome to the Number Guessing Game, {interaction.user.mention}! Guess a number between 0 and 50.")

    secret_number = random.randint(0, 50)
    attempts = 0

    while attempts < 5:
        try:
            user_guess_payload = await bot.wait_for("message", check=lambda m: m.author == interaction.user, timeout=30.0)
            user_guess = int(user_guess_payload.content)

            attempts += 1

            if user_guess == secret_number:
                await interaction.followup.send(f"{interaction.user.mention} Congratulations! You guessed the correct number {secret_number} in {attempts} attempts.")
                return
            elif user_guess < secret_number:
                await interaction.followup.send("Too low! Try again.")
            else:
                await interaction.followup.send("Too high! Try again.")

        except ValueError:
            await interaction.followup.send("Invalid input. Please enter a valid number.")

    await interaction.followup.send(f"You reached the maximum number of attempts! The correct number was {secret_number}.")

@bot.tree.command(name="python_hangman", description="Play a Python-themed Hangman game")
async def play_python_hangman(interaction: discord.Interaction):
    words: list[str] = [
    "python", "flask", "django", "variable", "function", "exception",
    "loop", "list", "tuple", "dictionary", "module", "package", "class",
    "inheritance", "decorator", "generator", "debugging", "syntax", "object",
    "parameter", "argument", "algorithm", "binary", "boolean", "immutable",
    "mutable", "expression", "statement", "pip", "request", "json",
    "regex", "html", "css", "docker", "git", "branch", "commit",
    "api", "rest", "oauth", "sqlite", "nosql", "redis", "queue",
    "stack", "lambda", "closure", "testcase", "unittest", "mock",
    "ci", "cloud"
    ]
    chosen_word = random.choice(words).lower()
    guessed_word = ["_"] * len(chosen_word)
    incorrect_guesses = 0
    max_attempts = 6
    guessed_letters = set()

    def display_word():
        return " ".join(guessed_word)

    await interaction.response.send_message(
        f"Welcome to **Python Hangman**, {interaction.user.mention}! 🐍\n"
        f"Try to guess the Python-related word letter by letter!\n"
        f"Word to guess: `{display_word()}`"
    )

    while incorrect_guesses < max_attempts and "_" in guessed_word:
        try:
            user_guess_payload = await bot.wait_for(
                "message",
                check=lambda m: m.author == interaction.user and m.content.isalpha() and len(m.content) == 1 and m.content.lower() not in guessed_letters,
                timeout=30.0
            )
            user_guess = user_guess_payload.content.lower()
            guessed_letters.add(user_guess)

            if user_guess in chosen_word:
                for i, letter in enumerate(chosen_word):
                    if letter == user_guess:
                        guessed_word[i] = user_guess
                await interaction.followup.send(f"✅ Correct! `{display_word()}`")
            else:
                incorrect_guesses += 1
                await interaction.followup.send(
                    f"❌ Wrong guess! Attempts left: {max_attempts - incorrect_guesses}\n"
                    f"`{display_word()}`"
                )

        except asyncio.TimeoutError:
            await interaction.followup.send(
                "⏱️ Time's up! The game has ended. Better luck next time!"
            )
            return

    if "_" not in guessed_word:
        await interaction.followup.send(
            f"🎉 Congratulations, {interaction.user.mention}! You guessed the Python word: `{chosen_word}`"
        )
    else:
        await interaction.followup.send(
            f"😞 Sorry, you ran out of attempts. The correct word was: `{chosen_word}`"
        )


@bot.tree.command(name="cardgame", description="Play the Card Guessing Game")
async def play_card_game(interaction: discord.Interaction):
    suits = ["Hearts", "Diamonds", "Clubs", "Spades"]
    ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "Jack", "Queen", "King", "Ace"]

    chosen_suit = random.choice(suits)
    chosen_rank = random.choice(ranks)

    await interaction.response.send_message(f"Welcome to the Card Guessing Game, {interaction.user.mention}! Try to guess the suit and rank of the card.")

    attempts = 0

    while attempts < 3:
        try:
            user_suit_payload = await bot.wait_for("message", check=lambda m: m.author == interaction.user, timeout=30.0)
            user_suit = user_suit_payload.content.capitalize()

            user_rank_payload = await bot.wait_for("message", check=lambda m: m.author == interaction.user, timeout=30.0)
            user_rank = user_rank_payload.content.capitalize()

            attempts += 1

            if user_suit == chosen_suit and user_rank == chosen_rank:
                await interaction.followup.send(f"{interaction.user.mention} Congratulations! You guessed the correct card ({chosen_rank} of {chosen_suit}) in {attempts} attempts.")
                return
            else:
                await interaction.followup.send(f"Wrong guess! Attempts left: {3 - attempts}. Try again.")

        except asyncio.TimeoutError:
            await interaction.followup.send("Time's up! The game has ended.")
            return

    await interaction.followup.send(f"You reached the maximum number of attempts! The correct card was {chosen_rank} of {chosen_suit}.")

@bot.tree.command(name="joke", description="Get a random joke about programming")
async def get_joke(interaction: discord.Interaction) -> None:
    jokes = [
    "Why do programmers prefer dark mode? Because light attracts bugs!",
    "How many programmers does it take to change a light bulb? None. That's a hardware problem.",
    "Why do Java developers wear glasses? Because they can't C#.",
    "Why was the JavaScript developer sad? Because he didn’t know how to ‘null’ his feelings.",
    "What’s a programmer’s favorite hangout place? The Foo Bar.",
    "Why was the developer broke? Because he used up all his cache.",
    "Why do programmers hate nature? It has too many bugs.",
    "Why did the programmer quit his job? He didn't get arrays.",
    "What do you call 8 hobbits? A hobbyte.",
    "Why do Python programmers prefer using 'hex()'? Because they can C in it.",
    "How do functions break up? They stop calling each other!",
    "Why was the developer afraid of the database? Too many foreign keys.",
    "Why do programmers confuse Halloween and Christmas? Because Oct 31 == Dec 25.",
    "Why did the coder take a break? Because they needed to debug their life.",
    "What do you get when you cross a computer with an elephant? Lots of memory.",
    "Why do programmers love coffee? Because it's their source code.",
    "How does a computer get drunk? It takes screenshots.",
    "Why don’t programmers like to code in the forest? Too many trees.",
    "How do you comfort a JavaScript bug? You console it.",
    "What’s a programmer’s favorite type of music? Algo-rhythms.",
    "Why did the software developer go broke? He lost his domain in a crash.",
    "Why don’t programmers trust numbers? They start at zero.",
    "Why was the coder always calm? They knew how to handle exceptions.",
    "What’s a programmer’s favorite exercise? Loops.",
    "Why was the array always so confident? It knew it had all the elements.",
    "What do you call a programmer from Finland? Nerdic.",
    "Why did the database administrator break up with their partner? They couldn't establish a connection.",
    "Why was the computer cold? It left its Windows open.",
    "Why did the JavaScript function break up? It had too many callbacks.",
    "Why do programmers prefer dogs over cats? Dogs are loyal, but cats act like they don’t exist until called."
    ]


    random_joke = random.choice(jokes)

    embed = discord.Embed(
        title="🌟 Random Joke",
        description=f"**{random_joke}**",
        color=discord.Color.blurple()  # You can customize the color
    )

    # Send the embed
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="fact", description="get some cool facts about programming")
async def get_random_fact(interaction: discord.Interaction):
    random_facts = [
    "The first computer programmer was Ada Lovelace in the 1840s, even before computers existed as we know them.",
    "The first high-level programming language was Fortran, developed in 1957.",
    "Python is named after Monty Python, not the snake.",
    "The first computer bug was an actual moth found in a Harvard Mark II computer in 1947.",
    "The term 'debugging' was popularized by Grace Hopper, inspired by the incident with the moth.",
    "JavaScript was created in just 10 days by Brendan Eich in 1995.",
    "There are over 700 programming languages in existence today.",
    "The world's first website is still online. It was created by Tim Berners-Lee in 1991.",
    "The programming language 'C' was developed in 1972 by Dennis Ritchie at Bell Labs.",
    "The '@' symbol in email addresses was chosen by Ray Tomlinson in 1971.",
    "Linux, one of the most popular open-source operating systems, was created by Linus Torvalds in 1991.",
    "HTML is not a programming language; it’s a markup language.",
    "COBOL, a language developed in 1959, is still used by many banks and businesses today.",
    "The first video game, 'Pong,' was programmed in 1972.",
    "Git, a version control system, was created by Linus Torvalds in 2005.",
    "Over 70% of developers use JavaScript, making it the most popular language in the world.",
    "The first mobile app was a simple calculator, released in 1994 on the IBM Simon Personal Communicator.",
    "PHP originally stood for 'Personal Home Page' but now stands for 'PHP: Hypertext Preprocessor.'",
    "The longest codebase in the world belongs to Google, with over 2 billion lines of code.",
    "The average salary for a software developer varies widely, but top developers often earn six figures annually.",
    "The first search engine was called 'Archie,' created in 1990.",
    "The Turing Test, created by Alan Turing, determines if a machine exhibits human-like intelligence.",
    "Java and JavaScript are not the same; they’re completely different programming languages.",
    "The 'Hello, World!' program is often the first program written by people learning a new language.",
    "Stack Overflow is the most visited site by programmers, second only to Google.",
    "The average software developer writes about 10–20 lines of production code per day.",
    "Hackers once took control of a Jeep Cherokee via its infotainment system in 2015, highlighting the importance of secure code.",
    "The most common password in the world is still '123456.'",
    "GitHub was acquired by Microsoft in 2018 for $7.5 billion.",
    "The most expensive software ever built is the US Department of Defense's F-35 fighter jet software."
    ]


    random_fact = random.choice(random_facts)

    embed = discord.Embed(
        title="🌟 Random Fact",
        description=f"**{random_fact}**",
        color=discord.Color.blurple()  # You can customize the color
    )

    
    await interaction.response.send_message(embed=embed)

bot.run(TOKEN)