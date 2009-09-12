"""Tools to for the basic bits of of DF syntax. 

Tags and their organization into objects.
"""
from collections import defaultdict
import util
import errors

def ParseToken(token):
  for parser in (int, float, util.Symbol):
    try:
      value = parser(token)
      return value
    except (ValueError, TypeError):
      pass
  return token

class Tag(object):
  """A [TAG:WITH:ARGS]."""
  MAX_TOKENS = None
  MIN_TOKENS = None
  def __init__(self, tokens):
    self.tokens = list(map(ParseToken, tokens))
    self.filename = None
    self.start_line = None
    self.comment = '\n'

  def SourceFilename(self):
    return self.filename

  def Validate(self, config):
    if self.MAX_TOKENS and len(self.tokens) > self.MAX_TOKENS:
      raise errors.InvalidTag(self, 'too many arguments.')

    if self.MIN_TOKENS and len(self.tokens) < self.MIN_TOKENS:
      raise errors.InvalidTag(self, 'too few arguments.')
    
    # More specific tags could do things like check that their arguments are a
    # valid object in config, for instance.

  def TagName(self):
    return self.tokens[0]

  def Render(self):
     return '%s[%s]' % (self.comment, ':'.join(map(str, self.tokens)))

  def __str__(self):
    return '[%s]' % (':'.join(map(str, self.tokens)))


class ToplevelComment:
  def __init__(self, filename, text):
    self.filename = filename
    self.text = text

  def Render(self):
     return self.text

  def SourceFilename(self):
    return self.filename

  def Validate(self, config):
    pass


class DFObject(object):
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
      raise errors.DisallowedTag(self, tag)

  def __str__(self):
    return '%s (+ %d tags)' % (self.typetag, len(self.tags))

  def SourceFilename(self):
    return self.typetag.SourceFilename()

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
    for field, value in cls.__dict__.items():
      if isinstance(value, type):
        if issubclass(value, ObjectStartTag):
          start_tags.append(value)
        elif issubclass(value, Subsection):
          subsections.append(value)
        elif issubclass(value, Tag):
          tags.append(value)

    if start_tags and 'START_TAGS' not in cls.__dict__:
      cls.START_TAGS = tuple(start_tags)

    if subsections and 'SUBSECTIONS' not in cls.__dict__:
      cls.SUBSECTIONS = tuple(subsections)
      cls.SUBSECTION_TAGS = tuple(s.TAG for s in subsections)

    if tags and 'TAGS' not in cls.__dict__:
      cls.TAGS = tuple(tags)
      # Maybe set ALLOW_UNKNOWN_TAGS = False, too?


class Subsection(DFObject):
  """A section within a DFObject."""
  pass


class ObjectStartTag(Tag):
  MAX_TOKENS = 2
  MIN_TOKENS = 2
  def ObjectType(self):
    return self.tokens[0]

  def ObjectIdentifier(self):
    return self.tokens[1]

class DFConfigSyntaxHelper:
  def __init__(self):
    pass

  def _declaration(impl):
    def _declaration_impl(self, target=None, **kwargs):
      if target is not None:
        return impl(self, target, **kwargs)
      return lambda target: impl(self, target, **kwargs)
    return _declaration_impl

  @_declaration
  def df_object(self, target, name=None):
    """Declare a DF object type.

    @C.df_object
    class THE_OBJECT_TYPE:
      @C.start_tag
      class THE_OBJECT_START_TAG: pass
    """
    target = util.EnsureSubclass(DFObject, target)
    target._GrovelForImplicitDefinitions()
    return target
     
  def NewTag(self, tokens):
    name = tokens[0]
    if name in self.tag:
      return self.tag[name](tokens)
    return Tag(tokens)

  @_declaration
  def section(self, target, name=None):
    """Declare a subsection within an object."""
    target = util.EnsureSubclass(Subsection, target)
    @self.start_tag(name=name or target.__name__)
    class SectionTag: pass
    SectionTag.__name__=name or target.__name__
    target.TAG = SectionTag
    target._GrovelForImplicitDefinitions()
    return target

  @_declaration
  def start_tag(self, target=None, name=None):
    """Declare a start tag for this object."""
    target = util.EnsureSubclass(ObjectStartTag, target)
    if name:
      target.__name__ = name
    return target


def TagStream(filename, input, tag_factory):
  """Turn input into a sequence of Tags and ToplevelComments."""

  # A half assed state machine. I'm quite sure this is very slow.
  class Parser:

    def __init__(self):
      self.counts = defaultdict(lambda: 0)
      self.tag_start = None
      self.comment = []
      self.tag = []

      self.state = self.STATE_TOPLEVEL()

    def CommentChar(self, c):
      self.comment.append(c)
      return []

    def TagChar(self, c):
      self.tag[-1] += c
      return []

    def TagEnd(self, c):
      tag = tag_factory(list(self.tag))
      tag.comment = ''.join(self.comment)
      tag.start_line = self.tag_start
      tag.filename = filename
      self.tag = None
      self.comment = []
      self.state = self.STATE_TOPLEVEL()
      return [tag]

    def TagStart(self, c):
      self.tag = ['']
      self.tag_start = self.CurrentLine()
      self.state = self.STATE_TAG()
      return []

    def TagSection(self, c):
      self.tag.append('')
      return []

    def UnexpectedStartTag(self, c):
      raise errors.ParseError(filename, self.tag_start,
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
        self.counts[char] += 1
        results = self.state[char](char)
        for tag in results:
          yield tag
        char = input.read(1)

      if self.tag:
        raise ParseError(filename, parser.tag_start,
                         'Unclosed tag: %s' % (self.tag,))

      if self.comment:
        yield ToplevelComment(filename, ''.join(self.comment))

    def CurrentLine(self):
     return self.counts['\n'] + 1

  parser = Parser()
  for tag in parser.Parse(input):
    yield tag

