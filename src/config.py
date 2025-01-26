import os

# Copy and paste your OpenAI API Key
openai_api_key = os.getenv("OPENAI_API_KEY")
# Put your name
key_owner = "benny"

maze_assets_loc = "assets"
env_matrix = f"{maze_assets_loc}/the_ville/matrix"
env_visuals = f"{maze_assets_loc}/the_ville/visuals"

fs_storage = "storage"
fs_temp_storage = "temp_storage"

collision_block_id = "32125"
use_openai = True
api_model = "gpt-4o"

# Verbose 
debug = False
