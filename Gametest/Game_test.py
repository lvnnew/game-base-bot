import discord
from discord.ext import commands

import sqlite3
from config import settings

client = commands.Bot(command_prefix = settings['PREFIX'])
client.remove_command('help')

connection = sqlite3.connect('server.db')
cursor = connection.cursor()


@client.event
async def on_ready():
        cursor.execute("""CREATE TABLE IF NOT EXISTS users (
                name TEXT,
                id INT,
                cash BIGINT,
                rep INT,
                lvl INT,
                server_id INT,
        )""")

        cursor.execute("""CREATE TABLE IF NOT EXISTS shop (
            role_id INT,
            id INT,
            cost BIGINT,
        )""")

        for guild in client.guilds:
                for member in guild.members:
                        if cursor.execute(f"SELECT id FROM users WHERE id = {member.id}").fetchone() is None:
                                cursor.execute(f"INSERT INTO users VALUES ('{member}', {member.id}, 0, 0, 1, {guild.id})")
                        else:
                                pass

        connection.commit()
        print('Bot connected')


@client.event
async def on_member_join(member):
        if cursor.execute(f"SELECT id FROM users WHERE id = {member.id}").fetchone() is None:
                cursor.execute(f"INSERT INTO users VALUES ('{member}', {member.id}, 0, 0, 1, {member.guild.id})")
                connection.commit()
        else:
                pass


@client.command(aliases = ['баланс', 'счет']) # показать твой счет или счет @конкретного пользователя
async def __balance(ctx, member: discord.Member = None):
        if member is None:
                await ctx.send(embed = discord.Embed(
                        description = f"""Баланс пользователя **{ctx.author}** составляет **{cursor.execute("SELECT cash FROM users WHERE id = {}".format(ctx.author.id)).fetchone()[0]} :leaves:**"""
                ))
        else:
                await ctx.send(embed = discord.Embed(
                        description = f"""Баланс пользователя **{member}** составляет **{cursor.execute("SELECT cash FROM users WHERE id = {}".format(member.id)).fetchone()[0]} :leaves:**"""
                ))


@client.command(aliases = ['выдать']) # начислить @конкретному пользователю, определенную сумму
async def __award(ctx, member: discord.Member = None, amount: int = None):
    if member is None:
        await ctx.send(f"**{ctx.author}**, укажите пользователя, которому желаете выдать определенную сумму")
    else:
        if amount is None:
            await ctx.send(f"**{ctx.author}**, укажите сумму, которую желаете начислить на счет пользователя")
        elif amount < 1:
            await ctx.send(f"**{ctx.author}**, укажите сумму больше 1 :leaves:")
        else:
            cursor.execute("UPDATE users SET cash = cash + {} WHERE id = {}".format(amount, member.id))
            connection.commit()

            await ctx.message.add_reaction('✅')

@client.command(aliases = ['забрать']) # снять у @конкретного пользователя, определенную сумму
async def __take(ctx, member: discord.Member = None, amount = None):
    if member is None:
        await ctx.send(f"**{ctx.author}**, укажите пользователя, у которого желаете отнять определенную сумму")
    else:
        if amount is None:
            await ctx.send(f"**{ctx.author}**, укажите сумму, которую желаете отнять со счета пользователя")
        elif amount == 'all':
            cursor.execute("UPDATE users SET cash = {} WHERE id = {}".format(0, member.id))
            connection.commit()

            await ctx.message.add_reaction('✅')
        elif int(amount) < 1:
            await ctx.send(f"**{ctx.author}**, укажите сумму больше 1 :leaves:")
        else:
            cursor.execute("UPDATE users SET cash = cash - {} WHERE id = {}".format(int(amount), member.id))
            connection.commit()

            await ctx.message.add_reaction('✅')

