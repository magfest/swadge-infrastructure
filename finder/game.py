#!/usr/bin/env python3
"""
An app used to figure out where swadges are.
"""

from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner
from autobahn.wamp import auth, SubscribeOptions
from collections import deque
import threading
import requests
import asyncio
import random
import time
import re


class Color:
    """Some common colors"""
    RED = 0xff0000
    ORANGE = 0xff7f00
    YELLOW = 0xffff00
    GREEN = 0x00ff00
    CYAN = 0x00ffff
    BLUE = 0x0000ff
    PURPLE = 0x7f00ff
    PINK = 0xff00ff

    WHITE = 0xffffff
    BLACK = 0x000000
    OFF = 0x000000

    RAINBOW = [RED, ORANGE, YELLOW, GREEN, CYAN, BLUE, PURPLE, PINK, WHITE]


def lighten(amt, color):
    """
    Lighten a color by a percent --
    :param amt:
    :param color:
    :return:
    """
    return int(amt * ((color >> 16) & 0xff)) << 16 \
           | int(amt * ((color >> 8) & 0xff)) << 8 \
           | int(amt * (color & 0xff)) & 0xff


# WAMP Realm; doesn't change
WAMP_REALM = "swadges"
WAMP_URL = "ws://api.swadge.com:1337/ws"

# WAMP Credentials; you will get your own later
WAMP_USER = "demo"
WAMP_PASSWORD = "hunter2"

# This is a unique name for this game
# Change this before you run it, otherwise it will conflict!
GAME_ID = "finder"

# This is a unique button sequence a swadge can enter to join this game.
# This can be changed at any time, as long as the new value is unique.
# Setting this to the empty string will disable joining by sequence.
# Maximum length is 12; 6 is recommended.
# Buttons are [u]p, [l]eft, [d]own, [r]ight, s[e]lect, [s]tart, [a], [b]
GAME_JOIN_SEQUENCE = "babaes"

# This is the name of a location that will cause a swadge to automatically
# join the game without needing to press any buttons. They will also leave
# the game when they are no longer in the location. Setting this to the
# empty string will disable joining by location. If this is set along with
# join by sequence, either of them being triggered will result in a join.
# Note that only one game can "claim" a location at once, so unless you need
# exclusive control over the location, you should just subscribe to that
# location.
#
# Current tracked locations (more may be added; if you'd like to make sure
# a location will be tracked, ask in #circuitboards):
# - panels1
# - gameroom
# - concerts
GAME_JOIN_LOCATION = ""

# Minimum number of seconds between scan requests per-badge
SCAN_FREQ = 60

FIND_HOST = "http://find.magevent.net"
FIND_GROUP = "labs2017"

LOC_TEA_ROOM = "tea_room"
LOC_TECHOPS = "techops"
LOC_PANELS1 = "panels1"
LOC_PANELS2 = "panels2"
LOC_PANELS3 = "panels3"
LOC_SPACE_CLINIC = "space_clinic"
LOC_HOTEL_JAIL = "hotel_jail"
LOC_LEGO_ROOM = "lego_room"
LOC_ESCAPE_ROOM = "escape_room"
LOC_LAN = "lan"
LOC_CONSOLES = "consoles"
LOC_CONCERTS = "concerts"
LOC_ARCADE = "arcade"
LOC_STOPS = "stops"
LOC_VIP_LOUNGE = "vip_lounge"
LOC_MAKERSPACE_UPPER = "makerspace_upper"
LOC_MAKERSPACE_LOWER = "makerspace_lower"
LOC_TABLETOP = "tabletop"
LOC_REGISTRATION = "registration"
LOC_VIDEO_ROOM = "video_room"
LOC_TOOOL = "toool"
LOC_130 = "130"
LOC_UNKNOWN = "unknown"


LOCATIONS = {
    LOC_TEA_ROOM: "Tea Room",
    LOC_TECHOPS: "BestOps",
    LOC_PANELS1: "Panels 1",
    LOC_PANELS2: "Panels 2",
    LOC_PANELS3: "Panels 3",
    LOC_SPACE_CLINIC: "Space Clinic",
    LOC_HOTEL_JAIL: "Hotel Jail",
    LOC_LEGO_ROOM: "Lego Room",
    LOC_ESCAPE_ROOM: "Escape Room",
    LOC_LAN: "LAN",
    LOC_CONSOLES: "Consoles",
    LOC_CONCERTS: "Concerts",
    LOC_ARCADE: "Arcade",
    LOC_STOPS: "Staff Operations",
    LOC_VIP_LOUNGE: "VIP Lounge",
    LOC_MAKERSPACE_UPPER: "Makerspace (Magnolia)",
    LOC_MAKERSPACE_LOWER: "Makerspace (Foyer)",
    LOC_TABLETOP: "Tabletop",
    LOC_REGISTRATION: "Registration",
    LOC_VIDEO_ROOM: "Video Room",
    LOC_TOOOL: "Toool",
    LOC_130: "130",
    LOC_UNKNOWN: "Nobody Knooows"
}

