#!/usr/bin/python2.6

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

from defaultdict import defaultdict

class Tag:
  """A [TAG:WITH:ARGS]."""
  MAX_TOKENS = None
  MIN_TOKENS = None
  def __init__(self, tokens):
    self.tokens = tokens
    self.comment = None

  def Validate(self):
    if self.MAX_TOKENS and len(self.tokens) > self.MAX_TOKENS:
      raise TagError('%s: too many arguments.' % self.TagName())
    if self.MIN_TOKENS and len(self.tokens) < self.MIN_TOKENS):
      raise TagError('%s: too few arguments.' % self.TagName())

  def TagName(self):
    return self.tokens[0]

  def Render(self):
    if self.comment:
      yield self.comment
    yield '[%s]' % (':'.join(self.tokens))

def Indenter(prefix):
  """Indent lines."""
  def Indent(stream):
    for line in stream:
      yield prefix + line
  return Indent

class Registry(dict):
  """Map name -> object, with an @decl."""
  def __init__(self, name):
    self.name = name

  def __call__(name=None):
    def _declaration(impl):
      if name is None:
        name = impl.__name__
      self[name] = impl
      return impl
    _declaration.__name__ = self.name
    return _declaration


TAG = Registry('tag')
DF_OBJECT = Registry('df_object')


def NewTag(tokens):
  name = tokens[0]
  if name in TAG:
    return TAG[name](tokens)
  return Tag(tokens)

INDENT = Indenter('\t')

class DFObject:
  """A CREATURE or MATGLOSS, etc."""
  def __init__(self, typetag):
    self.tags = []
    self.comment = None
    self.typetag = typetag

  def AppendTag(self, tag):
    self.tags.append(tag)
    # TODO: subsections, like ATTACK

  def Render(self):
    if self.comment:
      yield self.comment
    yield self.nametag.Render()
    for tag in tags:
      for line in INDENT(tag):
        yield line


# Bootstrap the OBJECT mode switch tag.
@TAG
class OBJECT(Tag):
  def __init__(self, tokens):
    Tag.__init__(self, tokens)
    if self.ObjectType() not in DF_OBJECT:
      self.DeclareGenericObjectType(self.ObjectType())
  
  def ObjectType(self):
    return self.tokens[1]

  def DeclareGenericObjectType(self, objectname):
    @TAG(name=objectname)
    class _ObjectTag(Tag):
      MAX_TOKENS = 2
      MIN_TOKENS = 2
      def ObjectType(self):
        return self.tokes[0]

      def ObjectIdentifier(self):
        return self.tokens[1]

    @DF_OBJECT(name=objectname)
    class _Object(DFObject):
      START_TAG = (_ObjectTag,)
    _Object.__name__ = objectname

    _ObjectTag.__name__ = objectname


class DFConfigFile:
  TOPLEVEL_TAGS = [ 'OBJECT' ]

  def __init__(self, name):
    self.objects = defaultdict({})
    self.toplevel = [] # ordered tags + comments + objects

  def Render(self):
    for elt in toplevel:
      for line in elt.Render():
        yield line

  def __str__(self):
    return self.Render()

  @classmethod
  def FromTextStream(cls, name, textstream):
    config = cls(name)
    current_def = None
    current_type = None
    for tag in TagStream(stream):
      if isinstance(tag, Tag):

        if isinstance(tag, OBJECT):
          # Switch types
          current_type = DF_OBJECT[tag.ObjectType()]
          current_def = None
          config.toplevel.append(tag)

        elif current_type and isinstance(tag, current_type.START_TAG):
          # New object
          current_def = current_type(tag)
          config.objects[tag.ObjectType()][tag.ObjectIdentifier()] = current_def
          config.toplevel.append(current_def)

        elif current_def:
          # Feed the current object
          current_def.AppendTag(tag)

        else:
          # Unrecognized tag
          raise UnknownToplevelTag(tag)
          
      else:
        # Not a tag
        config.toplevel.append(tag)
    
class ToplevelComment:
  def __init__(self, text):
    self.text = text

  def Render(self):
    yield self.text



def TagStream(input):

  current_comment = []
  current_tag = []

  # A half assed state machine:
  # state = { char : (state, char) -> newstate, [output] }
  def comment_char(state, c):
    current_comment.append(c)
    return state, []

  def tag_char(state, c):
    current_tag[0] += c
    return state, []

  def end_tag(state, c):
    tag = NewTag(list(current_tag))
    if current_comment:
      tag.comment = ''.join(current_comment)
      current_comment[:] = []
    return state_toplevel, [tag]

  def start_tag(state, c):
    current_tag[:] = ['']
    return state_tag, []

  def tag_section(state, c):
    current_tag.append(c)
    return state, []

  state_tag = defaultdict(tag_char, {']': end_tag, ':': tag_section})
  state_toplevel = defaultdict(comment_char, {'[': start_tag})
  # End half-assed state machine

  state = state_toplevel
  char = input.read(1)
  while char:
    state, results = state[char](state, char)
    for tag in results:
      yield tag

  if current_comment:
    yield ToplevelComment(''.join(current_comment))


if __name__ == '__main__':
  import fileiter
  print DFConfigFile.FromTextStream('<input>', fileiter.input())
