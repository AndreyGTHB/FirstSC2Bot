import sc2
from sc2.units import Units
from sc2 import run_game, maps, Race, Difficulty, Result
from sc2.player import Bot, Computer
from sc2.constants import *
from sc2.position import Point2, Pointlike

# Only for training the nn
from sc2 import BotAI as BotWithOnEnd

import cv2
import numpy as np
import random


HEADLESS = False
class FirstBot(BotWithOnEnd):
    PROBES_NEEDED = 60

    ITERATIONS_PER_MINUTE = 165
    iteration = 0

    flipped = None
    train_data = []

    WAITING = 16.5
    do_something_after = 0

    draw_dict = {
        NEXUS: [15, (0, 255, 0)],
        PYLON: [3, (20, 235, 0)],
        PROBE: [1, (55, 200, 0)],
        ASSIMILATOR: [2, (55, 200, 0)],
        GATEWAY: [3, (200, 100, 0)],
        CYBERNETICSCORE: [3, (150, 150, 0)],
        STARGATE: [5, (255, 0, 0)],
        ROBOTICSFACILITY: [5, (215, 155, 0)],
        VOIDRAY: [3, (255, 100, 0)],
        OBSERVER: [1, (255, 255, 255)]
    }
    enemy_draw_dict = {
       NEXUS: [15, (0, 0, 255)], COMMANDCENTER: [15, (0, 0, 255)], HATCHERY: [15, (0, 0, 255)],
       PROBE: [1, (55, 0, 155)], SCV: [1, (55, 0, 155)], DRONE: [1, (55, 0, 155)]
    }

    def get_minutes(self):
        return self.iteration / self.ITERATIONS_PER_MINUTE

    def get_enemy_units(self) -> Units:
        return self.state.enemy_units.not_structure
    def get_enemy_structures(self) -> Units:
        return self.state.enemy_units.structure
    def find_target(self):
        if self.get_enemy_units().exists:
            return self.get_enemy_units().random
        if self.get_enemy_structures().exists:
            return self.get_enemy_structures().random
        return self.enemy_start_locations[0]

    def get_location_variance(self, location, variance=20) -> Point2:
        x = location[0]
        y = location[1]
        x += ((random.randrange(-1*variance, variance))/100) * x
        y += ((random.randrange(-1*variance, variance))/100) * y
        if x < 0:
            x = 0
        if y < 0:
            y = 0
        if x > self.game_info.map_size[0]:
            x = self.game_info.map_size[0]
        if y > self.game_info.map_size[1]:
            y = self.game_info.map_size[1]
        go_to = Point2(Pointlike((x,y)))
        return go_to

    async def on_step(self, iteration):
        self.iteration = iteration

        await self.scout()

        await self.distribute_workers()
        await self.build_workers()

        await self.build_pylons()
        await self.expand()
        await self.build_assimilators()

        await self.build_army_structures()
        await self.build_army()

        await self.intel()
        await self.control_army()

    async def on_end(self, result):
        print('--- on_end called ---')
        print(game_result)
        if game_result == Result.Victory:
            np.save("train_data/{}.npy".format(str(int(time.time()))), np.array(self.train_data))

    async def build_workers(self):
        for nexus in self.units(NEXUS).ready.idle:
            if self.units(PROBE).amount < self.PROBES_NEEDED:
                if not self.can_afford(PROBE):
                    return
                await self.do(nexus.train(PROBE))

    async def build_pylons(self):
        if self.supply_left < 5 and not self.already_pending(PYLON):
            if self.can_afford(PYLON):
                await self.build(PYLON, self.units(NEXUS).random.position.towards(self.game_info.map_center, 2))

    async def expand(self):
        nexuses = self.units(NEXUS)
        if nexuses.amount < 2 or nexuses.amount > 3 or self.units(PROBE).amount >= self.units(NEXUS).amount * 22 - 4:
            if self.can_afford(NEXUS) and not self.already_pending(NEXUS) < 2:
                await self.expand_now(max_distance=0)

    async def build_assimilators(self):
        if self.units(GATEWAY).empty:
            return
        for nexus in self.units(NEXUS).ready:
            geysers = self.state.vespene_geyser.closer_than(10, nexus)
            for geyser in geysers:
                if not self.can_afford(ASSIMILATOR):
                    return
                worker = self.select_build_worker(geyser.position)
                if worker is None:
                    break
                if not self.units(ASSIMILATOR).closer_than(1, geyser).exists:
                    await self.do(worker.build(ASSIMILATOR, geyser))

    async def build_army_structures(self):
        pylons = self.units(PYLON).ready
        if pylons.exists:
            pylon = pylons.random
            gateways = self.units(GATEWAY)
            if gateways.empty:
                if self.can_afford(GATEWAY):
                    await self.build(GATEWAY, pylon.position.towards(self.game_info.map_center, 1))
            elif gateways.ready.exists and self.units(CYBERNETICSCORE).empty:
                if self.can_afford(CYBERNETICSCORE) and not self.already_pending(CYBERNETICSCORE):
                    await self.build(CYBERNETICSCORE, pylon.position.towards(self.game_info.map_center, 1))
            elif self.units(CYBERNETICSCORE).ready.exists:
                if self.units(ROBOTICSFACILITY).empty:
                    if self.can_afford(ROBOTICSFACILITY):
                        await self.build(ROBOTICSFACILITY, pylon.position.towards(self.game_info.map_center, 1))
                if self.units(STARGATE).amount < self.get_minutes():
                    if self.can_afford(STARGATE):
                        await self.build(STARGATE, pylon.position.towards(self.game_info.map_center, 1))
    async def build_army(self):
        for stargate in self.units(STARGATE).ready.noqueue:
            if self.can_afford(VOIDRAY):
                await self.do(stargate.train(VOIDRAY))

    async def intel(self):
        game_data = np.zeros((self.game_info.map_size[1], self.game_info.map_size[0], 3), np.uint8)

        for enemy_unit in self.state.enemy_units:
            unit_type = enemy_unit.type_id
            pos = enemy_unit.position
            if unit_type in self.enemy_draw_dict.keys():
                unit_radius = self.enemy_draw_dict[unit_type][0]
                unit_color = self.enemy_draw_dict[unit_type][1]
            elif enemy_unit.is_structure:
                unit_radius = 5
                unit_color = (200, 50, 212)
            else:
                unit_radius = 3
                unit_color = (50, 0, 215)
            cv2.circle(game_data, (int(pos[0]), int(pos[1])), unit_radius, unit_color, -1)

        for unit_type in self.draw_dict:
            unit_radius = self.draw_dict[unit_type][0]
            unit_color = self.draw_dict[unit_type][1]
            for unit in self.units(unit_type).ready:
                pos = unit.position
                cv2.circle(game_data, (int(pos[0]), int(pos[1])), unit_radius, unit_color, -1)

        minerals_ratio = self.minerals / 1500
        vespene_ratio = self.vespene / 1500
        population_ratio = self.supply_left / self.supply_cap
        plausible_supply = self.supply_cap / 200
        military_weight = self.units(VOIDRAY).amount / (self.supply_used) # CHANGE
        line_max = 50
        cv2.line(game_data, (0, 19), (int(line_max*military_weight), 19), (250, 250, 200), 3)  # worker/supply ratio
        cv2.line(game_data, (0, 15), (int(line_max*plausible_supply), 15), (220, 200, 200), 3)  # plausible supply (supply/200.0)
        cv2.line(game_data, (0, 11), (int(line_max*population_ratio), 11), (150, 150, 150), 3)  # population ratio (supply_left/supply)
        cv2.line(game_data, (0, 7), (int(line_max*vespene_ratio), 7), (210, 200, 0), 3)  # gas / 1500
        cv2.line(game_data, (0, 3), (int(line_max*mineral_ratio), 3), (0, 255, 25), 3)  # minerals minerals/1500

        self.flipped = cv2.flip(game_data, 0)
        if not HEADLESS:
            resized = cv2.resize(self.flipped, dsize=None, fx=2, fy=2)
            cv2.imshow('Intel', resized)
            cv2.waitKey(1)

    async def control_army(self): # CHANGE
        voidrays = self.units(VOIDRAY)
        if voidrays.idle.empty or self.iteration <= self.do_something_after:
            return
        choice = random.randrange(0, 4)
        target = None
        if choice == 0:
            self.do_something_after = self.iteration + self.WAITING
        elif choice == 1:
            if self.get_enemy_units().exists:
                target = self.get_enemy_units().closest_to(self.units(NEXUS).random)
        elif choice == 2:
            if self.get_enemy_structures().exists:
                target = self.get_enemy_structures().random
        elif choice == 3:
            target = self.enemy_start_locations[0]
        if target:
            for vr in voidrays:
                await self.do(vr.attack(target))
        y = np.zeros(4)
        y[choice] = 1
        print(y)
        self.train_data.append([y, self.flipped])


    async def scout(self):
        observers = self.units(OBSERVER)
        if observers.exists:
            for scout in observers.idle:
                enemy_location = self.enemy_start_locations[0]
                move_to = self.get_location_variance(enemy_location, 30)
                await self.do(scout.move(move_to))
        if observers.amount < 3:
            for rf in self.units(ROBOTICSFACILITY).ready.noqueue:
                if self.can_afford(OBSERVER):
                    await self.do(rf.train(OBSERVER))


run_game(
    maps.get("AbyssalReefLE"),
    [
        Bot(Race.Protoss, FirstBot()),
        Computer(Race.Zerg, Difficulty.Medium)
    ],
    realtime=False
)
