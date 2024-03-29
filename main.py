import time
import discord
import dotenv
from discord.ext import commands
import os
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import json
import requests
import re

JS_ADD_TEXT_TO_INPUT = """
  var elm = arguments[0], txt = arguments[1];
  elm.value += txt;
  elm.dispatchEvent(new Event('change'));
  """

dotenv.load_dotenv()

# Function to read CHARACTER_NAME from JSON file
def get_character_name():
    with open('config.json') as json_file:
        data = json.load(json_file)
        return data['CHARACTER_NAME']

# Function to update CHARACTER_NAME in JSON file
def update_character_name(new_name):
    with open('config.json', 'r+') as json_file:
        data = json.load(json_file)
        data['CHARACTER_NAME'] = new_name
        json_file.seek(0)
        json.dump(data, json_file, indent=4)
        json_file.truncate()

CHARACTER_NAME = get_character_name()

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='?', description="""🌟 Bridging the gap between SillyTavern and Discord! 🌟
Contribute here: https://github.com/Bobini1/SillyTavernDiscordBot""", intents=intents)

print("BOT NAME: " + CHARACTER_NAME)

s = webdriver.Chrome()
s.maximize_window()
s.get("http://127.0.0.1:8000")
time.sleep(1)

def connect_api():
    api_connections = s.find_element(By.XPATH, "//div[@title='API Connections']")
    api_connections.click()
    time.sleep(1)
    connect_button = s.find_element(By.ID, "api_button_textgenerationwebui")
    connect_button.click()

connect_api()

def select_character():
    # find div with title Character Management
    character_management = s.find_element(By.XPATH, "//div[@title='Character Management']")
    character_management.click()
    time.sleep(1)
    #find div with title Select/Create Characters
    characters = s.find_element(By.XPATH, "//div[@title='Select/Create Characters']")
    characters.click()
    time.sleep(1)
    # find elements with class name "character_select"
    characters = s.find_elements(By.CLASS_NAME, "character_select")
    print("LOADED BOTS:")
    # pick the one where there exists a span with ch_name = CHARACTER_NAME
    for character in characters[:-1]:
        ch_name = character.find_element(By.CLASS_NAME, "ch_name").text
        print("-- " + ch_name)
        if ch_name == CHARACTER_NAME:
            character.click()
    print()
    # close the drawer
    character_management = s.find_element(By.XPATH, "//div[@title='Character Management']")
    character_management.click()

select_character()

# find the input field, id send_textarea
input_field = s.find_element(By.ID, "send_textarea")

def markdown_handling(text):
    # Replace <em> tags with asterisks
    text = re.sub(r'<em>(.*?)</em>', r'*\1*', text)
    # Replace <strong> tags with double asterisks
    text = re.sub(r'<strong>(.*?)</strong>', r'**\1**', text)
    # Add two asterisks to the right of any word wrapped with three asterisks on each side
    text = re.sub(r'\*{3}(\w+)\*{3}', r'***\1*', text)
    # Remove <q> tags
    text = re.sub(r'<q>(.*?)</q>', r'\1', text)
    return text

def send(user_message, edit=False):
    # find the mesid of element with class last_mes
    mesid = int(s.find_elements(By.CLASS_NAME, "last_mes")[-1].get_attribute("mesid"))
    s.execute_script(JS_ADD_TEXT_TO_INPUT, input_field, user_message)
    input_field.send_keys("\n", Keys.ENTER)
    message_to_send = mesid if edit else mesid + 2
    # wait until mesid of last_mes is mesid+2
    WebDriverWait(s, 120).until(lambda s: int(s.find_element(By.CLASS_NAME, "last_mes").get_attribute("mesid")) == message_to_send)
    # find div with class last_mes
    last_message = s.find_elements(By.CLASS_NAME, "last_mes")[-1]
    notif_div = last_message.find_element(By.CLASS_NAME, "swipe_right")
    # wait until its style becomes display: flex
    WebDriverWait(s, 120).until(lambda s: notif_div.value_of_css_property("display") == "flex")
    # find a <p> inside it
    paragraphs = last_message.find_elements(By.TAG_NAME, "p") 
    response = "\n\n".join([markdown_handling(p.get_attribute("innerHTML")) for p in paragraphs])
    return response

