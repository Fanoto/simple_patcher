import argparse
from pathlib import Path
import sys

from .gui import gui_error, App
from .patch import parse_yamls, apply_patches

gui_enabled = True


def err_exit(msg: str) -> None:
    global gui_enabled
    if gui_enabled:
        gui_error(msg)
    else:
        print(msg, file=sys.stderr)
    sys.exit(1)


def main():
    default_patch_dir = './patches'

    parser = argparse.ArgumentParser(description='Simple binary patcher.')
    parser.add_argument('--auto', help='Will automatically run patcher using selected groups without starting GUI.', action='store_true')
    parser.add_argument('-p', '--patch_dir', help='Directory containing the patch files.', default=default_patch_dir)
    parser.add_argument('--orig_exe', help='Original executable to start from.', default=None)
    parser.add_argument('--new_exe', help='New executable to make.', default=None)
    parser.add_argument('--group', help='Add group to pre-selected patch list.', action='append')

    args = parser.parse_args()

    global gui_enabled
    gui_enabled = not args.auto

    if args.auto and (args.orig_exe is None or args.new_exe is None or args.group is None):
        err_exit('The "--auto" option requires "--orig_exe", "--new_exe", and "--group"')

    patch_dir = Path(args.patch_dir)

    if not patch_dir.is_dir():
        err_exit('Unable to find "patches" folder!')
    yamls = list(patch_dir.rglob('*.yaml'))
    if len(yamls) < 0:
        err_exit('Unable to find any patch files (.yaml) in patches folder!')

    patch_groups = parse_yamls(yamls)

    if args.group is not None:
        for group in args.group:
            if group not in patch_groups:
                err_exit(f'Specified group "{group}" was not found!')
            for patch in patch_groups[group]:
                patch.selected = True
                print(f'{patch.name} -> {patch.selected}')

    if args.auto:
        selected = []
        for group in patch_groups.values():
            selected.extend([patch for patch in group if patch.selected])
        successful = apply_patches(args.orig_exe, args.new_exe, selected)
        sys.exit(0 if successful else 1)

    app = App(patch_groups, orig_exe=args.orig_exe, new_exe=args.new_exe)
    app.run()


if __name__ == '__main__':
    main()
