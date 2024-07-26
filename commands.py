import re
import inspect
import sys
import json
import os
from datetime import datetime
from datetime import timezone

COMMAND_REGEX = None
COMMAND_PREFIX="+sb"
COMMAND_REGEX_STR = r"\s+(?P<command>\S+)(\s+(?P<args>.+))?"
RP_CATEGORIES_KEY = "rp_categories"
ENABLED_ROLES_KEY = "enabled_roles"
DATA_DICT = None

#TODO: Populate function pointers once, at startup

def get_command_function(function_name):
    members = inspect.getmembers(sys.modules[__name__])
    for member in members:
        func = None
        if member[0] == function_name:
            func = member[1]
        if func and inspect.isfunction(func):
            return func
    return None

def get_guild_data(guild):
    global DATA_DICT
    if not DATA_DICT:
        print("Attempting to load data dict from disk")
        load_data_dict()
    if not DATA_DICT: #if that didn't work
        print("Initializing new empty data dict")
        DATA_DICT = {}
    if not str(guild.id) in DATA_DICT.keys():
        print(f"guild id {guild.id} is not present in {DATA_DICT.keys()}")
        print("Initialiazing new subsection for guild")
        DATA_DICT[str(guild.id)] = {}
    guild_dict = DATA_DICT[str(guild.id)]
    if not RP_CATEGORIES_KEY in guild_dict:
        print("Adding rp_categories key to data for guild")
        guild_dict[RP_CATEGORIES_KEY] = []
    if not ENABLED_ROLES_KEY in guild_dict:
        print("Adding enabled_roles key to data for guild")
        guild_dict[ENABLED_ROLES_KEY] = []

    return guild_dict

def load_data_dict():
    global DATA_DICT
    path = os.getenv('DATA_DICT_PATH')
    if path and os.path.exists(path):
        with open(path) as json_file:
            DATA_DICT = json.load(json_file)

def save_data_dict():
    global DATA_DICT
    path = os.getenv('DATA_DICT_PATH')
    if path:
        with open(path, 'w') as json_file:
            json.dump(DATA_DICT, json_file, indent=4)

def format_member_post_out(member, message):
    return f"{member.display_name} ({member.name}) posted https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id} "+ \
            f"on {message.created_at.date()} UTC ({(datetime.now(timezone.utc) - message.created_at.replace(tzinfo=timezone.utc)).days} day(s) ago)"
            

async def parse_command(message):
    global COMMAND_REGEX
    if not COMMAND_REGEX:
        COMMAND_REGEX = re.compile(re.escape(COMMAND_PREFIX) + r"\s+(?P<command>\S+)(\s+(?P<args>.+))?")
    command_string = message.content
    result = re.match(COMMAND_REGEX, command_string)
    if not result:
        return
    command = result.group("command")
    args = result.group("args")
    print(f"Parsed command '{command}' with args '{args}'")
    if not command in COMMAND_DICT:
        await message.channel.send(f"{command} is not a valid command")
        return
    entry = COMMAND_DICT[command]
    func_name = entry["func"]
    command_function = get_command_function(func_name)
    if command_function == None:
        await message.channel.send("Function not defined")
        return
    await command_function(message, args)

COMMAND_DICT = {
        "help" : {
            "usage" : "help",
            "desc" : "Show the bot commands",
            "func" : "cmd_list_commands"
        },
        "addrpcat" : {
            "usage" : "addrpcat <category>",
            "desc" : "Add a category to the list of categories considered active for RP",
            "func" : "cmd_add_rp_cat"
        },
        "delrpcat" : {
            "usage" : "delrpcat <category>",
            "desc" : "Delete a category from the list of categories considered active for RP",
            "func" : "cmd_del_rp_cat"
        },
        "listrpcats" : {
            "usage" : "listrpcats",
            "desc" : "Show all of the current RP categories",
            "func" : "cmd_list_rp_cats"
        },
        "adduserrole" : {
            "usage" : "adduserrole <rolename>",
            "desc" : "Add a role that qualifies somebody to use the bot commands",
            "func" : "cmd_add_user_role"
        },
        "deluserrole" : {
            "usage" : "deluserrole <rolename>",
            "desc" : "Remove a role from the list of qualified user roles",
            "func" : "cmd_del_user_role"
        },
        "listuserroles" : {
            "usage" : "listuserroles",
            "desc" : "List the roles that are qualified to use the bot",
            "func" : "cmd_list_user_roles"
        },
        "getuserrp" : {
            "usage": "getuserrp <username>",
            "desc" : "Get the last post in an RP category from a given user",
            "func" : "cmd_get_user_rp"
        },
        "getallrp": {
            "usage" : "getallrp",
            "desc" : "Get the last RP post for each member of the server",
            "func" : "cmd_get_all_rp"
        }
}

def get_category_by_name(guild, name):
    category_list = guild.categories
    for category in category_list:
        if category.name.lower() == name.lower():
           return category
    return None

def get_category_by_id(guild, id_str):
    category_list = guild.categories
    for category in category_list:
        if str(category.id) == id_str:
            return category
    return None

def get_role_by_name(guild, name):
    role_list = guild.roles
    for role in role_list:
        if role.name.lower() == name.lower():
            return role
    return None

def get_role_by_id(guild, id_str):
    role_list = guild.roles
    for role in role_list:
        if id_str == str(role.id):
            return role
    return None

def get_text_channels(guild):
    text_channel_list = []
    guild_data = get_guild_data(guild)
    for category_id in guild_data[RP_CATEGORIES_KEY]:
        category = get_category_by_id(guild, category_id)
        for text_channel in category.text_channels:
            text_channel_list.append(text_channel)
    return text_channel_list