async def get_avatar():
    # Sanitize input and find the image element on the webpage using XPath
    image_element = s.find_element(By.XPATH, f'//img[starts-with(@src, "/thumbnail?type=avatar&file=")]')
    # Get the source (URL) of the image
    image_url = image_element.get_attribute("src")
    # Get the directory of the script
    script_directory = os.path.dirname(os.path.abspath(__file__))
    # Create the path for saving the image
    image_filename = os.path.basename(image_url)
    save_path = os.path.join(script_directory, 'thumbnail.png')
    # Download the image
    with open(save_path, "wb") as f:
        f.write(requests.get(image_url).content)
    # Get filepath
    current_dir = os.path.dirname(os.path.abspath(__file__))
    avatar_path = os.path.join(current_dir, 'thumbnail.png')
    try:
        # Open and read the image file
        with open(avatar_path, 'rb') as f:
            avatar_image = f.read()
        # Change the bot's avatar
        await bot.user.edit(avatar=avatar_image)
        os.remove(avatar_path)
    except FileNotFoundError:
        print("File 'thumbnail.png' not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

sent_messages = {}
emojis = ["⏩", "🔁"]

@bot.event
async def on_message(message):
    await bot.process_commands(message)  
    # Ignore messages sent by the bot
    if message.author == bot.user:
        return
    # Check if the message is a reply to a message sent by the bot
    if message.reference and message.reference.message_id in sent_messages:
        original_message = await message.channel.fetch_message(message.reference.message_id)
        if original_message.author == bot.user:
            print("USER: " + message.content)
            # Call the assistant and send the response
            ctx = await bot.get_context(message)
            async with ctx.typing():
                assistant_message = send(message.content)
                print("ASSISTANT: " + assistant_message)
                # Truncate if necessary
                if len(assistant_message) > 2000:
                    assistant_message = assistant_message[:1997] + "..."
                sent_message = await message.channel.send(assistant_message)
                for emoji in emojis:
                    await sent_message.add_reaction(emoji)
            return       
    # Check if bot's name has been mentioned directly
    if (CHARACTER_NAME.lower() in message.content.lower() or bot.user.mentioned_in(message)) and not message.content.startswith("?"):
        print("USER: " + message.content)
        # Call the assistant and send the response
        ctx = await bot.get_context(message)
        async with ctx.typing():
            assistant_message = send(message.content)
            print("ASSISTANT: " + assistant_message)
            # Truncate if necessary
            if len(assistant_message) > 2000:
                assistant_message = assistant_message[:1997] + "..."
            sent_message = await message.channel.send(assistant_message)
            for emoji in emojis:
                await sent_message.add_reaction(emoji)
        return
    # Store the message as sent by the bot
    if message.author == bot.user:
        sent_messages[message.id] = message

def is_admin(ctx):
    return ctx.author.guild_permissions.administrator

@bot.command(name='ctn', help='⏩ Send /continue to SillyTavern, the LLM will resume typing if it was cut off and edit its last message.', brief='⏩ Send /continue to SillyTavern')
async def ctn(ctx):
    async with ctx.typing():
        input_field.send_keys("/continue", Keys.ENTER)
        time.sleep(1)
        last_message = s.find_elements(By.CLASS_NAME, "last_mes")[-1]
        notif_div = last_message.find_element(By.CLASS_NAME, "swipe_right")
        # Wait until its style becomes display: flex
        WebDriverWait(s, 120).until(lambda s: notif_div.value_of_css_property("display") == "flex")
        assistant_message_elements = s.find_element(By.CLASS_NAME, "last_mes").find_elements(By.TAG_NAME, "p")
        assistant_messages= "\n\n".join([markdown_handling(p.get_attribute("innerHTML")) for p in assistant_message_elements])
        print("ASSISTANT: " + assistant_messages)
        # Truncate
        if len(assistant_messages) > 2000:
            assistant_messages = assistant_messages[:1997] + "..."
        # Retrieve the bot's message from the channel's history
        async for message in ctx.channel.history(limit=50):
            if message.author == bot.user:
                # Edit the bot's message with the new content
                await message.edit(content=assistant_messages)
                return
        # If no previous message found, send a new one
        await ctx.send(assistant_messages)

@bot.command(name='swipe', help='🔁 Swipe in SillyTavern, the llm will type a new response to the previous prompt and edit its last message.', brief='🔁 Swipe in SillyTavern')
async def swipe(ctx):
    # js to click on swipe button
    js_script = """
    var button = document.querySelector('.swipe_right.fa-solid.fa-chevron-right',':before');
    button.click();
    """
    s.execute_script(js_script)
    time.sleep(1)
    last_message = s.find_elements(By.CLASS_NAME, "last_mes")[-1]
    notif_div = last_message.find_element(By.CLASS_NAME, "swipe_right")
    # Wait until its style becomes display: flex
    WebDriverWait(s, 120).until(lambda s: notif_div.value_of_css_property("display") == "flex")
    assistant_message_elements = s.find_element(By.CLASS_NAME, "last_mes").find_elements(By.TAG_NAME, "p")
    assistant_messages= "\n\n".join([markdown_handling(p.get_attribute("innerHTML")) for p in assistant_message_elements])
    print("ASSISTANT: " + assistant_messages)
    # Truncate
    if len(assistant_messages) > 2000:
            assistant_messages = assistant_messages[:1997] + "..."
    # Retrieve the bot's message from the channel's history
    async for message in ctx.channel.history(limit=50):
            if message.author == bot.user:
                # Edit the bot's message with the new content
                await message.edit(content=assistant_messages)
                return
    # If no previous message found, send a new one
    await ctx.send(assistant_messages) 

# Invoke commands via emoji reacts
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return   
    if str(reaction.emoji) == "⏩":
        async for message in reaction.message.channel.history(limit=50):
            if message.author == bot.user:
                ctx = await bot.get_context(message)
                await ctx.invoke(bot.get_command('ctn'))
                break 
    if str(reaction.emoji) == "🔁":
        async for message in reaction.message.channel.history(limit=50):
            if message.author == bot.user:
                ctx = await bot.get_context(message)
                await ctx.invoke(bot.get_command('swipe'))
                break 

@bot.command(name='setbot', help='Set which bot to talk to, must match bot names in SillyTavern. Admin only.', brief='Set which bot to talk to')
@commands.check(is_admin)
async def setbot(ctx, *, new_name):
    global CHARACTER_NAME
    update_character_name(new_name)
    CHARACTER_NAME = get_character_name()
    select_character()
    await ctx.send(f"Personality set to: {CHARACTER_NAME}")
    for guild in bot.guilds:
        await guild.me.edit(nick=CHARACTER_NAME)
    await get_avatar()
    print(f"CHARACTER_NAME updated: {CHARACTER_NAME}")

@bot.command(name='newchat', help='Send /newchat to SillyTavern, start a fresh chat with the selected character. Admin only.', brief='Send /newchat to SillyTavern')
@commands.check(is_admin)
async def newchat(ctx):
    async with ctx.typing():
        input_field.send_keys("/newchat", Keys.ENTER)
        time.sleep(1)
        assistant_message_elements = s.find_element(By.CLASS_NAME, "last_mes").find_elements(By.TAG_NAME, "p")
        assistant_messages = "\n\n".join([markdown_handling(p.get_attribute("innerHTML")) for p in assistant_message_elements])
        print("ASSISTANT: " + assistant_messages)
        # truncate
        if len(assistant_messages) > 2000:
            assistant_messages = assistant_messages[:1997] + "..."
        await ctx.send(assistant_messages)

bot.run(os.environ['DISCORD_TOKEN'])