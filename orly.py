# ORLY?! Counter plugin for OBS Studio
# By RoadrunnerWMC -- April 15, 2018

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import contextlib
import json
import os.path
import sys
import time

import obspython as obs

PROP_ID_OWL_SOURCE = 'orly_owl'
PROP_ID_LABEL_SOURCE = 'orly_label'
PROP_ID_COUNTER_SOURCE = 'orly_counter'
PROP_ID_DING1_SOURCE = 'orly_ding1'
PROP_ID_DING10_SOURCE = 'orly_ding10'
PROP_ID_DING50_SOURCE = 'orly_ding50'
PROP_ID_OWL_X_POS = 'orly_owl_x_pos'
PROP_ID_OWL_Y_POS = 'orly_owl_y_pos'
PROP_ID_OWL_X_DISTANCE = 'orly_owl_x_distance'
PROP_ID_OWL_Y_DISTANCE = 'orly_owl_y_distance'
PROP_ID_HIDE_BUTTON = 'orly_hide_all'
PROP_ID_RESTORE_BUTTON = 'orly_restore_all'
PROP_NAME_OWL_SOURCE = 'Owl image:'
PROP_NAME_LABEL_SOURCE = 'Label textbox ("ORLY?! COUNTER:"):'
PROP_NAME_COUNTER_SOURCE = 'Number textbox ("0"):'
PROP_NAME_DING1_SOURCE = 'Ding:'
PROP_NAME_DING10_SOURCE = 'Ding (10):'
PROP_NAME_DING50_SOURCE = 'Ding (50):'
PROP_NAME_OWL_X_POS = 'Owl X position:'
PROP_NAME_OWL_Y_POS = 'Owl Y position:'
PROP_NAME_OWL_X_DISTANCE = 'Owl X movement distance:'
PROP_NAME_OWL_Y_DISTANCE = 'Owl Y movement distance:'
PROP_NAME_HIDE_BUTTON = 'Hide All'
PROP_NAME_RESTORE_BUTTON = 'Restore All'

OPACITY_FILTER_NAME = 'Opacity'

orlyStateMachine = None


def hexToColor(s):
    """
    ("#RRGGBB" or "#RRGGBBAA") -> (OBS color value)
    """
    assert s[0] == '#'
    r = int(s[1:3], 16)
    g = int(s[3:5], 16)
    b = int(s[5:7], 16)
    args = [r, g, b]
    if len(s) >= 9:
        args.append(int(s[7:9], 16))
    return rgbaToColor(*args)


def rgbaToColor(r, g, b, a=255):
    """
    Convert (r, g, b, a) to an OBS color value (0xAABBGGRR)
    """
    return (a << 24) | (b << 16) | (g << 8) | r


def colorToRgba(color):
    """
    Convert an OBS color value (0xAABBGGRR) to (r, g, b, a)
    """
    return (color & 0xFF,
            (color >> 8) & 0xFF,
            (color >> 16) & 0xFF,
            (color >> 24) & 0xFF)


# The set of colors that the counter will use whenever it reaches a
# given value: (fill, outline)
if sys.platform == 'win32':
    color250 = (hexToColor('#000000'), hexToColor('#ffffff'))
else:
    # FreeType2 textboxes on Linux don't support outlines
    color250 = (hexToColor('#444444'), None)
COLORS = {
    0:   (hexToColor('#5fa128'), None),
    50:  (hexToColor('#ffcc01'), None),
    100: (hexToColor('#ff0002'), None),
    150: (hexToColor('#9a00ff'), None),
    200: (hexToColor('#0200ff'), None),
    250: color250,
    300: (hexToColor('#ffffff'), None),
}


def colorsForNum(num):
    """
    Return the color and outline that should be used for the given ORLY
    number.
    """
    currentBracket = 0
    currentColor = (rgbaToColor(255, 255, 255), None) # default to white
                                                      # with no outline
    for bracket, col in COLORS.items():
        if bracket >= currentBracket and bracket <= num:
            currentBracket = bracket
            currentColor = col

    return currentColor


def fractionsOfOne(iterations):
    """
    Count from 0 to 1 inclusive using `iterations` iterations.
    For example, fractionsOfOne(5) yields 0, 0.25, 0.5, 0.75, 1.
    """
    for i in range(iterations):
        yield i / (iterations - 1)


