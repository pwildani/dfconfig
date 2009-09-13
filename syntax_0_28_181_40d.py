"""The raws syntax for Dwarf Fortress version 0.28.181.40d."""

import df_syntax

helper = df_syntax.DFConfigSyntaxHelper()

def NewToplevelTag(tokens):
  if tokens[0] == 'OBJECT':
    return OBJECT(tokens)
  return df_syntax.Tag(tokens)

# Bootstrap the OBJECT mode switch tag.
OBJECT = helper.DeclareObjectTag()

# DESCRIPTOR objects are COLOR or SHAPE
DESCRIPTOR = OBJECT.register('DESCRIPTOR')
@DESCRIPTOR
class COLOR: pass

@DESCRIPTOR
class SHAPE: pass

# ITEM objects are all of the many ITEM_*s.
ITEM = OBJECT.register('ITEM')
@ITEM
class ITEM_AMMO: pass

@ITEM
class ITEM_ARMOR: pass

@ITEM
class ITEM_FOOD: pass

@ITEM
class ITEM_GLOVES: pass

@ITEM
class ITEM_HELM: pass

@ITEM
class ITEM_INSTRUMENT: pass

@ITEM
class ITEM_PANTS: pass

@ITEM
class ITEM_SHIELD: pass

@ITEM
class ITEM_SHOES: pass

@ITEM
class ITEM_SIEGEAMMO: pass

@ITEM
class ITEM_TOY: pass

@ITEM
class ITEM_TRAPCOMP: pass

@ITEM
class ITEM_WEAPON: pass


# MATGLOSS objects are all of the various MATGLOSS_*
MATGLOSS = OBJECT.register('MATGLOSS')

@MATGLOSS
class MATGLOSS_METAL: pass

@MATGLOSS
class MATGLOSS_PLANT: pass

@MATGLOSS
class MATGLOSS_STONE: pass

@MATGLOSS
class MATGLOSS_WOOD: pass


# LANGUAGE objects are TRANSLATION, SYMBOL, or WORD
LANGUAGE = OBJECT.register('LANGUAGE')

@LANGUAGE
class TRANSLATION: pass

@LANGUAGE
class SYMBOL: pass

@LANGUAGE
class WORD: pass


# BODY objects are BODY and BODYGLOSS
BODY = OBJECT.register('BODY')
@BODY
class BODY:

  @helper.section
  class BP:
    """The BodyPart section."""

@BODY
class BODYGLOSS: pass


# TODO: [CREATURE][ATTACK]. Might be hard to do without listing all of the
# non-attack creature tags.
