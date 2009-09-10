#!/usr/local/bin/python3

"""
Dwarf Fortress config file representation.

A DF config file consists a set of tags in []'s.
Tags can have 0 or more colon separated arguments.

Text outside []'s is considered a comment and is ignored.

When an [OBJECT:<type>] tag is encountered, new instances of <type> will be
constructed from the next tags.

Typically, each <type> has a special tag indicating the start of a new
instance. This is usually, but not always, the same as the name of the type.


API Example:

  cfg = DFConfig('foo')
  cfg.ImportFile('raw/objects/reaction_standard.txt')
  #       OBJECT      START TAG    NAME
  r = cfg['REACTION']['REACTION']['BITUMINOUS_COAL_TO_COKE']
  r.AppendTag(Tag(['PRODUCT', 30, 1, 'BAR', 'NO_SUBTYPE', 'ASH', 'NO_SUBTYPE']))

  open('new/reaction_plus_ash.txt', 'w').write(
      cfg.Render('raw/objects/reaction_standard.txt'))
"""

from collections import defaultdict
import types

import util
import df_syntax
import errors


class DFConfig(object):
  """A dwarf fortress configuration set.

  Arguments:
    syntax: A DFConfigConfigSyntax*.
  """

  def __init__(self, syntax):
    # type -> subtype -> instance
    self.objects = defaultdict(lambda: defaultdict(dict))
    self.syntax = syntax

    # filename -> ordered tags + comments + objects
    self.toplevel = {}

  def __getitem__(self, key):
    return self.objects[key]

  def Render(self, filename):
    out = []
    for elt in self.toplevel[filename]:
      out.append(elt.Render())
    return ''.join(out)

  def __str__(self):
    return ''.join(self.Render(f) for f in self.toplevel)

  def Validate(self):
    for tokens in self.toplevel.values():
      for tag in tokens:
        tag.Validate(self)

  def ImportFile(self, filename):
    return self.ImportStream(filename, open(filename, 'r'))

  def ImportStream(self, filename, stream):
    current_def = None
    current_type = None
    current_typename = None
    self.toplevel[filename] = file_index = []

    for tag in df_syntax.TagStream(filename, stream, self.syntax.NewTag):
      if isinstance(tag, df_syntax.Tag):
        if isinstance(tag, self.syntax.OBJECT):
          # Switch types
          current_type = self.syntax.GetObjectType(tag.ObjectType())
          current_typename = tag.ObjectType()
          current_def = None
          file_index.append(tag)

        elif current_type and isinstance(tag, current_type.START_TAGS):
          # New object
          current_def = current_type(tag)
          type = current_typename
          subtype = tag.ObjectType()
          name = tag.ObjectIdentifier()
          if name in self.objects[type][subtype]:
            raise errors.DuplicateDefinition(self.objects[type][subtype][name],
                                      current_def)
          else:
            self.objects[type][subtype][name] = current_def
          file_index.append(current_def)

        elif current_def:
          # Feed the current object
          current_def.AppendTag(tag)

        else:
          # Unrecognized tag
          print('current_type', current_type)
          print('current_type.START', current_type.START_TAGS)

          raise errors.UnknownToplevelTag(tag, 'Unknown top-level tag: %s' % tag)
          
      else:
        # Not a tag
        file_index.append(tag)
    

if __name__ == '__main__':
  # Test driver code. This doesn't do anything particularly useful, but you can
  # use it to check for duplicate definitions and basic syntax errors.
  import sys
  import syntax_0_28_181_40d
  cfg = DFConfig(syntax_0_28_181_40d)
  for filename in sys.argv[1:]:
    try:
      cfg.ImportFile(filename)
      print('%s: %d toplevel objects' % (filename, len(cfg.toplevel[filename])))
    except errors.FileLineError as ex:
      print('%s:%s: %s' % (ex.filename, ex.linenum, ex))
    except errors.Error as ex:
      print('%s: %s: %s' % (filename, type(ex).__name__, ex))

    # Find typos in the render code. Needs to be eyeballed for a real test.
    cfg.Render(filename)

