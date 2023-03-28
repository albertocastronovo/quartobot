import os
import sys

import discord
from discord.ext import commands as dc, tasks
from discord import Intents, User, Embed
from discord.ui import View, Button
from game import Game, VictoryPieceType, PieceVal, PieceEmoji
from re import compile, match
from discord_classes import BoardView
import json
import elo
from textwrap import dedent
from random import choice

assert sys.version_info >= (3, 10)

print(f"Executing Python version: {sys.version}")

this_dir = os.path.dirname(__file__)
relative_token = "../../Desktop/quarto_token.txt"
absolute_token = os.path.join(this_dir, relative_token)

with open(absolute_token, "r") as f:
    TOKEN = f.readline()

try:
    with open("games.json", "r") as games_json:
        active_games = json.load(games_json)
        active_games = {
            int(p1): {
                int(p2): Game.from_string(g_str, p1, p2) for p2, g_str in active_games[p1].items()
            } for p1 in active_games.keys()
        }
except FileNotFoundError:
    active_games = {}

try:
    with open("ratings.json", "r") as ratings_json:
        ratings = json.load(ratings_json)
        ratings = {int(key): val for key, val in ratings.items()}
except FileNotFoundError:
    ratings = {}

leaderboard = []


class PersistentBot(dc.Bot):
    def __init__(self):
        intents = Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix=dc.when_mentioned_or("q!"), intents=intents, help_command=None)

    async def setup_hook(self) -> None:
        self.add_view(BoardView())


bot = PersistentBot()

pending_challenges = {}
button_id_pattern = compile(
    "^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}_[0-9]{18}_[0-9]{18}_[0-9]_[0-9]_[0-9]$"
)


@bot.event
async def on_ready():
    print(f"Ready and running as {bot.user}")
    if not save.is_running():
        save.start()


@tasks.loop(minutes=1.0)
async def save():
    print("'save' task started.")
    updated_games_json = {
        p1: {
            p2: g.to_string() for p2, g in active_games[p1].items()
        } for p1 in active_games.keys()
    }
    with open("games.json", "w") as new_games_json:
        json.dump(updated_games_json, new_games_json, indent=4)
    print("'games.json' saved.")

    with open("ratings.json", "w") as new_ratings_json:
        json.dump(ratings, new_ratings_json, indent=4)
    print("'ratings.json' saved.")
    update_leaderboard()


@save.before_loop
async def before():
    await bot.wait_until_ready()


@bot.event
async def on_command_error(context, error):
    if isinstance(error, dc.CommandNotFound):
        await context.send("This command does not exist. Try checking for typos, or consult** 'help' **!")
    elif isinstance(error, dc.UserNotFound):
        await context.send("The argument you provided was not a user I could find! Try again")
    elif isinstance(error, dc.MissingRequiredArgument):
        await context.send("Arguments for this command are missing. Check** 'help' **if you don't know how to use it!")


