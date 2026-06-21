import argparse
import init, build, vendor
from log import logger as log


commands = { "init": init, "build": build, "vendor": vendor, }


def main():
    parser = argparse.ArgumentParser(
        description="Oh, Dog! Over-engineered static Html DOcument Generator with depending support.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    build_parser = subparsers.add_parser('build', help='Build project into HTML')
    build_parser.add_argument('project_dir', nargs='?', default='.', help="Path to project directory")
    build_parser.add_argument('--no-cache', action='store_true', help="Force re-download of all dependencies")
    
    init_parser = subparsers.add_parser('init', help='Initialize a new project')
    init_parser.add_argument('path', nargs='?', default='.', help="Directory to initialize")
    init_parser.add_argument('--from', dest='base_from', nargs='+', help="Dependencies to require")
    init_parser.add_argument('-f', '--force', action='store_true', help="Overwrite existing files")
    
    vendor_parser = subparsers.add_parser('vendor', help='Copy dependencies\' files into project')
    vendor_parser.add_argument('project_dir', nargs='?', default='.', help="Path to project directory")
    vendor_parser.add_argument('-f', '--force', action='store_true', help="Overwrite existing files")
    vendor_parser.add_argument('--no-cache', action='store_true', help="Force re-download of all bases")
    
    parser.set_defaults(command='build')
    
    args = parser.parse_args()
    
    if args.command not in commands.keys():
        log.error(
            f'unknown command: {args.command}',
            hint = f"Available: {', '.join(tuple(commands.keys()))}"
        )
    
    commands[args.command].main(args)

if __name__ == "__main__":
    main()
