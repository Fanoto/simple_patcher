import binascii
from typing import List, Optional, Dict, Any
from pathlib import Path
import shutil

import PySimpleGUI as sg
import yaml


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
        self.selected = False

    def __str__(self):
        return (
            f'Patch: \n'
            f' name: {self.name}\n'
            f' description: {self.description}\n'
            f' author: {self.author}\n'
            f' group: {self.group}\n'
            f' patch: {self.patch}'
        )


def apply_patches(orig_exe: str, new_exe: str, patches: List[Patch], err=print, info=print) -> bool:
    orig_exe = Path(orig_exe)
    new_exe = Path(new_exe)

    if not orig_exe.is_file():
        err('Unable to find original executable:', orig_exe)
        return False
    if new_exe.is_file() and orig_exe.samefile(new_exe):
        err('Please select different original and new executables')
        return False
    shutil.copy(orig_exe, new_exe)
    with open(new_exe, 'r+b') as f:
        for patch in patches:
            info(f'Applying "{patch.name}"...')
            for base_patch in patch.patch:
                f.seek(base_patch.offset)
                f.write(base_patch.bytestr)
    return True


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
