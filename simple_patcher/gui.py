from typing import Dict, List, Optional
import PySimpleGUI as sg

from .patch import Patch, apply_patches

sg.theme('Dark Grey')


def gui_error(msg: str):
    sg.popup_quick_message(msg, title='Error',
                           no_titlebar=False, non_blocking=False,
                           auto_close=False)


def gui_quickerror(*args, title: str = 'Error'):
    sg.popup_quick_message(*args, title=title, background_color=sg.theme_text_color(),
                           text_color=sg.theme_background_color())


def gui_popup_alt_message(msg: str):
    sg.popup_quick_message(msg, non_blocking=False, font=(sg.DEFAULT_FONT[0], 20),
                           background_color=sg.theme_text_color(), text_color=sg.theme_background_color())


class App(object):
    def __init__(self, patch_groups: Dict[str, List[Patch]],
                 orig_exe: Optional[str] = None,
                 new_exe: Optional[str] = None):
        self._patches: List[Patch] = []
        self.patch_groups = patch_groups
        self.apply_button = sg.Button('Apply')
        self.quit_button = sg.Button('Quit')
        self.orig_exe = sg.Input(default_text=orig_exe if orig_exe else '')
        self.new_exe = sg.Input(default_text=new_exe if new_exe else '')
        self.layout = []
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
            patch.cbox = sg.Checkbox(patch.name, size=(20, 1), default=patch.selected)
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
            gui_quickerror('Please select original executable')
            return False
        if new_exe == '':
            gui_quickerror('Please select new executable')
            return False
        selected = [patch for patch in self._patches if patch.cbox.get()]
        return apply_patches(orig_exe, new_exe, selected, err=gui_quickerror)

    def run(self):
        while True:
            event, values = self.window.read()
            if event == sg.WIN_CLOSED or event == self.quit_button.get_text():
                break
            if event == self.apply_button.get_text():
                if self.do_patch():
                    gui_popup_alt_message('Complete!')