@contextlib.contextmanager
def getSourceByName(name):
    """
    Context manager to call obs_get_source_by_name() and release the
    source when done.
    """
    source = obs.obs_get_source_by_name(name)
    yield source
    if source is not None:
        obs.obs_source_release(source)


@contextlib.contextmanager
def sourceGetFilterByName(source, name):
    """
    Context manager to call obs_source_get_filter_by_name() and release
    the filter when done.
    """
    filter = obs.obs_source_get_filter_by_name(source, name)
    yield filter
    if filter is not None:
        obs.obs_source_release(filter)


@contextlib.contextmanager
def frontendGetCurrentScene():
    """
    Context manager to call obs_frontend_get_current_scene() and release
    the source when done.
    """
    source = obs.obs_frontend_get_current_scene()
    yield source
    if source is not None:
        obs.obs_source_release(source)


@contextlib.contextmanager
def getSourceSettings(source):
    """
    Context manager to get source settings and release them when done.
    """
    settings = obs.obs_source_get_settings(source)
    yield settings
    if settings is not None:
        obs.obs_data_release(settings)


@contextlib.contextmanager
def createObsData():
    """
    Context manager to call obs_data_create() and release the data when
    done.
    """
    data = obs.obs_data_create()
    yield data
    obs.obs_data_release(data)


@contextlib.contextmanager
def enumSources():
    """
    Context manager to call obs_enum_sources() and release the list when
    done.
    """
    sources = obs.obs_enum_sources()
    if sources is None:
        yield []
    else:
        yield sources
        obs.source_list_release(sources)


@contextlib.contextmanager
def sceneEnumItems(scene):
    """
    Context manager to call obs_scene_enum_items() and release the list
    when done.
    """
    items = obs.obs_scene_enum_items(scene)
    if items is None:
        yield []
    else:
        yield items
        obs.sceneitem_list_release(items)


