"""
Adafruit Pinguin -- an EAGLE silkscreen label generator for nicer fonts
with minimal intervention. Reads an EAGLE .brd file, looking for text
objects on specific layers, adds raster equivalents (in nicer fonts) on
different layers, which can be merged with the normal silk output.
"""

import argparse
import os
import xml.etree.ElementTree as ET
from PIL import Image, ImageFont, ImageDraw

# Some global configurables ----

# Configure .brd layers used for input and output
TOP_OUT = 170  #    Top silk output (will be added if not present)
BOTTOM_OUT = 171  # Bottom silk output (will be added if not present)
TOP_IN = 172  #     Top labels input
BOTTOM_IN = 173  #  Bottom labels input
# Additional "IN" layers might get added here later as a cheap
# way of specifying effects like inverted text in a box.

parser = argparse.ArgumentParser()
parser.add_argument('filename', nargs='?', default="AHT20.brd")
parser.add_argument('-vfont', type=str, default="fonts/GNU/FreeSans.ttf")
parser.add_argument('-pfont', type=str, default="fonts/Arimo/static/Arimo-Regular.ttf")
parser.add_argument('-ffont', type=str, default="fonts/GNU/FreeMono.ttf")
parser.add_argument('-vscale', type=float, default=1.414)
parser.add_argument('-pscale', type=float, default=1.414)
parser.add_argument('-fscale', type=float, default=1.414)
parser.add_argument('-dpi', type=int, default=1200)
args = parser.parse_args()
infile = args.filename
path = os.path.split(args.filename)
idx = path[1].rfind(".brd")
if idx < 0:
    print("Input must be a .brd file")
    exit(0)
if len(path[0]):
    outfile = path[0] + '/' + path[1][:idx] + "_out.brd"
else:
    outfile = path[1][:idx] + "_out.brd"
font_spec = ((args.vfont, args.vscale),
             (args.pfont, args.pscale),
             (args.ffont, args.fscale))
mm_to_px = args.dpi / 25.4
px_to_mm = 25.4 / args.dpi

label_num = 0  # Library parts are added incrementally


def layer_find_add(parent, list, number, name, color):
    """Search EAGLE tree for layer by number.
    If present, return it. If not, create new layer and return that.
    """
    num_str = str(number)
    for layer in list:
        if layer.get("number") == num_str:
            return layer  # Layer already present in file
    # Layer's not present in EAGLE file, add it
    return ET.SubElement(
        parent,
        "layer",
        number=num_str,
        name=name,
        color=str(color),
        fill="1",
        visible="yes",
        active="yes",
    )


def rect(parent, x1, x2, y, ax=0, ay=0):
    x1 = (x1 - ax) * px_to_mm
    x2 = (x2 - ax) * px_to_mm
    y2 = (y + 1 - ay) * px_to_mm
    y = (y - ay) * px_to_mm
    child = ET.SubElement(
        parent,
        "rectangle",
        x1="%3.2f" % x1,
        y1="%3.2f" % -y,
        x2="%3.2f" % x2,
        y2="%3.2f" % -y2,
        layer=str(TOP_OUT),
    )


# Convert an image into a series of rectangles
def rectify(parent, image, anchor_x, anchor_y):
    for row in range(image.height):
        pixel_state = 0  # Presume 'off' pixels to start
        start_x = 0
        for column in range(image.width):
            pixel = image.getpixel((column, row))
            if pixel != pixel_state:
                pixel_state = pixel
                if pixel_state > 0:
                    start_x = column
                else:
                    rect(parent, start_x, column, row, anchor_x, anchor_y)
        if pixel_state > 0:
            rect(parent, start_x, image.width, row, anchor_x, anchor_y)


# Order of this list is important, don't mess with
align_list = [
    "bottom-left",
    "bottom-center",
    "bottom-right",
    "center-left",
    "center",
    "center-right",
    "top-left",
    "top-center",
    "top-right",
]
font_list = ["vector", "proportional", "fixed"]


