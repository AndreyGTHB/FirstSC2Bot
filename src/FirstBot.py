import sc2
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer
from sc2.constants import NEXUS, PROBE, PYLON, ASSIMILATOR, GATEWAY, \
    CYBERNETICSCORE, STALKER


class FirstBot(sc2.BotAI):
    PROBES_NEEDED = 60

    async def on_step(self, iteration):
        await self.distribute_workers()
        await self.build_workers()

        await self.build_pylons()
        await self.expand()
        await self.build_assimilators()

        await self.build_army_structures()
        await self.build_army()

    async def build_workers(self):
        for nexus in self.units(NEXUS).ready.idle:
            if self.units(PROBE).amount < self.PROBES_NEEDED:
                if not self.can_afford(PROBE):
                    return
                await self.do(nexus.train(PROBE))

    async def build_pylons(self):
        if self.supply_left < 5 and not self.already_pending(PYLON):
            if self.can_afford(PYLON):
                await self.build(PYLON, self.units(NEXUS).first)

    async def expand(self):
        nexuses = self.units(NEXUS)
        if nexuses.amount < 2 or self.units(PROBE).amount >= self.units(NEXUS) * 22 - 4:
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
            if not self.units(GATEWAY).ready.exists:
                if self.can_afford(GATEWAY) and not self.already_pending(GATEWAY):
                    await self.build(GATEWAY, pylon)
            else:
                if not self.units(CYBERNETICSCORE).exists:
                    if self.can_afford(CYBERNETICSCORE) and not self.already_pending(CYBERNETICSCORE):
                        await self.build(CYBERNETICSCORE, pylon)

    async def build_army(self):
        for gate in self.units(GATEWAY).ready.idle:
            if not self.can_afford(STALKER):
                return
            await self.do(gate.train(STALKER))

    async def control_army(self):
        stalkers = self.units(STALKER)


run_game(
    maps.get("AbyssalReefLE"),
    [
        Bot(Race.Protoss, FirstBot()),
        Computer(Race.Terran, Difficulty.Easy)
    ],
    realtime=True
)
