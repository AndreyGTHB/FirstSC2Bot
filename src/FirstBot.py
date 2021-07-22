import sc2
from sc2.units import Units
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer
from sc2.constants import NEXUS, PROBE, PYLON, ASSIMILATOR, GATEWAY, \
    CYBERNETICSCORE, STALKER


class FirstBot(sc2.BotAI):
    PROBES_NEEDED = 60

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

    async def on_step(self, iteration):
        await self.distribute_workers()
        await self.build_workers()

        await self.build_pylons()
        await self.expand()
        await self.build_assimilators()

        await self.build_army_structures()
        await self.build_army()
        await self.control_army()

    async def build_workers(self):
        for nexus in self.units(NEXUS).ready.idle:
            if self.units(PROBE).amount < self.PROBES_NEEDED:
                if not self.can_afford(PROBE):
                    return
                await self.do(nexus.train(PROBE))

    async def build_pylons(self):
        if self.supply_left < 5 and not self.already_pending(PYLON):
            if self.can_afford(PYLON):
                await self.build(PYLON, self.units(NEXUS).random.position.towards(self.game_info.map_center, 3))

    async def expand(self):
        nexuses = self.units(NEXUS)
        if nexuses.amount < 2 or self.units(PROBE).amount >= self.units(NEXUS).amount * 22 - 4:
            if self.can_afford(NEXUS):
                await self.expand_now()

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
            if gateways.amount < self.units(NEXUS).amount * 2:
                if self.can_afford(GATEWAY):
                    await self.build(GATEWAY, pylon)
            if gateways.ready.exists and self.units(CYBERNETICSCORE).empty:
                if self.can_afford(CYBERNETICSCORE) and not self.already_pending(CYBERNETICSCORE):
                    await self.build(CYBERNETICSCORE, pylon)

    async def build_army(self):
        for gate in self.units(GATEWAY).ready.idle:
            if not self.can_afford(STALKER):
                return
            await self.do(gate.train(STALKER))

    async def control_army(self):
        stalkers = self.units(STALKER).ready
        if stalkers.amount > 10:
            for s in stalkers.idle:
                await self.do(s.attack(self.find_target()))
        elif stalkers.amount > 2:
            for s in stalkers.idle:
                if self.get_enemy_units().empty:
                    return
                await self.do(s.attack(self.get_enemy_units().random))

run_game(
    maps.get("AbyssalReefLE"),
    [
        Bot(Race.Protoss, FirstBot()),
        Computer(Race.Terran, Difficulty.Medium)
    ],
    realtime=False
)
