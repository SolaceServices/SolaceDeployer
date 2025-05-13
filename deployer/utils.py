import os
import sys
import argparse
import logging
import json

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
    parser.add_argument("--log", type=str, help="Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL", default="INFO")
    return parser.parse_args()

def show_help(app_name='deploy'):
    logging.info(f"{app_name} --mode=[deploymode] --target=[environment] [--appl=[applicationName]] [--action=[action]] [--log=[level]]")
    logging.info(f"     --mode: deployment mode, one of [configPush, semp] (required)")
    logging.info(f"     --target: target environment to execute the action on [one of tst,acc,prd]")
    logging.info(f'     --appl: JSON string of domainnames and their applications to handle. Example: \'[{{"domain1":["appl1","appl2"]}}]\'')
    logging.info(f"     --action: Action, one of [deploy, undeploy] (optional, default 'deploy'")
    logging.info(f"     --log: Set the logging level [DEBUG, INFO, WARNING, ERROR, CRITICAL] (optional, default 'INFO'")
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