# TODO: Will store the WAP closest to each location, in case FIND doesn't work.
# That will let us still have a reasonable location based off connected BSSID.
CLOSEST_WAPS = {

}


class LearnInfo:
    def __init__(self, badge_id):
        self.badge_id = badge_id
        self.group = None


class BadgeInfo:
    def __init__(self, badge_id):
        self.badge_id = badge_id
        self.last_scan = []
        self.last_scan_time = time.time() - random.randint(0, SCAN_FREQ)
        self.last_location = None


class GameComponent(ApplicationSession):
    badges = {}
    learn_badges = {}
    learn_groups = []

    dirty_queue = deque()
    location_broadcasts = asyncio.Queue()

    def onConnect(self):
        """
        Called by WAMP upon successfully connecting to the crossbar server
        :return: None
        """
        self.join(WAMP_REALM, ["wampcra"], WAMP_USER)

    def scan_thread(self):
        while True:
            try:
                next_badge = self.dirty_queue.popleft()
                badge_info = self.badges[next_badge]

                payload = {
                    "username": "swadge_" + str(next_badge),
                    "group": FIND_GROUP,
                    "time": int(badge_info.last_scan_time * 1000),
                    "wifi-fingerprint": [{"mac": scan['bssid'].upper(),
                                          "rssi": scan['rssi']} for
                                         scan in badge_info.last_scan]
                }

                badge_info.last_scan = []

                if next_badge in self.learn_badges:
                    learn_info = self.learn_badges[next_badge]
                    print(learn_info)
                    if learn_info.group is not None:
                        payload["location"] = self.learn_groups[learn_info.group]

                        res = requests.post(FIND_HOST + "/learn", json=payload)

                else:
                    payload["location"] = "tracking"
                    res = requests.post(FIND_HOST + "/track", json=payload)

                    location = res.json().get("location", "unknown")

                    if location != badge_info.last_location:
                        badge_info.last_location = location
                        self.location_broadcasts.put_nowait((next_badge, location))

            except IndexError:
                time.sleep(.1)
            except Exception as e:
                print("*****err*****")
                print(e)

    def onChallenge(self, challenge):
        """
        Called by WAMP for authentication.
        :param challenge: The server's authentication challenge
        :return:          The client's authentication response
        """
        if challenge.method == "wampcra":
            signature = auth.compute_wcs(WAMP_PASSWORD.encode('utf8'),
                                         challenge.extra['challenge'].encode('utf8'))
            return signature.decode('ascii')
        else:
            raise Exception("don't know how to handle authmethod {}".format(challenge.method))

    async def game_register(self):
        """
        Register the game with the server. Should be called after initial connection and any time
        the server requests it.
        :return: None
        """

        res = await self.call('game.register',
                              GAME_ID,
                              sequence=GAME_JOIN_SEQUENCE)

        err = res.kwresults.get("error", None)
        if err:
            print("Could not register:", err)
        else:
            # This call returns any players that may have already joined the game to ease restarts
            players = res.kwresults.get("players", [])
            await asyncio.gather(*(self.on_player_join(player) for player in players))

    async def on_new_badge(self, badge_id):
        print("New badge: " + str(badge_id))
        self.badges[badge_id] = BadgeInfo(badge_id)

    async def on_scan(self, timestamp, stations, badge_id=None):
        badge = self.badges.get(badge_id, None)

        if not badge:
            badge = BadgeInfo(badge_id)
            self.badges[badge_id] = badge

        badge.last_scan_time = time.time()
        if len(stations) == 0:
            print("Sending off {} total stations from {}".format(len(badge.last_scan), badge_id))
            if badge_id not in self.dirty_queue:
                self.dirty_queue.append(badge_id)
        else:
            print("Got scan with {} stations from {}".format(len(stations), badge_id))
            badge.last_scan.extend(stations)

    async def set_lights(self, badge_id):
        # Set the lights for the badge to simple colors
        # Note that the order of the lights will be [BOTTOM_LEFT, BOTTOM_RIGHT, TOP_RIGHT, TOP_LEFT]
        if badge_id in self.learn_badges:
            print(self.learn_badges)
            group = self.learn_badges[badge_id].group
            self.publish('badge.' + str(badge_id) + '.lights_static',
                         *([lighten(.01, Color.RAINBOW[group % len(Color.RAINBOW)])] * 4
                         if group is not None else [lighten(.01, Color.WHITE)] * 4))

    async def do_broadcasts(self):
        while True:
            badge, loc = await self.location_broadcasts.get()

            clean_loc = loc.replace(' ', '_').lower()

            print("Badge #" + str(badge) + " located at " + LOCATIONS.get(loc, loc))
            self.publish('badge.' + str(badge) + '.location', [clean_loc, 'find'], {'badge_id': badge})
            count = sum((b.last_location == loc for b in self.badges.values()))
            self.publish('location.' + clean_loc + '.occupants', [count], {'location': clean_loc})

    async def do_scan_requests(self):
        while True:
            cur_time = time.time()
            next_request = 2147483647

            for badge in self.badges.values():
                expire = badge.last_scan_time + SCAN_FREQ
                if expire < cur_time \
                        and badge.badge_id not in self.dirty_queue:
                    print("Requesting scan from " + str(badge.badge_id))
                    self.publish('badge.' + str(badge.badge_id) + '.request_scan')
                elif expire >= cur_time:
                    print("Not request scan from" + str(badge.badge_id))
                    # We'll sleep until the next badge expires
                    if expire < next_request:
                        next_request = expire
            await asyncio.sleep(max(next_request - time.time(), .1))

    async def on_player_join(self, badge_id):
        """
        Called when a player joins the game, such as by entering a join sequence or entering a
        designated location.
        :param badge_id: The badge ID of the player who left
        :return: None
        """

        print("Badge #{} joined".format(badge_id))

        self.learn_badges[badge_id] = LearnInfo(badge_id)

        await self.set_lights(badge_id)

    async def on_player_leave(self, badge_id):
        """
        Called when a player leaves the game, such as by leaving a designated location.
        :param badge_id: The badge ID of the player who left
        :return: None
        """

        # Make sure we unsubscribe from all this badge's topics
        print("Badge #{} left".format(badge_id))
        del self.learn_badges[badge_id]

    async def on_group_create(self, location):
        self.learn_groups.append(location)

    async def on_group_set(self, i, location):
        try:
            self.learn_groups[i] = location
            print(i, location)
            return {"success": True, "message": "Group " + str(i) + " changed to location " + location}
        except IndexError:
            pass

    async def on_group_add(self, player, group):
        if player in self.learn_badges:
            self.learn_badges[player].group = group

    async def get_groups(self):
        print(self.learn_badges)
        for k in self.learn_badges.values():
            print(k.badge_id)
            print(k.group)
        return {'groups': [{'location': l,
                            'display': LOCATIONS.get(l, l),
                            'badges': [b.badge_id for b in self.learn_badges.values()
                                       if b.group == i]}
                           for i, l in enumerate(self.learn_groups)],
                'locations': list(LOCATIONS.keys()),
                'display_locations': LOCATIONS,
                'loose_badges': [b.badge_id for b in self.learn_badges.values() if b.group is None]}

    async def onJoin(self, details):
        """
        WAMP calls this after successfully joining the realm.
        :param details: Provides information about
        :return: None
        """

        # Subscribe to all necessary things
        await self.subscribe(self.on_player_join, 'game.' + GAME_ID + '.player.join')
        await self.subscribe(self.on_player_leave, 'game.' + GAME_ID + '.player.leave')
        await self.subscribe(self.game_register, 'game.request_register')
        await self.subscribe(self.on_scan, 'badge..scan', options=SubscribeOptions(match='wildcard'))
        await self.subscribe(self.on_new_badge, 'badges.new')
        await self.register(self.on_group_create, 'game.' + GAME_ID + '.local.group_create')
        await self.register(self.on_group_set, 'game.' + GAME_ID + '.local.group_set')
        await self.register(self.on_group_add, 'game.' + GAME_ID + '.local.group_add')
        await self.register(self.get_groups, 'game.' + GAME_ID + '.local.get_groups')
        await self.game_register()

        res = await self.call('badges.list')
        badges = res.kwresults.get("badges")
        for badge_id in badges:
            await self.on_new_badge(badge_id)

        threading.Thread(target=self.scan_thread, daemon=True).start()

        await asyncio.gather(self.do_broadcasts(),
                             self.do_scan_requests())

    def onDisconnect(self):
        """
        Called when the WAMP connection is disconnected
        :return: None
        """
        asyncio.get_event_loop().stop()


if __name__ == '__main__':
    runner = ApplicationRunner(
        WAMP_URL,
        WAMP_REALM,
    )
    runner.run(GameComponent, log_level='info')
