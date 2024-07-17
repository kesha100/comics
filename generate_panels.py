import re
import openai
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
import os

openai.api_key = os.getenv('OPENAI_API_KEY')

def extract_panel_info(text):
    panel_info_list = []
    panel_blocks = text.split('# Panel')

    for block in panel_blocks:
        if block.strip():
            panel_info = {}
            # Extracting panel number
            panel_number = re.search(r'(\d+)', block)
            if panel_number:
                panel_info['number'] = panel_number.group()
            # Extracting panel description
            panel_description = re.search(r'description: (.+?)(?:\n|$)', block)
            if panel_description:
                panel_info['description'] = panel_description.group(1).strip()
            # Extracting panel text
            panel_text = re.search(r'text:\n```\n(.+?)\n```', block, re.DOTALL)
            if panel_text:
                panel_info['text'] = panel_text.group(1).strip()
            panel_info_list.append(panel_info)
    return panel_info_list

def generate_panels(scenario):
    template = """
    You are a cartoon creator.

    You will be given a short scenario, which you must split into 12 parts.
    Each part will be a different cartoon panel.
    For each cartoon panel, you will write a description of it with:
     - the characters in the panel, described precisely and consistently in each panel
     - the background of the panel
     - the same characters appearing throughout all panels without changing their descriptions
     - maintaining the same style for all panels

    The description should consist only of words or groups of words delimited by commas, no sentences.
    Always use the characters' descriptions instead of their names in the cartoon panel descriptions.
    Do not repeat the same description for different panels.

    You will also write the text of the panel.
    The text should not be more than 2 short sentences.
    Each sentence should start with the character's name.

    Example input:
    Characters: Adrien is a guy with blond hair wearing glasses. Vincent is a guy with black hair wearing a hat.
    Adrien and Vincent want to start a new product, and they create it in one night before presenting it to the board.

    Example output:

    # Panel 1
    description: a guy with blond hair wearing glasses, a guy with black hair wearing a hat, sitting at the office, with computers
    text:
    ```
    Vincent: I think Generative AI is the future of the company.
    Adrien: Let's create a new product with it.
    ```
    # Panel 2
    description: a guy with blond hair wearing glasses, a guy with black hair wearing a hat, working hard, with papers and notes scattered around
    text:
    ```
    Adrien: We need to finish this by morning.
    Vincent: Keep going, we can do it!
    ```
    # Panel 3
    description: a guy with blond hair wearing glasses, a guy with black hair wearing a hat, presenting their product, in a conference room, with a projector
    text:
    ```
    Vincent: Here's our new product!
    Adrien: We believe it will revolutionize the industry.
    ```
    # end

    Short Scenario:
    {scenario}

    Split the scenario into 12 parts, ensuring the characters remain consistent in description throughout all panels:
    """

    try:
        model = ChatOpenAI(model_name='gpt-4', openai_api_key=openai.api_key)
        human_message_prompt = HumanMessagePromptTemplate.from_template(template)
        chat_prompt = ChatPromptTemplate.from_messages([human_message_prompt])
        messages = chat_prompt.format_messages(scenario=scenario)
        result = model(messages)
        return extract_panel_info(result.content)
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

# Example usage