@dc.Cog.listener()
async def on_interaction(interaction):
    if interaction.data["component_type"] != 2:     # the interactive element is not a button
        return

    if not match(button_id_pattern, interaction.data["custom_id"]):  # the button is not that of a game
        return

    custom_id_params = interaction.data["custom_id"].split("_")
    game_id = custom_id_params[0]
    p1 = int(custom_id_params[1])
    p2 = int(custom_id_params[2])
    stage = int(custom_id_params[3])
    pos_x = int(custom_id_params[4])
    pos_y = int(custom_id_params[5])

    if p1 not in active_games:  # the first player has no active games
        await interaction.response.send_message(
            f"Hey <@{interaction.user.id}>, it looks like you have no active games anymore!"
        )
        return

    if p2 not in active_games[p1]:  # if there is not a game between them
        await interaction.response.send_message(
            f"Hey <@{interaction.user.id}>, there is no active game between you and your opponent!"
        )
        return

    selected_game = active_games[p1][p2]

    if interaction.user.id != p1 and interaction.user.id != p2:     # the caller is not a player
        await interaction.response.send_message("Let the players play their game, please.")
        return

    if str(interaction.message.id) != selected_game.last_message:   # not the last message sent by bot
        await interaction.response.send_message("This message has expired.")
        return

    if str(selected_game.id) != game_id:  # if the id is not the same as that recovered from the button
        await interaction.response.send_message(
            f"Hey <@{interaction.user.id}>, that game is no longer valid!"
        )
        return

    if selected_game.stage != stage:  # if the stage from the button is different from that of the active game
        await interaction.response.send_message(
            f"Hey <@{interaction.user.id}>, that is not the current stage of the game!"
        )
        return

    if str(interaction.user.id) != custom_id_params[selected_game.turn]:  # if it's not your turn
        await interaction.response.send_message(
            f"Hey <@{interaction.user.id}>, it's not your turn! Wait for your opponent."
        )
        return

    previous_message = await interaction.channel.fetch_message(
        int(selected_game.last_message)
    )
    new_view = View.from_message(previous_message)
    button_row = [
        new_view.children[pos_x * 4],
        new_view.children[pos_x * 4 + 1],
        new_view.children[pos_x * 4 + 2],
        new_view.children[pos_x * 4 + 3]
    ]
    for button in button_row:
        new_view.remove_item(button)

    if selected_game.stage == 1:  # the last player selected a piece
        new_emoji_name = selected_game.pieces_matrix[pos_x][pos_y]

        sr = selected_game.select_stage(new_emoji_name)
        if sr == 2 or selected_game.is_board_full():  # the game is a draw
            await interaction.response.send_message("The game is a draw!")
            del active_games[p1][p2]
            if not active_games[p1]:
                del active_games[p1]
            return
        elif sr == 1:  # game continues normally
            selected_game.change_stage()
            selected_game.next_turn()
            view, content = send_board(p1, p2)
            # era qui!!!

        else:  # there was an error.
            await interaction.response.send_message("That piece is already taken!")
            return

    else:  # the last player selected a cell to place the piece
        new_emoji_name = selected_game.last_selected_piece.label

        vb, vc = selected_game.place_stage(pos_x, pos_y)

        if vb > 0:  # stop, game won
            view, content = end_game_by_victory(selected_game, vb, vc)

        elif vb == 0:  # game continues normally
            if selected_game.is_board_full():
                await interaction.response.send_message("The game ended in a draw. Congratulations to both of you!")
                del active_games[p1][p2]
                if not active_games[p1]:
                    del active_games[p1]
            selected_game.change_stage()
            view, content = send_board(p1, p2)

        else:  # there was an error (the cell was not empty)
            await interaction.response.send_message("You selected a non empty cell!")
            return

    new_button = Button(
        style=discord.ButtonStyle.green,
        custom_id=f"{selected_game.id}_{p1}_{p2}_{selected_game.stage}_{pos_x}_{pos_y}",
        disabled=True,
        label=None,
        emoji=f"<:{new_emoji_name}:{PieceEmoji[new_emoji_name].value}>",
        row=pos_x
    )
    for i in range(4):
        if i == pos_y:
            new_view.add_item(new_button)
        else:
            new_view.add_item(button_row[i])

    await previous_message.edit(view=new_view, content=previous_message.content)

    await interaction.response.send_message(view=view, content=content)
    message = await interaction.original_response()
    selected_game.set_last_message(message)


@bot.command(pass_context=True, aliases=["h", "how", "howto", "bot", "quarto"])
async def help(context):
    description = dedent(f"""\
        Welcome to QuartoBot!
        The bot prefix is **q!**.
        Here is the list of commands you can use:
        
        **General commands**
          • **rules**: learn the rules of the game.
        
        **Game commands**
          • **challenge [quote someone]**: challenge the quoted player to a Quarto! game.
          • **accept [quote someone]**: accept the challenge the quoted player sent you and start the game.
          • **deny [quote someone]**: refuse the challenge the quoted player sent you.
          • **resume [quote someone]**: resend the board message of an active game between you and the quoted player.
          
        **Leaderboard commands**
          • **top**: show the top 10 players by ELO (less if < 10 total players).
          • **myrank**: show your position in the leaderboard.
          
    """)
    help_embed = Embed(
        title="QuartoBot Handbook",
        description=description,
        color=0x90ee90
    )
    await context.send(embed=help_embed)


