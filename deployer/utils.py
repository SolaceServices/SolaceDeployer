import os
import sys
import argparse
import logging
import json

from datetime import date
from pathlib import Path

class ConfigLoader:
    def __init__(self, config_dir='config'):
        self.config_dir = config_dir

    def load_config(self, env=None):
        env = env or os.getenv("APP_ENV", "dev")  # Defaults to dev
        config_file = os.path.join(self.config_dir, f"{ env }.json")

        try:
            with open(config_file,"r" ) as file:
                return json.load(file)
        except FileNotFoundError:
            raise Exception(f"Configuration file { config_file } not found!")
        except json.JSONDecodeError:
            raise Exception(f"Error parsing the configuration file { config_file }!")

def parse_arguments():
    parser = argparse.ArgumentParser(description="Process some parameters")
    parser.add_argument("--mode", type=str, help="deployment mode, one of [configPush, semp", default=None)
    parser.add_argument("--target", type=str, help="target environment to execute the action on [one of tst,acc,prd]", default=None)
    parser.add_argument("--appl", type=json.loads, required=False, help='JSON string of domainnames and their applications to handle. Example: \'[{{"domain1":["appl1","appl2"]}}]\'', default=None)
    parser.add_argument("--action", type=str, help="Action, one of [deploy, undeploy]", default="deploy")
    parser.add_argument("--log", type=str, help="Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)", default="INFO")
    parser.add_argument("--proxy", type=str, help="Enable usage of proxy ()true, false", default="false")
    return parser.parse_args()

def show_help(app_name='deploy'):
    logging.info(f"{app_name} --mode=[deploymode] --target=[environment] [--appl=[applicationName]] [--action=[action]] [--log=[level]]")
    logging.info(f"     --mode: deployment mode, one of [configPush, semp] (required)")
    logging.info(f"     --target: target environment to execute the action on [one of tst,acc,prd]")
    logging.info(f'     --appl: JSON string of domainnames and their applications to handle. Example: \'[{{"domain1":["appl1","appl2"]}}]\'')
    logging.info(f"     --action: Action, one of [deploy, undeploy] (optional, default 'deploy'")
    logging.info(f"     --log: Set the logging level [DEBUG, INFO, WARNING, ERROR, CRITICAL] (optional, default 'INFO'")
    logging.info(f"     --proxy: Enable usage of proxy [true, false] (optional, default 'false'")
    exit(1)

def setup_logging(log_level):
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)]
    )

def load_config(file_path):
    try:
        with open(file_path, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        logging.error(f"Error: Config file '{file_path}' not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        logging.error(f"Error: Invalid JSON format in file '{file_path}'.")
        sys.exit(1)

def preview_exists(environment_name, domain_name, application_name, version_name, state):
    file_path = Path(f"./store/{environment_name}/{domain_name}/{application_name}/{version_name}/preview-{state}.json")
    return file_path.exists()

def get_preview(environment_name, domain_name, application_name, version_name, state):
    file_path = Path(f"./store/{environment_name}/{domain_name}/{application_name}/{version_name}/preview-{state}.json")
    if file_path.exists() and file_path.is_file():
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    else:
        raise Exception(f"File {file_path} does not exist or is not a file")

def store_preview(preview, environment_name, domain_name, application_name, version_name, state):
    logging.info(f"Store preview for { environment_name }/{ domain_name }/{ application_name }/{ version_name }/preview-{ state }.json")
    file_path = f"./store/{ environment_name }/{ domain_name }/{ application_name }/{ version_name }/preview-{ state }.json"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w') as file:
        json.dump(preview, file, indent=2)


