# Adafruit_Pinguin
An EAGLE silkscreen label generator written in Python (using PIL/Pillow)
allowing nicer fonts, because EAGLE's proportional font doesn't get output
in CAM data, and the new vector font isn't very attractive.

Ingests am EAGLE .brd file, looking for text elements on layers 172 and
173 (top, bottom) and produces raster equivalents on layers 170 and 171.
When producing CAM files, the raster layers should be included with the top
and bottom silk, the former (input) layers should not. ANY other silk should
go on the normal layers used for such things! This is just for text.

Inspired a bit by SparkFun's "Buzzard" project, but wanting something more
automated.

Name is a cheesy portmanteau of "pin" (because that's mostly what's getting
labeled) and "penguin" (keeping with the bird naming motif; EAGLE, Buzzard,
etc.). I *detest* portmanteau software names but here we are.

"fonts" folder contains TrueType fonts: Google Arimo (EAGLE's proportional
font) and GNU FreeFont files as a starting point. THESE FONTS HAVE THEIR OWN
LICENSES INDEPENDENT FROM THE CODE, see notes in corresponding
subdirectories. If adding any font(s), CHECK for permissive license and
INCLUDE the license file; don't just add things wantonly!