@bot.command(pass_context=True)
async def rules(context):
    rules_message = dedent(f"""\
        Welcome to Quarto!
        
        The game is played on a **4x4 board**.
        The objective is to establish a line of **four pieces with at least one common characteristic** on the board.
        The line may be a **row, column or diagonal** of the game board.
        There are a total of **16 pieces** with different **characteristics**:
          • light or dark
          • round or square
          • tall or short
          • solid or hollow
          
        The first player is selected randomly. That player **selects one of the pieces and gives it to its opponent**.
        The 2nd player places that piece on any square of the board and then selects another piece for the 1st player.
        During its turn, the 1st player will place that piece on the board and select another piece, and so on.
        The game continues until one player completes the objective by placing the piece that was given to it.
        If all the pieces are placed before any player is able to win, the game ends in a draw.
        
    """)
    rules_embed = Embed(
        title="Game rules",
        description=rules_message,
        color=0x7df9ff
    )
    await context.send(embed=rules_embed)


@bot.command(pass_context=True, aliases=["c", "chal", "play"])
async def challenge(context, user: User):
    if user.bot:
        await context.send("Come on, you cannot challenge a bot. Select a human as your worthy opponent!")
        return
    # if context.message.author.id == user.id:
    # await context.send("I know how it feels to be alone, but there's little point in challenging yourself!")
    # return
    player_1 = context.message.author.id
    player_2 = user.id
    if player_1 not in pending_challenges:
        pending_challenges[player_1] = [player_2]
    elif player_2 not in pending_challenges[player_1]:
        pending_challenges[player_1].append(player_2)
    else:
        await context.send("A challenge is still pending. Wait for your rival to accept or deny your request!")
        return
    await context.send(f"<@{player_2}> has been challenged. Will he accept?")
    return


@bot.command(pass_context=True, aliases=["a", "yes"])
async def accept(context, user: User):
    challenger = user.id
    rival = context.message.author.id
    if challenger in pending_challenges and rival in pending_challenges[challenger]:
        first_to_start = choice([1, 2])
        if challenger not in active_games:
            active_games[challenger] = {rival: Game(challenger, rival, first_to_start)}
        elif rival not in active_games[challenger]:
            active_games[challenger][rival] = Game(challenger, rival, first_to_start)
        else:
            await context.send(
                f"You already have an unfinished game with <@{challenger}>. Finish it before starting a new one!")
            return
        pending_challenges[challenger].remove(rival)
        await context.send(f"<@{rival}> accepted your challenge, <@{challenger}>! The game will now begin.")

        if challenger not in ratings:   # if the challenger has no ranking yet
            ratings[challenger] = {"wins": 0, "losses": 0, "elo": 1000}

        if rival not in ratings:   # if the rival has no ranking yet
            ratings[rival] = {"wins": 0, "losses": 0, "elo": 1000}

        view, content = send_board(challenger, rival)
        message = await context.send(view=view, content=content)
        active_games[challenger][rival].set_last_message(message)

    else:
        await context.send(f"<@{challenger}> never challenged you to a game!")


@bot.command(pass_context=True, aliases=["d", "no"])
async def deny(context, user: User):
    challenger = user.id
    rival = context.message.author.id
    if challenger in pending_challenges and rival in pending_challenges[challenger]:
        pending_challenges[challenger].remove(rival)
        await context.send(f"<@{rival}> did not accept your challenge, <@{challenger}>. Try finding another opponent!")
    else:
        await context.send(f"<@{challenger}> never challenged you to a game!")


@bot.command(pass_context=True, aliases=["continue", "r", "goon"])
async def resume(context, user: User):
    player_a = context.message.author.id
    player_b = user.id
    if player_a not in active_games and player_b not in active_games:   # if none of them is in an active game
        await context.send("Neither of you is currently in an active game. Consider challenging each other!")
        return
    if (player_a in active_games and player_b not in active_games[player_a])\
            or (player_b in active_games and player_a not in active_games[player_b]):
        await context.send("You don't have an active game with that user. Consider using q!challenge to start playing!")
        return
    try:
        challenger = player_a
        rival = player_b
        view, content = send_board(challenger, rival)
    except KeyError:
        challenger = player_b
        rival = player_a
        view, content = send_board(challenger, rival)
    message = await context.send(view=view, content=content)
    active_games[challenger][rival].set_last_message(message)


