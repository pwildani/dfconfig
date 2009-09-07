#!/usr/local/bin/python2.6

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


class DisallowedTag(TagError):
  def __init__(self, context, tag):
    TagError.__init__(self, tag, '%s: %s tag is not allowed here' % (
        context.typetag, tag.TagName()))


class DuplicateDefinition(TagError):
  def __init__(self, preexisting, current):
    msg = '%s: defined both here and %s:%s' % (
        current.ObjectName(),
        preexisting.typetag.filename,
        preexisting.typetag.start_line)
    TagError.__init__(self, current.typetag, msg)


class ParseError(FileLineError):
  pass


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

DF_OBJECT_REGISTRY = Registry('df_object')

def DF_OBJECT(name=None):
  """Declare a DF object type."""
  def _DF_OBJECT(target):
    target = EnsureSubclass(DFObject, target)
    DF_OBJECT_REGISTRY(name=name)(target)
    target._GrovelForImplicitDefinitions()
    return target
  return _DF_OBJECT



SYMBOL_TABLE = {}
def Symbol(val):
  return SYMBOL_TABLE.setdefault(val, val)

def ParseToken(token):
  for parser in (int, float, Symbol):
    try:
      value = parser(token)
      return value
    except (ValueError, TypeError):
      pass
  return token


class Tag:
  """A [TAG:WITH:ARGS]."""
  MAX_TOKENS = None
  MIN_TOKENS = None
  def __init__(self, tokens):
    self.tokens = map(ParseToken, tokens)
    self.filename = None
    self.start_line = None
    self.comment = '\n'

  def Validate(self, config):
    if self.MAX_TOKENS and len(self.tokens) > self.MAX_TOKENS:
      raise InvalidTag(self, 'too many arguments.')

    if self.MIN_TOKENS and len(self.tokens) < self.MIN_TOKENS:
      raise InvalidTag(self, 'too few arguments.')
    
    # More specific tags could do things like check that their arguments are a
    # valid object in config, for instance.

  def TagName(self):
    return self.tokens[0]

  def Render(self):
     return '%s[%s]' % (self.comment, ':'.join(map(str, self.tokens)))

  def __str__(self):
    return '[%s]' % (':'.join(map(str, self.tokens)))


def NewTag(tokens):
  name = tokens[0]
  if name in TAG:
    return TAG[name](tokens)
  return Tag(tokens)


class DFObject:
  """A CREATURE or MATGLOSS, etc."""
  START_TAGS = ()
  SUBSECTIONS = ()
  SUBSECTION_TAGS = ()
  ALLOW_UNKNOWN_TAGS = True
  TAGS = ()

  def __init__(self, typetag):
    self.tags = []
    self.comment = None
    self.typetag = typetag

  def ObjectType(self):
    return self.typetag.ObjectType()

  def ObjectName(self):
    return self.typetag.ObjectIdentifier()

  def AppendTag(self, tag):
    if isinstance(tag, self.TAGS): # Useful to end subsections
      self.tags.append(tag)
    elif isinstance(tag, self.SUBSECTION_TAGS):
      self.tags.append(tag)
    elif self.tags and isinstance(self.tags[-1], self.SUBSECTIONS):
      self.tags[-1].AppendTag(tag)
      # TODO: Allow the subsection to reject the tag and fall back on the
      # unknown tag mechanism below.
    elif self.ALLOW_UNKNOWN_TAGS:
      self.tags.append(tag)
    else:
      raise DisallowedTag(self, tag)

  def __str__(self):
    return '%s (+ %d tags)' % (self.typetag, len(self.tags))

  def Render(self):
    out = []
    if self.comment:
      out.append(self.comment)
    for tag in [self.typetag] + self.tags:
      # TODO: Reindent along sections. For now, just preserve the whitespace
      out.append(tag.Render())
    return ''.join(out)

  def Validate(self, config):
    for tag in self.tags:
      tag.Validate(config)

  @classmethod
  def _GrovelForImplicitDefinitions(cls):
    start_tags = []
    subsections = []
    tags = []
    for field, value in cls.__dict__.iteritems():
      if isinstance(value, types.ClassType):
        if issubclass(value, ObjectStartTag):
          start_tags.append(value)
        elif issubclass(value, Subsection):
          subsections.append(value)
        elif issubclass(value, Tag):
          tags.append(value)

    if start_tags and 'START_TAG' not in cls.__dict__:
      cls.START_TAGS = tuple(start_tags)

    if subsections and 'SUBSECTIONS' not in cls.__dict__:
      cls.SUBSECTIONS = tuple(subsections)
      cls.SUBSECTION_TAGS = tuple(s.TAG for s in subsections)

    if tags and 'TAGS' not in cls.__dict__:
      cls.TAGS = tuple(tags)
      # Maybe set ALLOW_UNKNOWN_TAGS = False, too?

class Subsection(DFObject):
  pass


def EnsureSubclass(superclass, target):
  # Force target to be a subclass of superclass
  if not issubclass(target, superclass):
    bases = list(target.__bases__)
    bases.append(superclass)
    target.__bases__ = tuple(bases)
    assert issubclass(target, superclass)
    # Alternate: rebuild the class with a different bases list:
    #target = type(target.__name__,
    #              tuple(list(target.__bases__) + [superclass, object]),
    #              dict(target.__dict__))
  return target
  

