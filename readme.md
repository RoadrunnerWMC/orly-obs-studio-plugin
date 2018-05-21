# ORLY?! Counter plugin for OBS Studio

This is a plugin for OBS Studio that adds a real-time "ORLY?! Counter" as seen in [Skawo's videos](https://www.youtube.com/user/skawo90/videos). (This is really only useful for Skawo and his fans.)

## Setup

I apologize in advance for this lengthy setup process. OBS Studio plugins written in Python can't create their own sources, so you have to do it manually.

You'll need to follow this setup procedure for each scene you want to use the ORLY Counter in. (You won't need to load the plugin again when switching scenes, but you will need to select the sources for the scene you switch to in the plugin settings.)

1. Download the plugin and unzip it.
2. Create an image source for the owl, and set it to use `owl.png`.
3. Add the two textboxes (do these steps twice):
    1. Add a textbox.
        1. The first one is the counter name label ("ORLY?! COUNTER:").
        2. The second one is the counter itself ("0", initially).
    2. Set the textbox font to whatever you want. Skawo uses the font "Delfino."
    3. Right-click on the textbox.
    4. Choose "Filters."
    5. Click the "+" button in the bottom-left corner, and choose "Image Mask/Blend."
    6. Name it "Opacity" (capitalized exactly like that, or else the plugin won't be able to find it).
    7. Under "Path", browse to `white.png`.
    8. Click "Close."
4. Position the three sources approximately where they belong in the scene.
5. Add the three sound effects:
    1. Add a new Media Source.
        1. The first one is the default "ding."
        2. The second one is the "ding" used for multiples of 10.
        3. The third one is the "ding-ding-ding, dong" used for multiples of 50.
    2. Click "Browse" and choose the appropriate sound file (`ding-01.wav`, `ding-10.wav`, or `ding-50.wav`).
    3. Click "OK."
6. Add the Python script to OBS:
    1. Tools → Scripts
    2. Click "+," and select `orly.py`.
    3. If OBS loaded the plugin correctly, new options should appear on the right.
    4. Use the first six options to select the six sources you created.
    5. Check that the "Hide All" and "Restore All" buttons work.
    6. Adjust the owl position and movement-distance options if you want:
        1. To see the current x and y coordinates of the owl, right-click on it, choose "Transform," and then "Edit Transform."
        2. The movement distance should be large enough that the owl goes completely off-screen when hidden.
7. Set up hotkeys:
    1. Click the "Settings" button (below "Start Streaming").
    2. Choose the "Hotkeys" tab.
    3. Assign whatever keystrokes you want to the ORLY hotkeys.

## Usage

You can assign hotkeys for "ORLY +1" through "ORLY +5," which you can use to add to the ORLY counter whenever the game you're playing states something obvious. If you hit the "Negate next ORLY" hotkey followed by an addition hotkey, it will subtract that number of ORLYs instead; use this if you change your mind about an ORLY you assigned.

## Troubleshooting

### Hitting an addition hotkey does nothing.

Make sure that the plugin is loaded, that the plugin is using the sources in the current scene, and that you are on the correct scene.

The text in the counter textbox has to be a number, or else the plugin won't do anything.

### I can't hear the ding sounds.

OBS doesn't play them on your system audio, but they will be audible on your stream or in your video. You can check this yourself by recording a short test video file and playing it back.

### The settings go back to their defaults sometimes.

You can edit `defaults.json` to change the default settings.

### Something is wrong with the owl's position or movement.

The owl's position and movement distance is fully customizable in the plugin settings.

### The color for ORLY range 250-299 looks wrong.

The counter should have black text with a white outline when the number is in this range. However, OBS Studio uses different text-rendering backends on different operating systems, and the FreeType2 backend (used on Linux and probably macOS) doesn't support outline colors other than black. In this case, the ORLY plugin therefore uses dark gray text with no outline instead.

## Advanced usage

There are a couple of extra options in `defaults.json`:
- **framerate** controls the framerate of the animations.
- **negation-timeout** controls the maximum time (in seconds) that can elapse between hitting the "Negate next ORLY" hotkey and the addition hotkey for it to count as a subtraction.

## License notice

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <http://www.gnu.org/licenses/>.