@bot.command(pass_context=True, aliases=["forfeit", "ff", "surrender", "surr"])
async def concede(context, user: User):
    loser = context.message.author.id
    winner = user.id
    print("before if")
    if loser not in active_games and winner not in active_games:   # if none of them is in an active game
        await context.send("You cannot concede a game that does not exist.")
        return
    if (loser in active_games and winner not in active_games[loser])\
            or (winner in active_games and loser not in active_games[winner]):
        await context.send("You don't have an active game with that user. Consider using q!challenge to start playing!")
        return
    print("passed controls")
    try:
        selected_game = active_games[loser][winner]
    except KeyError:
        selected_game = active_games[winner][loser]
    print("before end game by victory")
    _, content = end_game_by_victory(selected_game, 5, 1, loser)
    await context.send(content)


@bot.command(pass_context=True, aliases=["t", "rank", "leaderboard"])
async def top(context):
    embed = Embed(
        title=f"Top {min(10, len(leaderboard))} players by ELO",
        description="If you're not in here, you can use **q!myrank** to check your position!",
        color=0xffd700
    )
    await print_leaderboard(context, embed, 1, 10)


@bot.command(pass_context=True, aliases=["me", "mypos", "myposition"])
async def myrank(context):
    user_id = context.message.author.id
    if user_id not in leaderboard:
        await context.send("You don't have a rank yet. Find an opponent to start playing!")
        return
    user_pos = leaderboard.index(user_id)
    embed = Embed(
        title=f"{context.guild.get_member(user_id).display_name}'s position in the leaderboard",
        description=f"You are currently **#{user_pos+1}!**",
        color=0xffd700
    )
    if user_pos < 4:
        await print_leaderboard(context, embed, 1, user_pos + 5)
    elif user_pos > len(leaderboard) - 5:
        await print_leaderboard(context, embed, user_pos - 3, len(leaderboard))
    else:
        await print_leaderboard(context, embed, user_pos - 3, user_pos + 5)


@bot.command(pass_context=True, aliases=["mystats", "wr"])
async def stats(context, *args):
    print(args[0])

    if len(args) < 0:   # only print data for single user
        pass
    else:               # print data for all mentioned users
        for arg in args:
            print(arg.id)

async def print_leaderboard(context, formatted_embed: Embed, start_pos: int = 1, end_pos: int = 1):
    if len(leaderboard) == 0:             # if no players are present in the leaderboard
        await context.send("There is no player yet. You may be the first one!")
        return
    if start_pos > end_pos:
        return

    start_pos = max(1, start_pos)
    end_pos = min(end_pos, len(leaderboard))
    rank_list = [f"#{i}" for i in range(start_pos, end_pos + 1)]
    name_list = [context.guild.get_member(m).display_name
                 if context.guild.get_member(m) is not None else "Unknown player"
                 for m in leaderboard[start_pos-1:end_pos]
                 ]
    elo_list = [f"{ratings[i]['elo']}" for i in leaderboard[start_pos-1:end_pos]]

    formatted_embed.add_field(
        name="Rank",
        value="\n".join(rank_list)
    )
    formatted_embed.add_field(
        name="Name",
        value="\n".join(name_list)
    )
    formatted_embed.add_field(
        name="ELO",
        value="\n".join(elo_list)
    )

    await context.send(embed=formatted_embed)


def update_leaderboard():
    global leaderboard
    try:
        leaderboard = [int(i[0]) for i in sorted(ratings.items(), key=lambda x: x[1]["elo"], reverse=True)]
    except (KeyError, IndexError):
        return