def get_member_by_id(guild, member_id):
    for member in guild.members:
        if member.id == member_id:
            return member
    return None

def get_member_by_name(guild, member_name):
    for member in guild.members:
        if member.name == member_name:
            return member
    return None

def check_if_authorized(member):
    guild_data = get_guild_data(member.guild)
    role_id_list = guild_data[ENABLED_ROLES_KEY]
    for role_id in role_id_list:
        role = get_role_by_id(member.guild, role_id)
        if role and role in member.roles:
            return True
    return False

async def get_last_post_for_user(guild, user_id):
    text_channel_list = get_text_channels(guild)
    last_post = None
    candidate_post_list = []
    for text_channel in text_channel_list:
        async for message in text_channel.history(limit=200):
            if not message.author.id == user_id:
                continue
            candidate_post_list.append(message)
            break
    for message in candidate_post_list:
        if not last_post:
            last_post = message
        elif last_post.created_at < message.created_at:
            last_post = message
    return last_post
    
async def get_last_posts_for_all_users(guild):
    out_map = {}
    text_channel_list = get_text_channels(guild)
    channel_map = {}
    for text_channel in text_channel_list:
        messages = [ message async for message in text_channel.history(limit=100) ]
        channel_map[text_channel] = messages
        threads = text_channel.threads
        for thread in threads:
            thread_messages = [ message async for message in thread.history(limit=100) ]
            channel_map[thread] = thread_messages
    for member in guild.members:
        if member.bot:
            continue
        last_post = None
        for channel in channel_map:
            message_list = channel_map[channel]
            for message in message_list:
                if message.author != member:
                    continue
                if last_post == None or last_post.created_at < message.created_at:
                    last_post = message
        out_map[member] = last_post
    return out_map


async def cmd_list_commands(message, args):
    commands_list = []
    for key,value in COMMAND_DICT.items():
        commands_list.append(COMMAND_PREFIX + " " + value["usage"] + " : " + value["desc"])
        commands_string = "\n".join(commands_list)
    await message.channel.send("These are the commands:\n" + "```" + commands_string + "```")

async def cmd_add_rp_cat(message, args):
    category = get_category_by_name(message.guild, args)
    if category != None:
        guild_data = get_guild_data(message.guild)
        if not str(category.id) in guild_data[RP_CATEGORIES_KEY]:
            guild_data[RP_CATEGORIES_KEY].append(str(category.id))
            await message.channel.send("Added category " + category.name)
            save_data_dict()
        else:
            await message.channel.send("Category " + category.name + " is already added")
    else:
        await message.channel.send(args + " is not a valid category")

async def cmd_list_rp_cats(message, args):
    guild_data = get_guild_data(message.guild)
    category_list = []
    for category_id in guild_data[RP_CATEGORIES_KEY]:
        category = get_category_by_id(message.guild, category_id)
        if category:
            category_list.append(category)
    if len(category_list) == 0:
        await message.channel.send("There are no current RP categories")
        return
    string_out_list = []
    string_out_list.append("Current RP categories:```")
    for category in category_list:
        string_out_list.append(f"Category: {category.name}\n")
    string_out_list.append("```")
    await message.channel.send("".join(string_out_list))

async def cmd_add_user_role(message, args):
    role = get_role_by_name(message.guild, args)
    if role != None:
        guild_data = get_guild_data(message.guild)
        role_list = guild_data[ENABLED_ROLES_KEY]
        if not str(role.id) in role_list:
            role_list.append(str(role.id))
            await message.channel.send("Added role " + role.name)
            save_data_dict()
        else:
            await message.channel.send("Role " + role.name + " is already added")
    else:
        await message.channel.send(args + " is not a valid role")

async def cmd_del_user_role(message, args):
    role = get_role_by_name(message.guild, args)
    if role != None:
        guild_data = get_guild_data(message.guild)
        role_list = guild_data[ENABLED_ROLES_KEY]
        if str(role.id) in role_list:
            role_list.remove(str(role.id))
            await message.channel.send("Removed role " + role.name)
            save_data_dict()
        else:
            await message.channel.send("Role " + role.name + " is not currently added")
    else:
        await message.channel.send(args + " is not a valid role")

async def cmd_list_user_roles(message, args):
    guild_data = get_guild_data(message.guild)
    role_list = []
    for role_id_str in guild_data[ENABLED_ROLES_KEY]:
        role = get_role_by_id(message.guild, role_id_str)
        if role:
            role_list.append(role)
    if len(role_list) == 0:
        await message.channel.send("There are currently no qualified roles")
        return
    string_out_list = []
    string_out_list.append("Current qualified roles:```")
    for role in role_list:
        string_out_list.append(f"Role: {role.name}\n")
    string_out_list.append("```")
    await message.channel.send("".join(string_out_list))

async def cmd_get_user_rp(message, args):
    member = get_member_by_name(message.guild, args)
    if member == None:
        await message.channel.send(f"{args} is not a valid user name")
        return
    await message.channel.send(f"Retrieving last RP post for {member.display_name}...")
    last_post = None
    last_post = await get_last_post_for_user(message.guild, member.id)
    if last_post == None:
        await message.channel.send(f"No posts found for user {member.name}")
    await message.channel.send(format_member_post_out(member, last_post))


async def cmd_get_all_rp(message, args):
    guild_data = get_guild_data(message.guild)
    await message.channel.send("Warning: This could take a while")
    post_map = await get_last_posts_for_all_users(message.guild)
    for member in post_map:
        if post_map[member]:
            await message.channel.send(format_member_post_out(member, post_map[member]))
        else:
            await message.channel.send(f"{member.name} has no RP posts found")
