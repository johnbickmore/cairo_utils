"""
Drawing: provides basic setup and drawing utilities for cairo:
"""
import logging as root_logger
import cairo
from .constants import BACKGROUND, TWOPI, FRONT, FONT_SIZE

logging = root_logger.getLogger(__name__)

def setup_cairo(n=5, font_size=FONT_SIZE, scale=True, cartesian=False, background=BACKGROUND):
    """
    Utility a Cairo surface and context
    n : the pow2 size of the surface
    font_size
    scale : True for coords of -1 to 1
    cartesian : True for (0,0) being in the bottom left
    background : The background colour to initialize to
    """
    size = pow(2, n)
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    ctx = cairo.Context(surface)
    if cartesian:
        ctx.scale(1, -1)
        ctx.translate(0, -size)
    if scale:
        ctx.scale(size, size)
    ctx.set_font_size(font_size)
    clear_canvas(ctx, colour=background)
    return (surface, ctx, size, n)


def write_to_png(surface, filename, i=None):
    """ Write the given surface to a png, with optional numeric postfix
    surface : The surface to write
    filename : Does not need file type postfix
    i : optional numeric
    """
    if i:
        surface.write_to_png("{}_{}.png".format(filename, i))
    else:
        surface.write_to_png("{}.png".format(filename))

def draw_rect(ctx, xyxys, fill=True):
    """ Draw simple rectangles.
    Takes the context and a (n,4) array
    """
    #ctx.set_source_rgba(*FRONT)
    for a in xyxys:
        ctx.rectangle(*a)
    if fill:
        ctx.fill()
    else:
        ctx.stroke()

def draw_circle(ctx, xyrs, fill=True):
    """ Draw simple circles
    Takes context,
    """
    for a in xyrs:
        ctx.arc(*a, 0, TWOPI)
    if fill:
        ctx.fill()
    else:
        ctx.stroke()

def clear_canvas(ctx, colour=BACKGROUND, bbox=None):
    """ Clear a rectangle of a context using particular colour
    colour : The colour to clear to
    bbox : The area to clear, defaults to (0,0,1,1)
    """
    ctx.set_source_rgba(*colour)
    if bbox is None:
        ctx.rectangle(0, 0, 1, 1)
    else:
        ctx.rectangle(*bbox)
    ctx.fill()
    ctx.set_source_rgba(*FRONT)

def draw_text(ctx, xy, text):
    """ Utility to simplify drawing text
    Takes context, position, text
    """
    logging.debug("Drawing text: {}, {}".format(text, xy))
    ctx.save()
    ctx.move_to(*xy)
    ctx.scale(1, -1)
    ctx.show_text(str(text))
    ctx.scale(1, -1)
    ctx.restore()