def process_layer(in_texts, in_layer, out_elements, out_packages, out_layer):
    global label_num
    in_str = str(in_layer)
    out_str = str(out_layer)
    for text in in_texts:
        if text.get("layer") == in_str:
            # Found a text object on the input layer
            # Rasterize it and place in the library, add an
            # element to the .brd output layer referencing it.
            text_font = font_list.index(text.get("font", "proportional"))
# TO DO: units here are in pixels...need to handle
# DPI conversion here, NOT in the rect function!
# (though that might need in/mm conversion)
# ImageFont size is in pixels...useless without DPI.
# I'm going to GUESS it's 72 or 96.
# Oh, OK - text.get(size) is likely document units
# (might be in or mm).
# DPI is inches.
# scale former by latter to get pixel units,
# then always replicate at 1:1
            #text_size = int(float(text.get("size")) * font_spec[text_font][1] + 0.5)
            text_size = int(float(text.get("size")) * font_spec[text_font][1] * mm_to_px + 0.5)
            font = ImageFont.truetype(font_spec[text_font][0], text_size)
            metrics = font.getmetrics()
            box = font.getbbox(
                text.text,
                mode="",
                direction=None,
                features=None,
                language=None,
                stroke_width=0,
                anchor=None,
            )
            print(metrics, box)
            width = box[2] - box[0] + 1
            height = box[3] - box[1] + 1
            image = Image.new("1", (width, height), color=0)
            draw = ImageDraw.Draw(image)
            draw.text(
                (-box[0], -box[1]), text.text, font=font, fill=1, features=None
            )
            text_align = align_list.index(text.get("align", "bottom-left"))
            anchor_horiz = text_align % 3
            anchor_vert = text_align // 3
            if anchor_horiz == 0:
                anchor_x = 0
            elif anchor_horiz == 1:
                anchor_x = width / 2
            else:
                anchor_x = width
            if anchor_vert == 0:
                anchor_y = metrics[0] - metrics[1]
            elif anchor_vert == 1:
                anchor_y = (metrics[0] - metrics[1]) * 0.5
            else:
                anchor_y = 0
            # Add package in library
            name = "pLabel" + str(label_num)
            package = ET.SubElement(out_packages, "package", name=name)
            rectify(package, image, anchor_x, anchor_y)
            # Add element in .brd (referencing lbr package)
            rot = text.get("rot", "R0")
            ET.SubElement(
                out_elements,
                "element",
                name=name,
                library="pinguin",
                package=name,
                x=text.get("x"),
                y=text.get("y"),
                smashed="yes",
                rot=rot,
            )
            label_num += 1


# -----


brd_tree = ET.parse(infile)
brd_root = brd_tree.getroot()
brd_layers = brd_root.findall("drawing/layers")[0]  # <layers> in .brd
layer_list = brd_layers.findall("layer")  #           List of <layer> elements

# If Pinguin_tPlace and/or Pinguin_bPlace layers are present in .brd,
# delete them (we'll make new ones in a moment). It's easier than
# conditionally adding them and iterating through to delete contents.
layer_names = [str(TOP_OUT), str(BOTTOM_OUT)]
for layer in layer_list:
    if layer.get("number") in layer_names:
        brd_layers.remove(layer)

top_out = ET.SubElement(
    brd_layers,
    "layer",
    number=str(TOP_OUT),
    name="Pinguin_tPlace",
    color=str(14),
    fill="1",
    visible="yes",
    active="yes",
)
bottom_out = ET.SubElement(
    brd_layers,
    "layer",
    number=str(BOTTOM_OUT),
    name="Pinguin_bPlace",
    color=str(13),
    fill="1",
    visible="yes",
    active="yes",
)

top_in = layer_find_add(brd_layers, layer_list, TOP_IN, "Pinguin_tIn", 10)
bottom_in = layer_find_add(brd_layers, layer_list, BOTTOM_IN, "Pinguin_bIn", 1)

