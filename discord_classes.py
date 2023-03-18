from discord import Interaction, ButtonStyle
from discord import ui


class BoardView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="b", style=ButtonStyle.gray, custom_id="0_0", row=0)
    async def b0_0(self, interaction: Interaction, button: ui.Button):
        button.disabled = True
        button.style = ButtonStyle.red
        await interaction.response.edit_message(view=self)

    @ui.button(label="b", style=ButtonStyle.gray, custom_id="0_1", row=0)
    async def b0_1(self, interaction: Interaction, button: ui.Button):
        button.disabled = True
        button.style = ButtonStyle.red
        await interaction.response.edit_message(view=self)

    @ui.button(label="b", style=ButtonStyle.gray, custom_id="0_2", row=0)
    async def b0_2(self, interaction: Interaction, button: ui.Button):
        button.disabled = True
        button.style = ButtonStyle.red
        await interaction.response.edit_message(view=self)

    @ui.button(label="b", style=ButtonStyle.gray, custom_id="0_3", row=0)
    async def b0_3(self, interaction: Interaction, button: ui.Button):
        button.disabled = True
        button.style = ButtonStyle.red
        await interaction.response.edit_message(view=self)

    @ui.button(label="b", style=ButtonStyle.gray, custom_id="1_0", row=1)
    async def b1_0(self, interaction: Interaction, button: ui.Button):
        button.disabled = True
        button.style = ButtonStyle.red
        await interaction.response.edit_message(view=self)

    @ui.button(label="b", style=ButtonStyle.gray, custom_id="1_1", row=1)
    async def b1_1(self, interaction: Interaction, button: ui.Button):
        button.disabled = True
        button.style = ButtonStyle.red
        await interaction.response.edit_message(view=self)

    @ui.button(label="b", style=ButtonStyle.gray, custom_id="1_2", row=1)
    async def b1_2(self, interaction: Interaction, button: ui.Button):
        button.disabled = True
        button.style = ButtonStyle.red
        await interaction.response.edit_message(view=self)

    @ui.button(label="b", style=ButtonStyle.gray, custom_id="1_3", row=1)
    async def b1_3(self, interaction: Interaction, button: ui.Button):
        button.disabled = True
        button.style = ButtonStyle.red
        await interaction.response.edit_message(view=self)

    @ui.button(label="b", style=ButtonStyle.gray, custom_id="2_0", row=2)
    async def b2_0(self, interaction: Interaction, button: ui.Button):
        button.disabled = True
        button.style = ButtonStyle.red
        await interaction.response.edit_message(view=self)

    @ui.button(label="b", style=ButtonStyle.gray, custom_id="2_1", row=2)
    async def b2_1(self, interaction: Interaction, button: ui.Button):
        button.disabled = True
        button.style = ButtonStyle.red
        await interaction.response.edit_message(view=self)

    @ui.button(label="b", style=ButtonStyle.gray, custom_id="2_2", row=2)
    async def b2_2(self, interaction: Interaction, button: ui.Button):
        button.disabled = True
        button.style = ButtonStyle.red
        await interaction.response.edit_message(view=self)

    @ui.button(label="b", style=ButtonStyle.gray, custom_id="2_3", row=2)
    async def b2_3(self, interaction: Interaction, button: ui.Button):
        button.disabled = True
        button.style = ButtonStyle.red
        await interaction.response.edit_message(view=self)

    @ui.button(label="b", style=ButtonStyle.gray, custom_id="3_0", row=3)
    async def b3_0(self, interaction: Interaction, button: ui.Button):
        button.disabled = True
        button.style = ButtonStyle.red
        await interaction.response.edit_message(view=self)

    @ui.button(label="b", style=ButtonStyle.gray, custom_id="3_1", row=3)
    async def b3_1(self, interaction: Interaction, button: ui.Button):
        button.disabled = True
        button.style = ButtonStyle.red
        await interaction.response.edit_message(view=self)

    @ui.button(label="b", style=ButtonStyle.gray, custom_id="3_2", row=3)
    async def b3_2(self, interaction: Interaction, button: ui.Button):
        button.disabled = True
        button.style = ButtonStyle.red
        await interaction.response.edit_message(view=self)

    @ui.button(label="b", style=ButtonStyle.gray, custom_id="3_3", row=3)
    async def b3_3(self, interaction: Interaction, button: ui.Button):
        button.disabled = True
        button.style = ButtonStyle.red
        await interaction.response.edit_message(view=self)
