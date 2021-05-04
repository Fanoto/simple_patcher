from simple_patcher.gui import sg, gui_quickerror, gui_popup_alt_message
from pathlib import Path
import argparse
import yaml
from typing import Optional, Dict, List, Tuple


def gen_patch(orig_exe: str, new_exe: str, patch_file: str,
              name: str, author: str, group: str, descr: str,
              err=gui_quickerror):
    orig_exe = Path(orig_exe)
    new_exe = Path(new_exe)
    patch_file = Path(patch_file)

    if not orig_exe.is_file():
        err('Unable to find original executable:', orig_exe)
        return False
    if not new_exe.is_file():
        err('Unable to find new executable:', new_exe)
        return False
    if new_exe.is_file() and orig_exe.samefile(new_exe):
        err('Please select different original and new executables')
        return False
    if orig_exe.stat().st_size > new_exe.stat().st_size:
        err('Original executable is larger than new executable, truncation not yet supported!')
        return False
    if patch_file.exists() and not patch_file.is_file():
        err("Patch file exists, but doesn't appear to be a file?")
        return False

    patches: List[Tuple[int, bytearray]] = []
    all_diff_offsets = []
    bufsz = 4096

    # Assertion here that new_exe is larger or equal to orig_exe in size.
    # Potential race between point of `stat` and points of `read`.
    with open(orig_exe, 'rb') as orig_f, open(new_exe, 'rb') as new_f:
        while True:
            offset = new_f.tell()
            orig_buf = orig_f.read(bufsz)
            new_buf = new_f.read(bufsz)
            if len(orig_buf) == 0 and len(new_buf) == 0:
                break
            if orig_buf == new_buf:
                continue
            if len(orig_buf) != bufsz:
                orig_buf = list(orig_buf) + [None] * (bufsz - len(orig_buf))
            if len(new_buf) != bufsz:
                new_buf = list(new_buf) + [None] * (bufsz - len(new_buf))
            # Buffers don't match, so there is at least one diff
            for i in range(0, bufsz):
                if orig_buf[i] != new_buf[i]:
                    diff_offset = offset + i
                    diff_byte = new_buf[i]
                    all_diff_offsets.append(diff_offset)
                    if (diff_offset - 1) in all_diff_offsets:
                        # If our immediately previous offset is in the diff list, append
                        # to the ongoing bytearray
                        patches[-1][1].append(diff_byte)
                    else:
                        barray = bytearray()
                        barray.append(diff_byte)
                        patches.append((diff_offset, barray))
    formatted_patches = [dict(
        offset=f'{offset:08X}',
        bytes=' '.join([f'{b:02X}' for b in barray])
    ) for offset, barray in patches]
    del patches
    yaml_dict = dict(
        name=name,
        author=author,
        group=group,
        description=descr,
        patch=formatted_patches
    )
    with open(patch_file, 'a') as f:
        # Prepend newline
        f.write('\n')
        yaml.dump(yaml_dict, stream=f, explicit_start=True, default_flow_style=False, sort_keys=False)
    return True


class App(object):
    def __init__(self, orig_exe: str = '', new_exe: str = '',
                 patch: str = '', name: str = '', author: str = '',
                 group: str = '', descr: str = ''):
        self.gen_button = sg.Button('Generate')
        self.quit_button = sg.Button('Quit')
        self.orig_exe = sg.Input(default_text=orig_exe)
        self.new_exe = sg.Input(default_text=new_exe)
        self.patch_file = sg.Input(default_text=patch)
        self.name_field = sg.Input(default_text=name)
        self.author_field = sg.Input(default_text=author)
        self.group_field = sg.Input(default_text=group)
        self.descr_field = sg.Multiline(default_text=descr)

        self.layout = []
        binary_filetypes = (('Executables', '*.exe'), ('All Files', '*.*'))
        patch_filetypes = (('YAML', '*.yaml'), )
        self.layout.append([sg.Text('Original Executable', size=(20, 1)),
                            self.orig_exe,
                            sg.FileBrowse(file_types=binary_filetypes)])
        self.layout.append([sg.Text('New Executable', size=(20, 1)),
                            self.new_exe,
                            sg.FileBrowse(file_types=binary_filetypes)])
        self.layout.append([sg.Text('Patch File', size=(20, 1)),
                            self.patch_file,
                            sg.SaveAs(file_types=patch_filetypes)])
        self.layout.append([sg.HorizontalSeparator()])
        font = sg.DEFAULT_FONT
        self.layout.append([sg.Text('Patch Fields', font=(font[0], int(font[1] * 1.5)))])
        self.layout.append([sg.Text('Name', size=(20, 1), justification='right'),
                            self.name_field])
        self.layout.append([sg.Text('Author', size=(20, 1), justification='right'),
                            self.author_field])
        self.layout.append([sg.Text('Group', size=(20, 1), justification='right'),
                            self.group_field])
        self.layout.append([sg.Text('Description', size=(20, 1), justification='right'),
                            self.descr_field])
        self.layout.append([self.gen_button, self.quit_button])
        self.window = sg.Window('Patch Generator', layout=self.layout)

    def do_patch_gen(self) -> bool:
        orig_exe = self.orig_exe.get()
        new_exe = self.new_exe.get()
        patch_file = self.patch_file.get()
        name = self.name_field.get()
        author = self.author_field.get()
        group = self.group_field.get()
        descr = self.descr_field.get().strip()
        if orig_exe == '':
            gui_quickerror('Please select original executable')
            return False
        if new_exe == '':
            gui_quickerror('Please select new executable')
            return False
        if patch_file == '':
            gui_quickerror('Please provide a patch file')
            return False
        if name == '':
            gui_quickerror('Please provide a name')
            return False
        if author == '':
            gui_quickerror('Please provide an author')
            return False
        if group == '':
            gui_quickerror('Please provide a group')
            return False
        if descr == '':
            gui_quickerror('Please provide a description')
            return False

        return gen_patch(orig_exe, new_exe, patch_file,
                         name, author, group, descr)

    def run(self):
        while True:
            event, values = self.window.read()
            if event == sg.WIN_CLOSED or event == self.quit_button.get_text():
                break
            if event == self.gen_button.get_text():
                if self.do_patch_gen():
                    gui_popup_alt_message('Complete!')


def main():
    parser = argparse.ArgumentParser(description='Patch generator.')
    parser.add_argument('-o', '--orig_exe', help='Original executable.')
    parser.add_argument('-n', '--new_exe', help='New executable.')
    parser.add_argument('-p', '--patch',
                        help='Where to play patch file.',
                        default='patch.yaml')
    parser.add_argument('--name', help='The name of the patch.',
                        default='PatchName')
    parser.add_argument('--author', help='The author of the patch.',
                        default='Anonymous')
    parser.add_argument('--group',
                        help='The group the patch belongs to.',
                        default='custom')
    parser.add_argument('--description',
                        help='Description of the patch.',
                        default='Changes some bytes.')

    args = parser.parse_args()

    orig_exe = args.orig_exe
    if orig_exe is None:
        orig_exe = ''
    new_exe = args.new_exe
    if new_exe is None:
        new_exe = ''
    patch = args.patch
    if patch is None:
        patch = ''

    app = App(orig_exe=orig_exe, new_exe=new_exe, patch=patch,
              name=args.name, author=args.author, group=args.group,
              descr=args.description)
    app.run()


if __name__ == '__main__':
    main()