# Sort .brd layers list so Pinguin-added items aren't at end in EAGLE menu
brd_layers[:] = sorted(brd_layers, key=lambda child: int(child.get("number")))

brd_grid = brd_root.findall("drawing/grid")[0]
print(brd_grid.get("unit"))
# could be "mic", "mm", "mil" or "inch"
# micrometer, millimeter, mills (1/1000 in), inch
# If inch, text scale is equal to DPI setting
# if mills, DPI / 1000
# etc.
print(brd_grid.get("distance"))
# Text units are always mm regardless of doc units setting.
# (Properties dialog scales so units = doc units, but file is mm)


# Get list of text objects in the .brd file

brd_elements = brd_root.findall("drawing/board/elements")[0]  # <elements> in .brd
brd_plain = brd_root.findall("drawing/board/plain")[0]
brd_texts = brd_root.findall("drawing/board/plain/text")
# brd_texts = brd_plain.findall("text")
# Need to do some check-if-exist stuff here
brd_libraries = brd_root.findall("drawing/board/libraries")[0]  # <libraries> in .brd
brd_library_list = brd_libraries.findall("library")  # List of <library> items
for lib in brd_library_list:  #                        Iterate through list
    if lib.get("name") == "pinguin":  #                If pinguin library,
        brd_libraries.remove(lib)  #                   delete it, we'll make a new one
brd_library = ET.SubElement(brd_libraries, "library", name="pinguin")
brd_packages = ET.SubElement(brd_library, "packages")

process_layer(brd_texts, TOP_IN, brd_elements, brd_packages, TOP_OUT)
process_layer(brd_texts, BOTTOM_IN, brd_elements, brd_packages, BOTTOM_OUT)

# ElementTree by default doesn't indent XML. There's an option in Python >= 3.9
# to do this, but it's not present in older versions (e.g. macOS at the moment).
# This is a "nice to have" during development & testing but is not crucial...so
# we try/except and just pass if it's a problem, no worries. xmllint, if
# available, can be invoked manually after the fact:
#     xmllint --format - <infile >outfile
try:
    ET.indent(brd_tree, space="  ")
except:
    pass
brd_tree.write(outfile, encoding="utf-8", xml_declaration=True)


# ------------------------------


# Default alignment (None) is lower left
# center alignment is centered on BOTH axes
# <!ENTITY % TextFont          "(vector | proportional | fixed)">
# <!ENTITY % Align             "(bottom-left | bottom-center | bottom-right | center-left | center | center-right | top-left | top-center | top-right)">
# (is position of anchor relative to text)
# <!ATTLIST text
#           x             %Coord;        #REQUIRED
#           y             %Coord;        #REQUIRED
#           size          %Dimension;    #REQUIRED
#           layer         %Layer;        #REQUIRED
#           font          %TextFont;     "proportional"
#           ratio         %Int;          "8" <- stroke thickness
#           rot           %Rotation;     "R0" <- degrees (not just 90 inc)
#           align         %Align;        "bottom-left"
#           distance      %Int;          "50" <- line distance
#           grouprefs     IDREFS         #IMPLIED
#           >
# Ratio is ignored on proportional font

#    # First 4 are required, rest are optional and have defaults if not present
#    print(
#        t.get("x"),
#        t.get("y"),
#        t.get("size"),
#        t.get("layer"),
#        t.get("font", "proportional"),
#        t.get("ratio", "8"),
#        t.get("rot", "R0"),
#        t.get("align", "bottom-left"),
#        t.text,
#    )

# <!ATTLIST layer
#          number        %Layer;        #REQUIRED
#          name          %String;       #REQUIRED
#          color         %Int;          #REQUIRED
#          fill          %Int;          #REQUIRED
#          visible       %Bool;         "yes"
#          active        %Bool;         "yes"
#          >
