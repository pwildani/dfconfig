#!/Library/Frameworks/Python.framework/Versions/2.6/bin/python2.6

"""
Dwarf Fortress config file representation.

A DF config file consists a set of tags in []'s.
Tags can have 0 or more colon separated arguments.

Text outside []'s is considered a comment and is ignored.

When an [OBJECT:<type>] tag is encountered, new instances of <type> will be
constructed from the next tags.

Typically, each <type> has a special tag indicating the start of a new
instance. This is usually, but not always, the same as the name of the type.
"""

from collections import defaultdict

class Error(Exception):
  pass


class FileLineError(Error):
  def __init__(self, filename, linenum, *args):
    self.filename = filename
    self.linenum = linenum
    Error.__init__(self, *args)


class TagError(FileLineError):
  def __init__(self, tag, message):
    self.tag = tag
    FileLineError.__init__(self, tag.filename, tag.start_line, message)


class InvalidTag(TagError):
  pass


class UnknownToplevelTag(TagError):
  pass

class ParseError(FileLineError):
  pass


class DuplicateDefinition(TagError):
  def __init__(self, preexisting, current):
    msg = '%s: defined both here and %s:%s' % (
        current.ObjectName(),
        preexisting.typetag.filename,
        preexisting.typetag.start_line)
    TagError.__init__(self, current.typetag, msg)


class Registry(dict):
  """Map name -> object, with an @decl."""
  def __init__(self, name):
    self.name = name

  def __call__(self, name=None):
    def _declaration(impl):
      if name is None:
        thename = impl.__name__
      else:
        thename = name
      self[thename] = impl
      return impl
    _declaration.__name__ = self.name
    return _declaration

TAG = Registry('tag')

DF_OBJECT = Registry('df_object')


class Tag:
  """A [TAG:WITH:ARGS]."""
  MAX_TOKENS = None
  MIN_TOKENS = None
  def __init__(self, tokens):
    self.tokens = tokens
    self.filename = None
    self.start_line = None
    self.comment = '\n'

  def Validate(self):
    if self.MAX_TOKENS and len(self.tokens) > self.MAX_TOKENS:
      raise InvalidTag(self, 'too many arguments.')
    if self.MIN_TOKENS and len(self.tokens) < self.MIN_TOKENS:
      raise InvalidTag(self, 'too few arguments.')

  def TagName(self):
    return self.tokens[0]

  def Render(self):
    if self.comment:
      yield self.comment
    yield '[%s]' % (':'.join(self.tokens))

  def __str__(self):
    return '[%s]' % (':'.join(self.tokens))


def NewTag(tokens):
  name = tokens[0]
  if name in TAG:
    return TAG[name](tokens)
  return Tag(tokens)


class DFObject:
  """A CREATURE or MATGLOSS, etc."""
  def __init__(self, typetag):
    self.tags = []
    self.comment = None
    self.typetag = typetag

  def ObjectType(self):
    return self.typetag.ObjectType()

  def ObjectName(self):
    return self.typetag.ObjectIdentifier()

  def AppendTag(self, tag):
    self.tags.append(tag)
    # TODO: subsections, like ATTACK and BP

  def __str__(self):
    return ''.join(self.typetag.Render()) + ' (+ %d tags)' % len(self.tags)

  def Render(self):
    if self.comment:
      yield self.comment
    for tag in [self.typetag] + self.tags:
    # TODO: Reindent along sections. For now, just preserve the whitespace
      for line in tag.Render():
        yield line




