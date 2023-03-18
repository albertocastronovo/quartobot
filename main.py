import os
import sys

import discord
from discord.ext import commands as dc, tasks
from discord import Intents, User
from discord.ui import View, Button
from game import Game, VictoryPieceType, PieceVal, PieceEmoji
from re import compile, match
from discord_classes import BoardView
import json
import elo

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
except FileNotFoundError:
    ratings = {}


class PersistentBot(dc.Bot):
    def __init__(self):
        intents = Intents.default()
        intents.message_content = True
        super().__init__(command_prefix=dc.when_mentioned_or("q!"), intents=intents)

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
    print("Currently printing previously loaded games:")
    print(active_games)
    if not save.is_running():
        save.start()
    print("Task save running.")


@tasks.loop(minutes=5.0)
async def save():
    print("Task started.")
    updated_games_json = {
        p1: {
            p2: g.to_string() for p2, g in active_games[p1].items()
        } for p1 in active_games.keys()
    }
    with open("games.json", "w") as new_games_json:
        json.dump(updated_games_json, new_games_json)

    with open("ratings.json", "w") as new_ratings_json:
        json.dump(ratings, new_ratings_json)
    print("Task executed.")


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
            if vb == 1:  # won by row
                content = f"Player {selected_game.turn} won by row with {VictoryPieceType(vc).name.lower()} pieces"
            elif vb == 2:  # won by col
                content = f"Player {selected_game.turn} won by col with {VictoryPieceType(vc).name.lower()} pieces"
            elif vb == 3:  # won by first diag
                content = f"Player {selected_game.turn} won by diag1 with {VictoryPieceType(vc).name.lower()} pieces"
            else:  # won by second diag
                content = f"Player {selected_game.turn} won by diag2 with {VictoryPieceType(vc).name.lower()} pieces"
            view, _ = send_board(p1, p2)

            try:
                winner = p1 if selected_game.turn == 1 else p2
                loser = p2 if selected_game.turn == 1 else p1
                r_winner = ratings[winner]["elo"]
                r_loser = ratings[loser]["elo"]
                p_winner = elo.get_winning_probability(r_winner, r_loser)
                p_loser = 1 - p_winner
                next_winner = elo.get_next_rating(r_winner, p_winner, won=1)
                next_loser = elo.get_next_rating(r_loser, p_loser, won=0)
                content += f"\nYou won, <@{winner}>! Your rating increases from {r_winner} to {next_winner}"
                content += f"\nYou lost, <@{loser}>! Your rating decreases from {r_loser} to {next_loser}"
                ratings[winner]["elo"] = next_winner
                ratings[winner]["wins"] += 1
                ratings[loser]["elo"] = next_loser
                ratings[loser]["losses"] += 1

            except KeyError:
                content += "\nThe ELO of the players could not be retrieved. The ratings won't be changed."

            del active_games[p1][p2]
        elif vb == 0:  # game continues normally
            if selected_game.is_board_full():
                await interaction.response.send_message("The game ended in a draw. Congratulations to both of you!")
                del active_games[p1][p2]
            selected_game.change_stage()
            view, content = send_board(p1, p2)
            # era qui!!!

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


@bot.command(pass_context=True)
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


@bot.command(pass_context=True)
async def accept(context, user: User):
    challenger = user.id
    rival = context.message.author.id
    if challenger in pending_challenges and rival in pending_challenges[challenger]:
        if challenger not in active_games:
            active_games[challenger] = {rival: Game(challenger, rival)}
        elif rival not in active_games[challenger]:
            active_games[challenger][rival] = Game(challenger, rival)
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


@bot.command(pass_context=True)
async def deny(context, user: User):
    challenger = user.id
    rival = context.message.author.id
    if challenger in pending_challenges and rival in pending_challenges[challenger]:
        pending_challenges[challenger].remove(rival)
        await context.send(f"<@{rival}> did not accept your challenge, <@{challenger}>. Try finding another opponent!")
    else:
        await context.send(f"<@{challenger}> never challenged you to a game!")


@bot.command(pass_context=True)
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


@bot.command(pass_context=True)
async def test(context):
    print("command registered")
    await context.send("Test message!", view=BoardView())


def send_board(player_1, player_2):
    selected_game = active_games[player_1][player_2]
    game_board = selected_game.board.board
    view = View(timeout=None)
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
    if selected_game.turn == 1:
        whose_turn = player_1
    else:
        whose_turn = player_2
    if selected_game.state == 1 or selected_game.state == 2:
        content = f"Congratulations, <@{whose_turn}>!"
    elif selected_game.state == 3:
        content = f"The game is a draw!"
    else:
        if selected_game.stage == 1:
            content = f"<@{whose_turn}>, player {selected_game.turn}, pick a piece for your opponent!"
        else:
            content = f"<@{whose_turn}>, player {selected_game.turn}, place your piece on the board!"
    return view, content


bot.run(TOKEN)
