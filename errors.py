class Error(Exception):
  pass


class FileLineError(Error):
  """"An error on a specific line in a file."""
  def __init__(self, filename, linenum, *args):
    self.filename = filename
    self.linenum = linenum
    Error.__init__(self, *args)


class TagError(FileLineError):
  """An error related to a specific tag."""
  def __init__(self, tag, message):
    self.tag = tag
    FileLineError.__init__(self, tag.filename, tag.start_line,
                           '%s: %s' % (tag, message))


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
