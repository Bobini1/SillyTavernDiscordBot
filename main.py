import time

import discord
import dotenv
from discord.ext import commands
import os
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait

from selenium.webdriver.common.by import By

JS_ADD_TEXT_TO_INPUT = """
  var elm = arguments[0], txt = arguments[1];
  elm.value += txt;
  elm.dispatchEvent(new Event('change'));
  """

dotenv.load_dotenv()

CHARACTER_NAME = os.environ['CHARACTER_NAME']

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='?', description="An LLM bot!!", intents=intents)

print("BOT NAME: " + CHARACTER_NAME)

s = webdriver.Chrome()
s.maximize_window()
s.get("http://127.0.0.1:8000")
time.sleep(1)
# find div with title Character Management
character_management = s.find_element(By.XPATH, "//div[@title='Character Management']")
character_management.click()
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

# find the input field, id send_textarea
input_field = s.find_element(By.ID, "send_textarea")


def send(user_message, edit=False):
    # find the mesid of element with class last_mes
    mesid = int(s.find_elements(By.CLASS_NAME, "last_mes")[-1].get_attribute("mesid"))
    s.execute_script(JS_ADD_TEXT_TO_INPUT, input_field, user_message)
    input_field.send_keys("\n")
    message_to_send = mesid if edit else mesid + 2
    # wait until mesid of last_mes is mesid+2
    WebDriverWait(s, 120).until(lambda s: int(s.find_element(By.CLASS_NAME, "last_mes").get_attribute("mesid")) == message_to_send)
    # find div with class last_mes
    last_message = s.find_elements(By.CLASS_NAME, "last_mes")[-1]
    notif_div = last_message.find_element(By.CLASS_NAME, "swipe_right")
    # wait until its style becomes display: flex
    WebDriverWait(s, 120).until(lambda s: notif_div.value_of_css_property("display") == "flex")
    # find a <p> inside it
    response = last_message.find_elements(By.TAG_NAME, "p")
    response = "\n\n".join([r.text for r in response])
    return response


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')


@bot.event
async def on_message(message):
    if CHARACTER_NAME.lower() in message.content.lower() and not message.content.startswith("?") and message.author != bot.user:
        print("USER: " + message.content)
        ctx = await bot.get_context(message)
        async with ctx.typing():
            assistant_message = send(message.content)
            print("ASSISTANT: " + assistant_message)
            # truncate
            if len(assistant_message) > 2000:
                assistant_message = assistant_message[:1997] + "..."
            await message.channel.send(assistant_message)
    await bot.process_commands(message)


@bot.command()
async def ctn(ctx):
    """Send '/continue' to the llm"""
    async with ctx.typing():
        assistant_message = send("/continue", edit=True)
        print("ASSISTANT: " + assistant_message)
        # truncate
        if len(assistant_message) > 2000:
            assistant_message = assistant_message[:1997] + "..."
        await ctx.send(assistant_message)


bot.run(os.environ['DISCORD_TOKEN'])