def SECTION(name=None):
  """Declare a subsection within an object."""
  def _SECTION(target):
    target = EnsureSubclass(Subsection, target)
    @START_TAG(name or target.__name__)
    class SectionTag: pass
    target.TAG = SectionTag
    target._GrovelForImplicitDefinitions()
    return target
  return _SECTION

def START_TAG(name=None):
  """Declare a start tag for this object."""
  def _START_TAG(target):
    target = TAG(name)(EnsureSubclass(ObjectStartTag, target))
    return target
  return _START_TAG


class DFConfig:
  """A dwarf fortress configuration set."""

  def __init__(self, name):
    # type -> subtype -> instance
    self.objects = defaultdict(lambda: defaultdict(dict))

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
    for tokens in self.toplevel.itervalues():
      for tag in tokens:
        tag.Validate(self)

  def ImportFile(self, filename):
    return self.ImportStream(filename, open(filename, 'r'))

  def ImportStream(self, filename, stream):
    current_def = None
    current_type = None
    current_typename = None
    self.toplevel[filename] = file_index = []

    for tag in TagStream(filename, stream):
      if isinstance(tag, Tag):
        if isinstance(tag, OBJECT):
          # Switch types
          current_type = DF_OBJECT_REGISTRY[tag.ObjectType()]
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
          print 'current_type', current_type
          print 'current_type.START', current_type.START_TAGS

          raise UnknownToplevelTag(tag, 'Unknown top-level tag: %s' % tag)
          
      else:
        # Not a tag
        file_index.append(tag)
    
class ToplevelComment:
  def __init__(self, text):
    self.text = text

  def Render(self):
     return self.text

  def Validate(self, config):
    pass


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

    # Generic OBJECT == TAG
    if self.ObjectType() not in DF_OBJECT_REGISTRY:
      self.DeclareGenericObjectType(self.ObjectType())
  
  def ObjectType(self):
    return self.tokens[1]

  def DeclareGenericObjectType(self, objectname):

    @DF_OBJECT(name=objectname)
    class _Object(DFObject):

      @START_TAG(name=objectname)
      class StartTag:
        MAX_TOKENS = 2
        MIN_TOKENS = 2
        def ObjectType(self):
          return self.tokens[0]

        def ObjectIdentifier(self):
          return self.tokens[1]
      START_TAG.__name__ = objectname

    _Object.__name__ = objectname


# DESCRIPTOR objects start with the COLOR or SHAPE tags
@DF_OBJECT()
class DESCRIPTOR:
  @START_TAG()
  class COLOR: pass
  @START_TAG()
  class SHAPE: pass

# ITEM objects start with the ITEM_* tags
@DF_OBJECT()
class ITEM:
  @START_TAG()
  class ITEM_AMMO: pass

  @START_TAG()
  class ITEM_ARMOR: pass

  @START_TAG()
  class ITEM_FOOD: pass

  @START_TAG()
  class ITEM_GLOVES: pass

  @START_TAG()
  class ITEM_HELM: pass

  @START_TAG()
  class ITEM_INSTRUMENT: pass

  @START_TAG()
  class ITEM_PANTS: pass

  @START_TAG()
  class ITEM_SHIELD: pass

  @START_TAG()
  class ITEM_SHOES: pass

  @START_TAG()
  class ITEM_SIEGEAMMO: pass

  @START_TAG()
  class ITEM_TOY: pass

  @START_TAG()
  class ITEM_TRAPCOMP: pass

  @START_TAG()
  class ITEM_WEAPON: pass


# MATGLOSS objects start with the MATGLOSS_* tags
@DF_OBJECT()
class MATGLOSS:
  @START_TAG()
  class MATGLOSS_METAL: pass

  @START_TAG()
  class MATGLOSS_PLANT: pass

  @START_TAG()
  class MATGLOSS_STONE: pass

  @START_TAG()
  class MATGLOSS_WOOD: pass



# LANGUAGE objects start with TRANSLATION, SYMBOL, or WORD tags
@DF_OBJECT()
class LANGUAGE:
  @START_TAG()
  class TRANSLATION: pass

  @START_TAG()
  class SYMBOL: pass

  @START_TAG()
  class WORD: pass


# BODY startswith both BODY and BODYGLOSS
@DF_OBJECT()
class BODY:
  @START_TAG()
  class BODY: pass

  @START_TAG()
  class BODYGLOSS: pass

  @SECTION()
  class BP: pass


# TODO: [CREATURE][ATTACK]. Might be hard to do without listing all of the non-attack creature tags.

if __name__ == '__main__':
  # Test driver code. This doesn't do anything particularly useful, but you can
  # use it to check for duplicate definitions and basic syntax errors.
  import sys
  cfg = DFConfig('the config')
  for filename in sys.argv[1:]:
    try:
      cfg.ImportFile(filename)
      print '%s: %d toplevel objects' % (filename, len(cfg.toplevel[filename]))
    except FileLineError, ex:
      print '%s:%s: %s' % (ex.filename, ex.linenum, ex)
    except Error, ex:
      print '%s: %s: %s' % (filename, type(ex).__name__, ex)

    # Find typos in the render code. Needs to be eyeballed for a real test.
    cfg.Render(filename)

