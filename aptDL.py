# THIS WHOLE PROJECT WAS PROBABLY MADE WITH HORRIBLE HORRIBLE CODING PRACTICES
# I AM AN IDIOT
# PLEASE CONSIDER NOT USING THIS CODE ANYWHERE ELSE
import argparse, json, os, time, posixpath, logging
from termcolor import cprint
from urllib.parse import urlparse
from debian_inspector import debcon
from modules.download import download
from modules.helper import remove_illegal_filename_characters
from modules.repo import DebianRepo, InstallerRepo

def repo_download(repo, args):
    package_count = len(repo.packages)
    unpurchased_packages = list()
    for index, package in enumerate(repo.packages):
        download_link = repo.get_dl_link(index)
        if package['package'] in unpurchased_packages:
            continue
        if download_link is None:
            logger.warning(f"({index+1}/{package_count}) Couldn't download {package['package']}")
            unpurchased_packages.append(package['package'])
            continue
        if not args.original_names:
            filename = remove_illegal_filename_characters(f"{package['package']}-{package['version']}{os.path.splitext(package['filename'])[1]}")
            destination = os.path.join(args.output, package['package'], filename)
        else:
            filename = remove_illegal_filename_characters(os.path.basename(package['filename']))
            destination = os.path.join(args.output, package['package'], filename)
        if not args.dont_skip_downloaded and os.path.isfile(destination):
            continue
        try:
            logger.info(f"Downloading package {package['package']}, version {package['version']}\nLink: {download_link}\nOutput file: {destination}")
            download(download_link, destination, f"({index+1}/{package_count})")
            time.sleep(args.cooldown)
        except ConnectionError as e:
            print(repr(e))

    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers(help='help for subcommand', dest='command')

    oneshot = subparser.add_parser('oneshot', help='Archive a single repo')
    repotype = oneshot.add_mutually_exclusive_group()
    oneshot.add_argument('url', metavar='URL', nargs='+', type=str, 
        help="""URL of the repo to download from.
                If archiving a dist repo, specify the suite after the URL, separated by a whitespace character.
                Example: https://apt.procurs.us iphoneos-arm64/1700""")
    oneshot.add_argument('-o', '--output', metavar='DIR', default='./', type=str, help='Folder to download archived packages to')
    oneshot.add_argument('--auth', '--authentication', metavar='JSONFILE', type=str, 
        help="""The path to JSON file containing authentication information, which is required to archive paid packages.
                You can build it yourself, or run token_helper.py to dump the token.""")
    oneshot.add_argument('--cooldown', type=int, default=5, help='Cooldown time between each package download, default is 5 seconds.')
    oneshot.add_argument('--dont-skip-downloaded', action='store_true', help='Overwrites packages that already exists in the destination directory')
    oneshot.add_argument('--original-names', action='store_true', 
        help="""Only change the filename when necessary (invalid characters etc)
                Default is to change filenames to PACKAGE-VERSION.ext""")
    oneshot.add_argument('-v', '--verbose', action="store_const", dest="loglevel", const=logging.INFO, default=logging.WARNING, help='be verbose')
    repotype.add_argument('-i', '--installer', action='store_true', help='Specify the repo as an Installer repo')

    input_file = subparser.add_parser('sources', help="""Archive all repos inside a Deb822-formatted repo list (such as sileo.sources)""")
    input_file.add_argument('sources', metavar='FILE', nargs='+', type=str, help="""*.sources files to read from, must have a Deb822 control file format""")
    input_file.add_argument('-o', '--output', metavar='DIR', type=str, help='Folder to download archived packages to. A folder with the repo\'s hostname is created for each repo.')
    input_file.add_argument('--auth', '--authentication', metavar='JSONFILE', type=str, 
        help="""The path to a directory with JSON files containing authentication information, which is required to archive paid packages.
                You can build it yourself, or run token_helper.py to dump the token.
                Filenames must follow the format REPO_HOSTNAME.json, for example repo.chariz.com.json""")
    input_file.add_argument('--cooldown', type=int, default=5, help='Cooldown time between each package download, default is 5 seconds.')
    input_file.add_argument('--dont-skip-downloaded', action='store_true', help='Overwrites packages that already exists in the destination directory')
    input_file.add_argument('--original-names', action='store_true', 
        help="""Only change the filename when necessary (invalid characters etc)
                Default is to change filenames to PACKAGE-VERSION.ext""")
    input_file.add_argument('-v', '--verbose', action="store_const", dest="loglevel", const=logging.INFO, default=logging.WARNING, help='be verbose')

    args = parser.parse_args()
    
    logging.basicConfig(level=args.loglevel, format="%(asctime)s - %(levelname)s - %(message)s")
    logger = logging.getLogger(__name__)

    match args.command:
        case 'oneshot':
            if args.installer:
                repo = InstallerRepo(args.url[0])
            else:
                args.url = [args.url[0], './'] if len(args.url) == 1 else args.url
                if args.auth and os.path.isfile(args.auth):
                    with open(args.auth, 'r') as file:
                        repo = DebianRepo(args.url[0], suites=args.url[1], auth=json.load(file))
                else:
                    repo = DebianRepo(args.url[0], suites=args.url[1])
            repo_download(repo, args)
        case 'sources':
            args.apt = True
            sources_list = list()
            output_dir = args.output
            for sources_filename in args.sources:
                sources_list += list(debcon.get_paragraphs_data_from_file(sources_filename))
            for source in sources_list:
                cprint(f"Downloading from {source['uris']} {source['suites']}", 'blue')
                repo_netloc = urlparse(source['uris']).netloc
                auth = None
                authfile = posixpath.join(args.auth, f"{repo_netloc}.json")
                logger.debug(f"Looking for authentication data in {authfile}")
                if os.path.isfile(authfile):
                    logger.info(f"Using authentication data from {authfile}")
                    with open(authfile, 'r') as file:
                        auth=json.load(file)
                repo = DebianRepo(source['uris'], suites=source['suites'], auth=(auth if auth else None))
                args.output = os.path.abspath(posixpath.join(output_dir, repo_netloc, source['suites']))
                repo_download(repo, args)