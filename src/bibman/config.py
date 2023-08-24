import yaml
import os
import shutil

path_to_config = f'{os.getenv("HOME")}/.config/bibman/config.yml'
if not os.path.exists(path_to_config):
    if not os.path.exists(f'{os.getenv("HOME")}/.config/bibman'):
        os.mkdir(f'{os.getenv("HOME")}/.config/bibman')

    current_path = os.path.dirname(os.path.abspath(__file__)) # This is your Project Root
    shutil.copy(os.path.join(current_path, 'config.yml'), path_to_config)
    print(f'A new default config file has been create at {path_to_config}')

with open(path_to_config, 'r') as file:
    config_dict = yaml.safe_load(file)

data_dir = os.path.expanduser(config_dict['data_dir']) # '~/bibman/data/'