@client.command(aliases = ['добавить-роль']) # добавить @конкретную роль в магазин ролей
async def __add_shop(ctx, role: discord.Role = None, cost: int = None):
    if role is None:
        await ctx.send(f"**{ctx.author}**, укажите роль, которую вы хотите внести в магазин")
    else:
        if cost is None:
            await ctx.send(f"**{ctx.author}**, укажите стоимость для данной роли")
        elif cost < 0:
            await ctx.send(f"**{ctx.author}**, стоимость роли не может быть такой маленькой")
        else:
            cursor.execute("INSERT INTO shop VALUES ({}, {}, {})".format(role.id, ctx.guild.id, cost))
            connection.commit()

            await ctx.message.add_reaction('✅')


@client.command(aliases = ['удалить-роль']) # удалить @конкретную роль из магазина ролей
async def __remove_shop(ctx, role: discord.Role = None):
    if role is None:
        await ctx.send(f"**{ctx.author}**, укажите роль, которую вы желаете удалить из магазина")
    else:
        cursor.execute("DELETE FROM shop WHERE role_id = {}".format(role.id))
        connection.commit()

        await ctx.message.add_reaction('✅')


@client.command(aliases = ['все-роли']) # посмотреть все свои купленные роли или роли @конкретного пользователя
async def __shop(ctx):
    embed = discord.Embed(title = 'Магазин ролей')

    for row in cursor.execute("SELECT role_id, cost FROM shop WHERE id = {}".format(ctx.guild.id)):
        if ctx.guild.get_role(row[0]) != None:
            embed.add_field(
                name = f"Стоимость {row[1]}",
                value = f"Вы приобрете роль {ctx.guild.get_role(row[0]).mention}",
                inline = False
            )
        else:
            pass

    await ctx.send(embed = embed)


@client.command(aliases = ['купить', 'купить-роль']) # купить @определенную роль
async def __buy(ctx, role: discord.Role = None):
    if role is None:
        await ctx.send(f"**{ctx.author}**, укажите роль, которую вы желаете приобрести в магазине")
    else:
        if role in ctx.author.roles:
            await ctx.send(f"**{ctx.author}**, у вас уже имеется данная роль")
        elif cursor.execute("SELECT cost FROM shop WHERE role_id = {}".format(role.id)).fetchone()[0] > cursor.execute("SELECT cash FROM users WHERE id = {}".format(ctx.author.id)).fetchone()[0]:
            await ctx.send(f"**{ctx.author}**, у вас не достаточно средств для покупки данной роли")
        else:
            await ctx.author.add_roles(role)
            cursor.execute("UPDATE users SET cash = cash - {0} WHERE id = {1}".format(cursor.execute("SELECT cost FROM shop WHERE role_id = {}".format(role.id)).fetchone()[0], ctx.author.id))
            connection.commit()

            await ctx.message.add_reaction('✅')


@client.command(aliases = ['репутация', 'репа']) #начислить 1 репутацию, @конкретному пользователю
async def __rep(ctx, member: discord.Member = None):
    if member is None:
        await ctx.send(f"**{ctx.author}**, укажите участника сервера")
    else:
        if member.id == ctx.author.id:
            await ctx.send(f"**{ctx.author}**, вы не можете указать самого себя")
        else:
            cursor.execute("UPDATE users SET rep = rep + {} WHERE id = {}".format(1, member.id))
            connection.commit()

            await ctx.message.add_reaction('✅')


@client.command(aliases = ['топ', 'в-топе']) # посмотреть топ 10 игроков
async def __leaderboard(ctx):
    embed = discord.Embed(title = 'Топ 10 сервера')
    counter = 0

    for row in cursor.execute("SELECT name, cash FROM users WHERE server_id = {} ORDER BY cash DESC LIMIT 10".format(ctx.guild.id)):
        counter += 1
        embed.add_field(
        name = f'# {counter} | "{row[0]}"',
        value = f'Баланс: {row[1]}',
        inline = False
        )

    await ctx.send(embed = embed)


client.run(settings['TOKEN'])
