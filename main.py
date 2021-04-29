import binascii
import yaml
import shutil
from pathlib import Path
import sys
from typing import List, Dict, Any, Optional
import PySimpleGUI as sg

sg.theme('Dark Grey')


class BasePatch(object):
    def __init__(self, offset: int, bytestr: bytes):
        self.offset = offset
        self.bytestr = bytestr

    def __str__(self) -> str:
        return f'{self.offset:08x}: {binascii.hexlify(self.bytestr, sep=" ")}'

    def __repr__(self) -> str:
        return f'{type(self)} - {self}'


class Patch(object):
    def __init__(self, name: str = '', description: str = '',
                 author: str = '', group: str = '',
                 patch: List[BasePatch] = []):
        self.name = name
        self.description = description
        self.author = author
        self.group = group
        self.patch = patch
        self.cbox: Optional[sg.Checkbox] = None

    def __str__(self):
        return (
            f'Patch: \n'
            f' name: {self.name}\n'
            f' description: {self.description}\n'
            f' author: {self.author}\n'
            f' group: {self.group}\n'
            f' patch: {self.patch}'
          )


def patch_from_yaml(raw_dict: Dict[str, Any]) -> Optional[Patch]:
    required_keys = ['name', 'author', 'group', 'description', 'patch']

    missing_keys = set(required_keys).difference(raw_dict.keys())
    if len(missing_keys) != 0:
        raise KeyError(f'Patch missing these fields: {missing_keys}')

    patches = raw_dict.pop('patch')
    if not isinstance(patches, list):
        raise TypeError('"patch" field expected to be a list')
    patch_objs = []
    for patch in patches:
        patch_objs.append(BasePatch(
            int(patch['offset'], 16),
            binascii.unhexlify(patch['bytes'].strip().replace(' ', ''))
        ))
    return Patch(**raw_dict, patch=patch_objs)


def parse_yamls(paths: List[Path]) -> Dict[str, List[Patch]]:
    individual_patches = []
    for path in paths:
        with open(path, 'r') as f:
            raw_read = yaml.load_all(f.read(), yaml.BaseLoader)
        individual_patches.extend([patch_from_yaml(raw_patch) for raw_patch in raw_read])
    patch_groups = {}

    for patch in individual_patches:
        if patch.group not in patch_groups:
            patch_groups[patch.group] = [patch]
        else:
            patch_groups[patch.group].append(patch)
    return patch_groups


def quick_error(*args, title: str = 'Error'):
    sg.popup_quick_message(*args, title=title, background_color=sg.theme_text_color(),
                           text_color=sg.theme_background_color())


class App(object):
    def __init__(self, patch_groups: Dict[str, List[Patch]]):
        self._patches: List[Patch] = []
        self.patch_groups = patch_groups
        self.apply_button = sg.Button('Apply')
        self.quit_button = sg.Button('Quit')
        self.orig_exe = sg.Input()
        self.new_exe = sg.Input()
        self.layout = []
        # Tends to be buggy from initial testing
        #self.layout.append([sg.Titlebar(title='Simple Patcher')])
        valid_filetypes = (('Executables', '*.exe'), ('All Files', '*.*'))
        self.layout.append([sg.Text('Original Executable', size=(20, 1)), self.orig_exe, sg.FileBrowse(file_types=valid_filetypes)])
        self.layout.append([sg.Text('New Executable', size=(20, 1)), self.new_exe, sg.FileSaveAs(file_types=valid_filetypes)])
        self.layout.append([self.build_tabgroup(patch_groups)])
        self.layout.append([self.apply_button, self.quit_button])
        self.window = sg.Window('Simple Patcher', layout=self.layout)

    def build_patchgroup_tab(self, group_name: str, patches: List[Patch]) -> sg.Tab:
        rows = []
        for patch in patches:
            self._patches.append(patch)
            patch.cbox = sg.Checkbox(patch.name, size=(20, 1))
            if len(rows) > 0:
                rows.append([sg.HorizontalSeparator()])
            rows.append(
                [patch.cbox, sg.Text(f'by {patch.author}', size=(20, 1)), sg.Text(patch.description, size=(50, None))])
        return sg.Tab(group_name, layout=rows)

    def build_tabgroup(self, patch_groups: Dict[str, List[Patch]]) -> sg.TabGroup:
        tabs = []
        for group_name, patches in patch_groups.items():
            tabs.append(self.build_patchgroup_tab(group_name, patches))
        return sg.TabGroup([tabs])

    def do_patch(self) -> bool:
        orig_exe = self.orig_exe.get()
        new_exe = self.new_exe.get()
        if orig_exe == '':
            quick_error('Please select original executable')
            return False
        if new_exe == '':
            quick_error('Please select new executable')
            return False
        orig_exe = Path(orig_exe)
        new_exe = Path(new_exe)

        if not orig_exe.is_file():
            quick_error('Unable to find original executable:', orig_exe)
            return False
        if new_exe.is_file() and orig_exe.samefile(new_exe):
            quick_error('Please select different original and new executables')
            return False
        selected = [patch for patch in self._patches if patch.cbox.get()]
        shutil.copy(orig_exe, new_exe)
        with open(new_exe, 'r+b') as f:
            for patch in selected:
                print(f'Applying "{patch.name}"...')
                for base_patch in patch.patch:
                    f.seek(base_patch.offset)
                    f.write(base_patch.bytestr)
        return True

    def run(self):
        while True:
            event, values = self.window.read()
            if event == sg.WIN_CLOSED or event == self.quit_button.get_text():
                break
            if event == self.apply_button.get_text():
                if self.do_patch():
                    sg.popup_quick_message('Complete!', non_blocking=False)


def main():
    patches_dir = Path('patches')
    if not patches_dir.is_dir():
        sg.popup_quick_message('Unable to find "patches" folder!', title='Error', no_titlebar=False, non_blocking=False, auto_close=False)
        sys.exit(1)
    yamls = list(patches_dir.rglob('*.yaml'))
    if len(yamls) < 0:
        sg.popup_quick_message('Unable to find any patch files (.yaml) in patches folder!', title='Error')
        sys.exit(1)

    patch_groups = parse_yamls(yamls)

    app = App(patch_groups)
    app.run()


if __name__ == '__main__':
    main()