def send_board(player_1, player_2):
    print("before selected game")
    print(f"total games: {active_games}")
    print(f"games: {active_games[player_1]}")
    selected_game = active_games[player_1][player_2]
    print("before game board")
    game_board = selected_game.board.board
    view = View(timeout=None)
    print("in send board: after view creation")
    for i in range(len(game_board)):
        for j in range(len(game_board)):
            if selected_game.stage == 1:  # piece selection

                emoji_name = selected_game.pieces_matrix[i][j]
                emoji = f"<:{emoji_name}:{PieceEmoji[emoji_name].value}>"
                label = None
                disabled = selected_game.pieces.get(emoji_name) is None
                if disabled:
                    button_style = discord.ButtonStyle.red
                else:
                    button_style = discord.ButtonStyle.blurple
            else:  # piece placement
                emoji_name = PieceVal(game_board[i][j]).name
                emoji = f"<:{emoji_name}:{PieceEmoji[emoji_name].value}>"
                label = None
                disabled = game_board[i][j] != 0
                button_style = discord.ButtonStyle.gray

            if selected_game.state == 1 or selected_game.state == 2:    # if the game is won
                x, y = selected_game.last_xy
                if selected_game.win_cond == 1:     # row
                    if i == x:
                        button_style = discord.ButtonStyle.green
                    else:
                        button_style = discord.ButtonStyle.gray
                elif selected_game.win_cond == 2:   # col
                    if j == y:
                        button_style = discord.ButtonStyle.green
                    else:
                        button_style = discord.ButtonStyle.gray
                elif selected_game.win_cond == 3:   # diag1
                    if i == j:
                        button_style = discord.ButtonStyle.green
                    else:
                        button_style = discord.ButtonStyle.gray
                elif selected_game.win_cond == 4:   # diag2
                    if i == 3 - j:
                        button_style = discord.ButtonStyle.green
                    else:
                        button_style = discord.ButtonStyle.gray
                else:
                    button_style = discord.ButtonStyle.gray

            button = Button(
                style=button_style,
                custom_id=f"{selected_game.id}_{player_1}_{player_2}_{selected_game.stage}_{i}_{j}",
                disabled=disabled,
                label=label,
                emoji=emoji,
                row=i
            )
            button.callback = on_interaction
            view.add_item(button)
    print("in send board: after double for loop")
    if selected_game.turn == 1:
        whose_turn = player_1
    else:
        whose_turn = player_2
    print(f"before selected state: {selected_game.state}")
    if selected_game.state == 1 or selected_game.state == 2:
        content = f"Congratulations, <@{whose_turn}>! You won!"
    elif selected_game.state == 3:
        content = f"The game is a draw!"
    else:
        print(f"before selected stage: {selected_game.stage}")
        if selected_game.stage == 1:
            content = f"<@{whose_turn}>, player {selected_game.turn}, pick a piece for your opponent!"
        else:
            content = f"<@{whose_turn}>, player {selected_game.turn}, place your piece on the board!"
    return view, content


def end_game_by_victory(selected_game: Game, victory_by: int, victory_code: int, conceding_player=None):
    if victory_by <= 0:
        return -1, -1
    print("passed victory by")
    p1, p2 = selected_game.get_players()
    turn = selected_game.turn
    feature = VictoryPieceType(victory_code).name.lower()
    print("before send board")
    view, _ = send_board(p1, p2)
    print("before content writing")
    if victory_by == 5 and conceding_player is not None:     # code for victory by forfeit
        cturn = 1 if p1 == conceding_player else 2
        content = f"Player {cturn} decided to concede. Player {3 - cturn} wins!"
        if cturn == 1:
            winner = p2
            loser = p1
        else:
            winner = p1
            loser = p2
    else:
        content = f"Player {turn} won with {feature} pieces. Congratulations!"
        if turn == 1:
            winner = p1
            loser = p2
        else:
            winner = p2
            loser = p1
    print("before try statement")
    try:
        r_winner = ratings[winner]["elo"]
        r_loser = ratings[loser]["elo"]
        p_winner = elo.get_winning_probability(r_winner, r_loser)
        p_loser = 1 - p_winner
        next_winner = elo.get_next_rating(r_winner, p_winner, won=1)
        next_loser = elo.get_next_rating(r_loser, p_loser, won=0)
        content += f"\nYou won, <@{winner}>! Your rating increases from {r_winner} to {next_winner}"
        content += f"\nYou lost, <@{loser}>! Your rating decreases from {r_loser} to {next_loser}"
        print("after content in try")
        ratings[winner]["elo"] = next_winner
        ratings[winner]["wins"] += 1
        ratings[loser]["elo"] = next_loser
        ratings[loser]["losses"] += 1

    except KeyError:
        print("inside except statement")
        content += "\nThe ELO of the players could not be retrieved. The ratings won't be changed."
    del active_games[p1][p2]
    if not active_games[p1]:
        del active_games[p1]

    return view, content


bot.run(TOKEN)