class OrlyStateMachine():
    """
    State machine for ORLY animations.
    """
    framerate = None
    negationTimeout = None

    owlSourceName = ''
    labelSourceName = ''
    counterSourceName = ''
    ding1SourceName = ''
    ding10SourceName = ''
    ding50SourceName = ''

    owlBaseX = None
    owlBaseY = None
    owlXDistance = None
    owlYDistance = None
    textColor = None
    outlineColor = None

    currentAnim = None
    negatePressedAt = 0

    orlyCountIfInterrupted = None

    def __init__(self, defaults):
        """
        Initialize the state machine.
        """
        self.owlBaseX = defaults['owl-x-position']
        self.owlBaseY = defaults['owl-y-position']
        self.owlXDistance = defaults['owl-x-movement-distance']
        self.owlYDistance = defaults['owl-y-movement-distance']

        self.framerate = defaults['framerate']
        self.negationTimeout = defaults['negation-timeout']


    def iterSceneItemsByName(self, sourceName):
        """
        Iterator over scene items with a given source name, in the
        scene currently displayed in the frontend
        """
        # This took me a while to figure out, so I'll comment it
        # enough to be understandable.

        # First, we get the source we need to find items of
        with getSourceByName(sourceName) as s:
            if s is None: return []

            # Now we get the entire scene that's currently streaming
            with frontendGetCurrentScene() as currentSceneSource:
                if currentSceneSource is None: return []

                # (and convert it to a scene)
                currentScene = obs.obs_scene_from_source(currentSceneSource)
                if currentScene is None: return []

                # Now we iterate over all the items in that scene
                with sceneEnumItems(currentScene) as items:
                    for item in items:
                        if item is None: continue

                        # Now we find what source this item is using
                        itemSource = obs.obs_sceneitem_get_source(item)
                        # And the name of that source
                        itemSourceName = obs.obs_source_get_name(itemSource)
                        # And if it's what we want, we yield it!
                        if itemSourceName == sourceName:
                            yield item


    def updateSettings(self, settings):
        """
        Update the settings with the given obs_data_t settings object.
        """

        # Update the owl source name
        newOwlName = obs.obs_data_get_string(
            settings,
            PROP_ID_OWL_SOURCE)
        if self.owlSourceName != newOwlName:
            for item in self.iterSceneItemsByName(newOwlName):
                pos = obs.vec2()
                obs.obs_sceneitem_get_pos(item, pos)
                self.owlBaseY = pos.y
                break
        self.owlSourceName = newOwlName

        # Update the label and counter source names
        self.labelSourceName = obs.obs_data_get_string(
            settings,
            PROP_ID_LABEL_SOURCE)
        newCounterSourceName = obs.obs_data_get_string(
            settings,
            PROP_ID_COUNTER_SOURCE)
        if self.counterSourceName != newCounterSourceName:
            with getSourceByName(newCounterSourceName) as source:
                if source is not None:
                    with getSourceSettings(source) as settings:
                        text = obs.obs_data_get_string(settings, 'text')
                        try:
                            self.textColor, self.outlineColor = \
                                colorsForNum(int(text))
                            self.setSourceTextColorByName(newCounterSourceName,
                                                          self.textColor,
                                                          self.outlineColor)
                        except ValueError: pass
        self.counterSourceName = newCounterSourceName

        # Update the ding source names
        self.ding1SourceName = obs.obs_data_get_string(
            settings,
            PROP_ID_DING1_SOURCE)
        self.ding10SourceName = obs.obs_data_get_string(
            settings,
            PROP_ID_DING10_SOURCE)
        self.ding50SourceName = obs.obs_data_get_string(
            settings,
            PROP_ID_DING50_SOURCE)

        # Update the owl Y position and movement distance
        self.owlBaseX = obs.obs_data_get_double(
            settings,
            PROP_ID_OWL_X_POS)
        self.owlBaseY = obs.obs_data_get_double(
            settings,
            PROP_ID_OWL_Y_POS)
        self.owlXDistance = obs.obs_data_get_double(
            settings,
            PROP_ID_OWL_X_DISTANCE)
        self.owlYDistance = obs.obs_data_get_double(
            settings,
            PROP_ID_OWL_Y_DISTANCE)


    def setSourceOpacityByName(self, sourceName, opacity):
        """
        Sets the opacity of the given source by name, if it has the
        appropriate filter.
        """
        with getSourceByName(sourceName) as source:
            if source is None: return

            with sourceGetFilterByName(source, OPACITY_FILTER_NAME) as filter:
                if filter is None: return

                with createObsData() as settings:
                    obs.obs_data_set_int(settings, 'opacity', int(opacity))
                    obs.obs_source_update(filter, settings)


    def setSourceTextColorByName(self, sourceName, color, outline=None):
        """
        Sets the color of the given text source by name. The color
        should be an int, in OBS color format. The outline color can
        either be None (meaning no outline) or an int in OBS color
        format.
        """
        with getSourceByName(sourceName) as source:
            if source is None: return

            with createObsData() as settings:
                if obs.obs_source_get_id(source) == 'text_ft2_source':
                    obs.obs_data_set_int(settings, 'color1', color)
                    obs.obs_data_set_int(settings, 'color2', color)

                    # FreeType2 currently doesn't support setting
                    # outline colors. We *could* turn the outline on,
                    # but that's probably not what whoever specified an
                    # outline wanted. So we just won't.
                
                elif obs.obs_source_get_id(source) == 'text_gdiplus':
                    colorRGB = rgbaToColor(*colorToRgba(color)[:3])
                    colorA = int(colorToRgba(color)[3] * 100/255)
                    obs.obs_data_set_int(settings, 'color', colorRGB)
                    obs.obs_data_set_int(settings, 'opacity', colorA)

                    obs.obs_data_set_bool(settings,
                                          'outline',
                                          outline is not None)
                    if outline is not None:
                        outlineRGB = rgbaToColor(*colorToRgba(outline)[:3])
                        outlineA = int(colorToRgba(outline)[3] * 100/255)
                        obs.obs_data_set_int(settings,
                                             'outline_color',
                                             outlineRGB)
                        obs.obs_data_set_int(settings,
                                             'outline_opacity',
                                             outlineA)

                obs.obs_source_update(source, settings)


    def setSourcePosByName(self, sourceName, x=None, y=None):
        """
        Set the position of the given source by name. If either
        coordinate is None, that coordinate will not be modified.
        """
        if x == y == None: return

        for item in self.iterSceneItemsByName(sourceName):
            pos = obs.vec2()
            obs.obs_sceneitem_get_pos(item, pos)
            if x is not None:
                pos.x = x
            if y is not None:
                pos.y = y
            obs.obs_sceneitem_set_pos(item, pos)


    def prepareForSfx(self):
        """
        Stop all playing sound effects, so that one can be played soon.
        """
        for sourceName in [self.ding1SourceName,
                        self.ding10SourceName,
                        self.ding50SourceName]:
            for item in self.iterSceneItemsByName(sourceName):
                obs.obs_sceneitem_set_visible(item, False)


    def playSFX(self, sourceName):
        """
        Play the sound effect with the given source name.
        """
        for item in self.iterSceneItemsByName(sourceName):
            obs.obs_sceneitem_set_visible(item, True)


    def tick(self):
        """
        Play the next animation frame.
        Return True if there's still more animation to play.
        """
        if self.currentAnim is not None:
            try:
                next(self.currentAnim)
                return True
            except StopIteration:
                return False
        return False


    def appearAnimation(self):
        """
        The animation in which the scene items appear.
        """
        self.hideAll()

        for pct in fractionsOfOne(self.framerate // 6):
            x = self.owlBaseX + self.owlXDistance * (1 - pct)
            y = self.owlBaseY + self.owlYDistance * (1 - pct)
            self.setSourcePosByName(self.owlSourceName, x, y)
            yield

        for i in range(self.framerate // 7):
            yield

        for pct in fractionsOfOne(self.framerate // 6):
            self.setSourceOpacityByName(self.labelSourceName, pct * 100)
            yield

        for i in range(int(self.framerate / 2.5)):
            yield

        for pct in fractionsOfOne(self.framerate // 6):
            self.setSourceOpacityByName(self.counterSourceName, pct * 100)
            yield


    def disappearAnimation(self):
        """
        The animation in which the scene items disappear.
        """
        for pct in fractionsOfOne(self.framerate // 5):
            x = self.owlBaseX + self.owlXDistance * pct
            y = self.owlBaseY + self.owlYDistance * pct
            self.setSourcePosByName(self.owlSourceName, x, y)
            pct = 1 - pct
            self.setSourceOpacityByName(self.labelSourceName, pct * 100)
            self.setSourceOpacityByName(self.counterSourceName, pct * 100)
            yield


    def increment(self, amount=1):
        """
        Begin the animation of incrementing the counter.
        """
        self.prepareForSfx()

        with getSourceByName(self.counterSourceName) as counterSource:
            if counterSource is None: return

            if self.orlyCountIfInterrupted is None:
                with getSourceSettings(counterSource) as counterSettings:
                    if counterSettings is None: return
                    currentText = obs.obs_data_get_string(counterSettings,
                                                          'text')

                # Don't crash if the textbox doesn't contain a number
                try:
                    currentValue = int(currentText)
                except ValueError:
                    print('ERROR: The number textbox contains "%s"!'
                          % currentText)
                    return
            else:
                currentValue = self.orlyCountIfInterrupted

            isMultipleOf10 = False
            for i in range(amount):
                isMultipleOf10 |= (currentValue + i + 1) % 10 == 0
            newValue = currentValue + amount
            self.orlyCountIfInterrupted = newValue

            if amount != 1:
                if amount >= 0:
                    text = '+' + str(amount)
                elif amount < 1:
                    text = str(amount)
                color = None
                outline = None
            else:
                text = str(newValue)
                color, outline = colorsForNum(newValue)

            with createObsData() as counterSettings:
                obs.obs_data_set_string(counterSettings, 'text', text)
                obs.obs_source_update(counterSource, counterSettings)

        if amount != 1:
            self.setSourceTextColorByName(self.counterSourceName,
                                          rgbaToColor(255, 255, 255))
        elif color == self.textColor or self.textColor is None:
            self.setSourceTextColorByName(self.counterSourceName,
                                          color,
                                          outline)
            self.textColor = color
            self.outlineColor = outline

        def anim():
            """
            Generator function for the ORLY increment animation
            """
            nonlocal color, outline, text
            yield from self.appearAnimation()

            if amount != 1:
                for i in range(int(self.framerate * 1.15)):
                    yield

                for pct in fractionsOfOne(self.framerate // 6):
                    self.setSourceOpacityByName(self.counterSourceName,
                                                100 - pct * 100)
                    yield

                yield

                text = str(newValue)
                color, outline = colorsForNum(newValue)

                with getSourceByName(self.counterSourceName) as counterSource:
                    with createObsData() as counterSettings:
                        obs.obs_data_set_string(counterSettings, 'text', text)
                        obs.obs_source_update(counterSource, counterSettings)

                # If we're increasing (i.e. we may flip to a new color),
                # set it to the previous color. If we're decreasing,
                # just set it to the color it should actually be.
                if amount > 0 and self.textColor is not None:
                    self.setSourceTextColorByName(self.counterSourceName,
                                                  self.textColor,
                                                  self.outlineColor)
                else:
                    self.setSourceTextColorByName(self.counterSourceName,
                                                  color,
                                                  outline)
                    self.textColor = color
                    self.outlineColor = outline

                for pct in fractionsOfOne(self.framerate // 6):
                    self.setSourceOpacityByName(self.counterSourceName,
                                                pct * 100)
                    yield

            if self.textColor == color or amount < 0:
                if amount > 0:
                    if isMultipleOf10:
                        self.playSFX(self.ding10SourceName)
                    else:
                        self.playSFX(self.ding1SourceName)

                for i in range(int(self.framerate * 1.15)):
                    yield

            else:
                self.playSFX(self.ding50SourceName)

                for i in range(int(self.framerate * 0.4)):
                    yield

                # Blend the old and new colors
                r1a, g1a, b1a, _ = colorToRgba(self.textColor)
                r2a, g2a, b2a, _ = colorToRgba(color)
                fadeOutline = (self.outlineColor is not None
                               or outline is not None)
                if fadeOutline:
                    soC = self.outlineColor
                    if self.outlineColor is None:
                        soC = rgbaToColor(0, 0, 0, 0)
                    outlineC = outline
                    if outline is None:
                        outlineC = rgbaToColor(0, 0, 0, 0)
                    r1b, g1b, b1b, a1b = colorToRgba(soC)
                    r2b, g2b, b2b, a2b = colorToRgba(outlineC)
                for pct in fractionsOfOne(self.framerate // 6):
                    r3a = int(r1a + (r2a - r1a) * pct)
                    g3a = int(g1a + (g2a - g1a) * pct)
                    b3a = int(b1a + (b2a - b1a) * pct)
                    fadeColor = rgbaToColor(r3a, g3a, b3a)
                    if fadeOutline:
                        r3b = int(r1b + (r2b - r1b) * pct)
                        g3b = int(g1b + (g2b - g1b) * pct)
                        b3b = int(b1b + (b2b - b1b) * pct)
                        a3b = int(a1b + (a2b - a1b) * pct)
                        if a3b <= 1:
                            fadeOutlineColor = None
                        else:
                            fadeOutlineColor = rgbaToColor(r3b, g3b, b3b, a3b)
                    else:
                        fadeOutlineColor = None
                    self.setSourceTextColorByName(self.counterSourceName,
                                                  fadeColor,
                                                  fadeOutlineColor)
                    yield

                self.textColor = color
                self.outlineColor = outline

                for i in range(int(self.framerate * 2.15)):
                    yield

            yield from self.disappearAnimation()

            self.orlyCountIfInterrupted = None

        self.currentAnim = anim()


    def hideAll(self):
        """
        Hide all sources.
        """
        # Set the ORLY owl position
        self.setSourcePosByName(self.owlSourceName,
                                self.owlBaseX + self.owlXDistance,
                                self.owlBaseY + self.owlYDistance)

        # Set the label and counter opacities
        self.setSourceOpacityByName(self.labelSourceName, 0)
        self.setSourceOpacityByName(self.counterSourceName, 0)


    def restoreAll(self):
        """
        Restore (un-hide) all sources.
        """

        # Restore the ORLY owl position
        self.setSourcePosByName(self.owlSourceName,
                                self.owlBaseX,
                                self.owlBaseY)

        # Restore the label opacity
        self.setSourceOpacityByName(self.labelSourceName, 100)

        # Restore the counter color and opacity
        white = rgbaToColor(255, 255, 255)
        self.setSourceTextColorByName(self.counterSourceName, white)
        self.setSourceOpacityByName(self.counterSourceName, 100)


def createStateMachine():
    """
    Create the state machine that will handle all animations, if it's
    not already created.
    """
    global orlyStateMachine
    if orlyStateMachine is not None: return

    # OBS exposes script_path() for us, but guess what? It crashes
    # sometimes! (in particular, if you repeatedly reload the script)
    # So we'll get the path the manual way.
    defaultsPath = os.path.join(os.path.dirname(__file__), 'defaults.json')
    with open(defaultsPath, 'r', encoding='utf-8') as f:
        defaults = json.load(f)

    orlyStateMachine = OrlyStateMachine(defaults)



def script_description():
    """
    Return a nice description for the script.
    """
    desc = """
A script that provides a real-time ORLY Counter for your stream!
By RoadrunnerWMC.
"""[1:-1]
    return desc


def script_load(settings):
    """
    This is run automatically when the script is loaded. It sets stuff
    up.
    """
    createStateMachine()
    orlyStateMachine.updateSettings(settings)

    # Register hotkeys
    for i in range(5):
        obs.obs_hotkey_register_frontend(
            'orly_counter_inc_' + str(i + 1),
            'ORLY +' + str(i + 1),
            lambda pressed, q=i: handleORLY(pressed, q + 1))
    obs.obs_hotkey_register_frontend(
        'orly_counter_negate',
        'Negate next ORLY',
        handleNegateORLY)


def script_update(settings):
    """
    Run whenever the script settings are changed by the user.
    """
    createStateMachine()
    orlyStateMachine.updateSettings(settings)


def script_unload():
    """
    Run when the script is about to be unloaded.
    """
    obs.obs_hotkey_unregister(handleORLY)


def script_properties():
    """
    Defines the user-configurable script properties.
    Code for letting the user choose a video source is from
    https://github.com/burkdan/OBS-Google-Events/blob/master/google_calendar_event.py
    """
    # Create the properties object
    props = obs.obs_properties_create()

    # Make properties for the sources that will be used for the
    # animations
    sourceOwlProp = obs.obs_properties_add_list(
        props, 
        PROP_ID_OWL_SOURCE,
        PROP_NAME_OWL_SOURCE,
        obs.OBS_COMBO_TYPE_EDITABLE,
        obs.OBS_COMBO_FORMAT_STRING)
    sourceLabelProp = obs.obs_properties_add_list(
        props, 
        PROP_ID_LABEL_SOURCE,
        PROP_NAME_LABEL_SOURCE,
        obs.OBS_COMBO_TYPE_EDITABLE,
        obs.OBS_COMBO_FORMAT_STRING)
    sourceNumProp = obs.obs_properties_add_list(
        props, 
        PROP_ID_COUNTER_SOURCE,
        PROP_NAME_COUNTER_SOURCE,
        obs.OBS_COMBO_TYPE_EDITABLE,
        obs.OBS_COMBO_FORMAT_STRING)
    # ...and sound effects
    sourceDing1Prop = obs.obs_properties_add_list(
        props, 
        PROP_ID_DING1_SOURCE,
        PROP_NAME_DING1_SOURCE,
        obs.OBS_COMBO_TYPE_EDITABLE,
        obs.OBS_COMBO_FORMAT_STRING)
    sourceDing10Prop = obs.obs_properties_add_list(
        props, 
        PROP_ID_DING10_SOURCE,
        PROP_NAME_DING10_SOURCE,
        obs.OBS_COMBO_TYPE_EDITABLE,
        obs.OBS_COMBO_FORMAT_STRING)
    sourceDing50Prop = obs.obs_properties_add_list(
        props, 
        PROP_ID_DING50_SOURCE,
        PROP_NAME_DING50_SOURCE,
        obs.OBS_COMBO_TYPE_EDITABLE,
        obs.OBS_COMBO_FORMAT_STRING)

    # Add source names to the source property boxes
    with enumSources() as sources:
        for source in sources:
            sourceId = obs.obs_source_get_id(source)

            if sourceId in ['text_gdiplus', 'text_ft2_source']:
                name = obs.obs_source_get_name(source)

                obs.obs_property_list_add_string(sourceLabelProp,
                                                 name, name)
                obs.obs_property_list_add_string(sourceNumProp,
                                                 name, name)

            elif sourceId == 'image_source':
                name = obs.obs_source_get_name(source)

                obs.obs_property_list_add_string(sourceOwlProp, name, name)

            elif sourceId == 'ffmpeg_source':
                name = obs.obs_source_get_name(source)

                obs.obs_property_list_add_string(sourceDing1Prop, name, name)
                obs.obs_property_list_add_string(sourceDing10Prop, name, name)
                obs.obs_property_list_add_string(sourceDing50Prop, name, name)

    # Make properties for the owl position
    obs.obs_properties_add_float(
        props,
        PROP_ID_OWL_X_POS,
        PROP_NAME_OWL_X_POS,
        -9999, 9999, 1) # min, max, step
    obs.obs_properties_add_float(
        props,
        PROP_ID_OWL_Y_POS,
        PROP_NAME_OWL_Y_POS,
        -9999, 9999, 1) # min, max, step
    obs.obs_properties_add_float(
        props,
        PROP_ID_OWL_X_DISTANCE,
        PROP_NAME_OWL_X_DISTANCE,
        -9999, 9999, 1) # min, max, step
    obs.obs_properties_add_float(
        props,
        PROP_ID_OWL_Y_DISTANCE,
        PROP_NAME_OWL_Y_DISTANCE,
        -9999, 9999, 1) # min, max, step

    # Create button "properties" to allow quick setup
    obs.obs_properties_add_button(
        props,
        PROP_ID_HIDE_BUTTON,
        PROP_NAME_HIDE_BUTTON,
        handleHideAll)
    obs.obs_properties_add_button(
        props,
        PROP_ID_RESTORE_BUTTON,
        PROP_NAME_RESTORE_BUTTON,
        handleRestoreAll)

    return props


def script_defaults(settings):
    """
    Set default script setting values.
    """
    createStateMachine()
    obs.obs_data_set_double(settings,
        PROP_ID_OWL_X_POS,
        orlyStateMachine.owlBaseX)
    obs.obs_data_set_double(settings,
        PROP_ID_OWL_Y_POS,
        orlyStateMachine.owlBaseY)
    obs.obs_data_set_double(settings,
        PROP_ID_OWL_X_DISTANCE,
        orlyStateMachine.owlXDistance)
    obs.obs_data_set_double(settings,
        PROP_ID_OWL_Y_DISTANCE,
        orlyStateMachine.owlYDistance)


def tick():
    """
    Called once per frame during the ORLY animation.
    """
    global existingTimer
    if not orlyStateMachine.tick():
        obs.remove_current_callback()
        existingTimer = False


def handleNegateORLY(pressed):
    """
    Called when the user presses or releases the "Negate next ORLY"
    hotkey.
    """
    if not pressed: return

    orlyStateMachine.negatePressedAt = time.time()


existingTimer = False
def handleORLY(pressed, amount):
    """
    Called when the user presses or releases a hotkey to increment the
    counter.
    """
    if not pressed: return

    global existingTimer
    if existingTimer:
        obs.timer_remove(tick)

    timeElapsed = time.time() - orlyStateMachine.negatePressedAt
    if timeElapsed <= orlyStateMachine.negationTimeout:
        amount = -amount
        orlyStateMachine.negatePressedAt = 0
    orlyStateMachine.increment(amount)

    obs.timer_add(tick, int(1000 / orlyStateMachine.framerate))
    existingTimer = True


def handleHideAll(props=None, prop=None, *args, **kwargs):
    """
    Handler for the "hide all" button. All functionality is delegated
    to the state machine.
    """
    orlyStateMachine.hideAll()


def handleRestoreAll(props=None, prop=None, *args, **kwargs):
    """
    Handler for the "restore all" button. All functionality is delegated
    to the state machine.
    """
    orlyStateMachine.restoreAll()
