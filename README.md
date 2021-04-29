# Simple Patcher
A simple patcher intended to read off patch files formatted as YAML.

## YAML Format
TODO

### Example
```yaml
name: Patch 1
author: Anonymous
group: default
description: This is the description text.
patch:
  - offset: 123ABC
    bytes: 90 90 EB FE

---

name: Patch 2
author: Anonymoose
group: extra
description: >
  This is an example of some longer, multi-line
  description text.
patch:
  - offset: DEADBEEF
    bytes: >
      AB CD EF 01 23 45 67 89 AB CD EF 01 02 03
      12
      34 56 78 9A
  - offset: 0102AB
    bytes: 90
```