class DFConfig:

  def __init__(self, name):
    # type -> subtype -> instance
    self.objects = defaultdict(lambda: defaultdict(dict))

    # filename -> ordered tags + comments + objects
    self.toplevel = {}

  def Render(self, filename):
    for elt in self.toplevel[filename]:
      for line in elt.Render():
        yield line

  def __str__(self):
    return ''.join(''.join(self.Render(f)) for f in self.toplevel)

  def ImportFile(self, filename, stream):
    current_def = None
    current_type = None
    current_typename = None
    self.toplevel[filename] = file_index = []

    for tag in TagStream(filename, stream):
      if isinstance(tag, Tag):
        if isinstance(tag, OBJECT):
          # Switch types
          current_type = DF_OBJECT[tag.ObjectType()]
          current_typename = tag.ObjectType()
          current_def = None
          file_index.append(tag)

        elif current_type and isinstance(tag, current_type.START_TAG):
          # New object
          current_def = current_type(tag)
          type = current_typename
          subtype = tag.ObjectType()
          name = tag.ObjectIdentifier()
          if name in self.objects[type][subtype]:
            raise DuplicateDefinition(self.objects[type][subtype][name],
                                      current_def)
          else:
            self.objects[type][subtype][name] = current_def
          file_index.append(current_def)

        elif current_def:
          # Feed the current object
          current_def.AppendTag(tag)

        else:
          # Unrecognized tag
          raise UnknownToplevelTag(tag, 'Unknown top-level tag')
          
      else:
        # Not a tag
        file_index.append(tag)
    
class ToplevelComment:
  def __init__(self, text):
    self.text = text

  def Render(self):
    yield self.text



def TagStream(filename, input):

  # A half assed state machine. I'm quite sure this is very slow.
  class Parser:

    def __init__(self):
      self.counts = defaultdict(lambda: 0)
      self.tag_start = None
      self.comment = []
      self.tag = []

      self.state = self.STATE_TOPLEVEL()

    def CommentChar(self, c):
      #print 'comment_char:', repr(c), self.tag
      self.comment.append(c)
      return []

    def TagChar(self, c):
      #print 'tag_char:', repr(c), self.tag
      self.tag[-1] += c
      return []

    def TagEnd(self, c):
      #print 'end_tag:', repr(c), self.tag
      tag = NewTag(list(self.tag))
      tag.comment = ''.join(self.comment)
      tag.start_line = self.tag_start
      tag.filename = filename
      self.tag = None
      self.comment = []
      self.state = self.STATE_TOPLEVEL()
      return [tag]

    def TagStart(self, c):
      #print 'start_tag:', repr(c), self.tag
      self.tag = ['']
      self.tag_start = self.CurrentLine()
      self.state = self.STATE_TAG()
      return []

    def TagSection(self, c):
      #print 'tag_section:', repr(c), self.tag
      self.tag.append('')
      return []

    def UnexpectedStartTag(self, c):
      raise ParseError(filename, self.tag_start,
                       'Tag is not closed before next [')

    def STATE_TAG(self):
      if not hasattr(self, '_state_tag'):
        tc = self.TagChar
        self._state_tag =  defaultdict(lambda: tc, {
            ']': self.TagEnd,
            ':': self.TagSection,
            '[': self.UnexpectedStartTag,
        })
      return self._state_tag

    def STATE_TOPLEVEL(self):
      if not hasattr(self, '_state_toplevel'):
        cc = self.CommentChar
        self._state_toplevel =  defaultdict(lambda: cc, {
            '[': self.TagStart,
        })
      return self._state_toplevel

    def Parse(self, input):
      char = input.read(1)
      while char:
        #print 'input: ', repr(char)
        self.counts[char] += 1
        results = self.state[char](char)
        for tag in results:
          #print "TAG: ", tag
          yield tag
        char = input.read(1)

      if self.tag:
        raise ParseError(filename, parser.tag_start,
                         'Unclosed tag: %s' % (self.tag,))

      if self.comment:
        yield ToplevelComment(''.join(self.comment))

    def CurrentLine(self):
     return self.counts['\n'] + 1

  parser = Parser()
  for tag in parser.Parse(input):
    yield tag


# The typical behavior for new instances.
class ObjectStartTag(Tag):
  MAX_TOKENS = 2
  MIN_TOKENS = 2
  def ObjectType(self):
    return self.tokens[0]

  def ObjectIdentifier(self):
    return self.tokens[1]

# ==============================================================================
# Now we have all of the special cases and inconsistencies:

