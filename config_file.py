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

  cfg = DFRawsConfig('foo')
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


class DFRawsConfig(object):
  """A dwarf fortress configuration set.

  Arguments:
    syntax: A syntax definition.
       Must have a NewToplevelTag method and an OBJECT tag.
  """

  def __init__(self, syntax):
    # type -> subtype -> instance
    self.objects = defaultdict(lambda: defaultdict(dict))
    self.syntax = syntax

    # filename -> ordered tags + comments + objects
    self.toplevel = {}

  def __getitem__(self, key):
    return self.objects[key]

  def RenderSingleFile(self, filename):
    out = []
    for elt in self.toplevel[filename]:
      out.append(elt.Render())
    return ''.join(out)

  def RenderAll():
    for _, objs in sorted(self.toplevel.items()):
      for obj in objs:
        for bit in obj.Render():
          yield bit

  def __str__(self):
    return ''.join(self.RenderAll())

  def Validate(self):
    for tokens in self.toplevel.values():
      for tag in tokens:
        tag.Validate(self)

  def ImportFile(self, filename):
    with open(filename, 'rb') as configfile:
      return self.ImportStream(filename, configfile)

  def ImportStream(self, filename, stream):
    current_object = None
    current_def = None
    current_type = None
    current_typename = None
    self.toplevel[filename] = file_index = []
    def TagFactory(tokens):
      tag = None
      if current_object:
        # Try a tag known to the current object set
        tag = current_object.NewTag(tokens)
      if not tag:
        # Then try a generic tag in this syntax
        tag = self.syntax.NewToplevelTag(tokens)
      if not tag:
        # Finally, fall back to a generic tag
        tag = df_syntax.Tag(tokens)
      return tag

    for tag in df_syntax.TagStream(filename, stream, TagFactory):
      if isinstance(tag, df_syntax.Tag):
        if isinstance(tag, self.syntax.OBJECT):
          # Switch types
          current_object = tag
          current_typename = tag.ObjectType()
          current_def = None
          file_index.append(tag)

        elif current_object and current_object.IsStartTag(tag):
          # New object
          if current_def:
            self.RecordToplevelDefinition([type, subtype, name],
                                          current_def)

          current_def = current_object.Instantiate(tag)
          type = current_typename
          subtype = tag.ObjectType()
          name = tag.ObjectIdentifier()

        elif current_def:
          # Feed the current object
          current_def.AppendTag(tag)
          # TODO(pwilson): allow it to reject the tag and forcibly end the
          # current definition

        else:
          # Unrecognized tag
          self.OnUnknownTag(tag)
          
      else:
        # Not a tag
        file_index.append(tag)
    if current_def:
      self.RecordToplevelDefinition([type, subtype, name],
                                    current_def)
    
  def OnDuplicateDefinition(self, path, old_definition, new_definition):
    raise errors.DuplicateDefinition(old_definition, new_definition)

  def OnUnknownTag(self, tag):
    raise errors.UnknownToplevelTag(tag, 'Unknown top-level tag: %s' % tag)
    
  def RecordToplevelDefinition(self, path, definition):
    type, subtype, name = path
    if name in self.objects[type][subtype]:
      self.OnDuplicateDefinition([type, subtype, name],
                                 self.objects[type][subtype][name],
                                 definition)
    else:
      self.objects[type][subtype][name] = definition
      self.toplevel[definition.SourceFilename()].append(definition)


if __name__ == '__main__':
  # Test driver code. This doesn't do anything particularly useful, but you can
  # use it to check for duplicate definitions and basic syntax errors.
  import sys
  import syntax_0_28_181_40d
  cfg = DFRawsConfig(syntax_0_28_181_40d)
  for filename in sys.argv[1:]:
    try:
      cfg.ImportFile(filename)
      print('%s: %d toplevel objects' % (filename, len(cfg.toplevel[filename])))
      cfg.Validate()
    except errors.FileLineError as ex:
      print('%s:%s: %s' % (ex.filename, ex.linenum, ex))
    except errors.Error as ex:
      print('%s: %s: %s' % (filename, type(ex).__name__, ex))

    # Find typos in the render code. Needs to be eyeballed for a real test.
    cfg.RenderSingleFile(filename)

