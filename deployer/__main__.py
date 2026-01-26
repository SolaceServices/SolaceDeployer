import os
from deployer.utils import parse_arguments

def main():
    from deployer import deploy

    arguments = parse_arguments()

    if arguments.proxy == 'false':
        # below settings are only overridden for this session
        os.environ.pop('http_proxy', None)
        os.environ.pop('HTTP_PROXY', None)
        os.environ.pop('https_proxy', None)
        os.environ.pop('HTTPS_PROXY', None)
        os.environ["no_proxy"] = "*"
        os.environ["NO_PROXY"] = "*"
    deploy.run(arguments)

if __name__ == "__main__":
    main()