# Bootstrap the OBJECT mode switch tag.
@TAG()
class OBJECT(Tag):
  def __init__(self, tokens):
    Tag.__init__(self, tokens)

    # Generic OBJECT == TAG case.
    if self.ObjectType() not in DF_OBJECT:
      self.DeclareGenericObjectType(self.ObjectType())
  
  def ObjectType(self):
    return self.tokens[1]

  def DeclareGenericObjectType(self, objectname):

    @DF_OBJECT(name=objectname)
    class _Object(DFObject):

      @TAG(name=objectname)
      class START_TAG(ObjectStartTag):
        MAX_TOKENS = 2
        MIN_TOKENS = 2
        def ObjectType(self):
          return self.tokens[0]

        def ObjectIdentifier(self):
          return self.tokens[1]
      START_TAG.__name__ = objectname

    _Object.__name__ = objectname


# DESCRIPTOR objects start with the COLOR or SHAPE tags
@TAG()
class COLOR(ObjectStartTag): pass

@TAG()
class SHAPE(ObjectStartTag): pass

@DF_OBJECT()
class DESCRIPTOR(DFObject):
  START_TAG = (COLOR, SHAPE)

# ITEM objecs start with the ITEM_* tags

@TAG()
class ITEM_AMMO(ObjectStartTag): pass

@TAG()
class ITEM_ARMOR(ObjectStartTag): pass

@TAG()
class ITEM_FOOD(ObjectStartTag): pass

@TAG()
class ITEM_GLOVES(ObjectStartTag): pass

@TAG()
class ITEM_HELM(ObjectStartTag): pass

@TAG()
class ITEM_INSTRUMENT(ObjectStartTag): pass

@TAG()
class ITEM_PANTS(ObjectStartTag): pass

@TAG()
class ITEM_SHIELD(ObjectStartTag): pass

@TAG()
class ITEM_SHOES(ObjectStartTag): pass

@TAG()
class ITEM_SIEGEAMMO(ObjectStartTag): pass

@TAG()
class ITEM_TOY(ObjectStartTag): pass

@TAG()
class ITEM_TRAPCOMP(ObjectStartTag): pass

@TAG()
class ITEM_WEAPON(ObjectStartTag): pass

@DF_OBJECT()
class ITEM(DFObject):
  START_TAG = (ITEM_AMMO, ITEM_ARMOR, ITEM_FOOD, ITEM_GLOVES,
               ITEM_HELM, ITEM_INSTRUMENT, ITEM_PANTS, ITEM_SHIELD,
               ITEM_SHOES, ITEM_SIEGEAMMO, ITEM_TOY, ITEM_TRAPCOMP,
               ITEM_WEAPON)


# MATGLOSS objects start with the MATGLOSS_* tags

@TAG()
class MATGLOSS_METAL(ObjectStartTag): pass

@TAG()
class MATGLOSS_PLANT(ObjectStartTag): pass

@TAG()
class MATGLOSS_STONE(ObjectStartTag): pass

@TAG()
class MATGLOSS_WOOD(ObjectStartTag): pass

@DF_OBJECT()
class MATGLOSS(DFObject):
  START_TAG = (MATGLOSS_METAL, MATGLOSS_PLANT, MATGLOSS_STONE, MATGLOSS_WOOD)


# LANGUAGE objects start with TRANSLATION, SYMBOL, or WORD tags
@TAG()
class TRANSLATION(ObjectStartTag): pass

@TAG()
class SYMBOL(ObjectStartTag): pass

@TAG()
class WORD(ObjectStartTag): pass

@DF_OBJECT()
class LANGUAGE(DFObject):
  START_TAG = (TRANSLATION, SYMBOL, WORD)



# BODY startswith both BODY and BODYGLOSS
@TAG()
class BODY(ObjectStartTag): pass

@TAG()
class BODYGLOSS(ObjectStartTag): pass

@DF_OBJECT(name='BODY')
class BODY_object(DFObject):
  START_TAG = (BODY, BODYGLOSS)


if __name__ == '__main__':
  # Test driver code. This doesn't do anything particularly useful
  import sys
  cfg = DFConfig('the config')
  for filename in sys.argv[1:]:
    try:
      cfg.ImportFile(filename, open(filename, 'r'))
      print '%s: %d toplevel objects' % (filename, len(cfg.toplevel[filename]))
    except FileLineError, ex:
      print '%s:%s: %s' % (ex.filename, ex.linenum, ex)
    # print ''.join(cfg.Render(filename))

