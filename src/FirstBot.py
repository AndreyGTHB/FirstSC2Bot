import sc2
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer
from sc2.constants import NEXUS, PROBE, PYLON, ASSIMILATOR, GATEWAY, \
    CYBERNETICSCORE, STALKER


class FirstBot(sc2.BotAI):
    async def on_step(self, iteration):
        await self.distribute_workers()
        await self.build_workers()

        await self.build_pylons()
        await self.expand()
        await self.build_assimilators()

        await self.build_army_structures()
        await self.build_army()

    def probes_need(self) -> int:
        return self.units(NEXUS).amount * 22

    async def build_workers(self):
        for nexus in self.units(NEXUS).ready.idle:
            if self.units(PROBE).amount < self.probes_need():
                if not self.can_afford(PROBE):
                    return
                await self.do(nexus.train(PROBE))

    async def build_pylons(self):
        if self.supply_left < 5 and not self.already_pending(PYLON):
            if self.can_afford(PYLON):
                await self.build(PYLON, self.units(NEXUS).first)

    async def expand(self):
        nexuses = self.units(NEXUS)
        if nexuses.amount < 2 or self.units(PROBE).amount >= self.probes_need() - 4:
            if self.can_afford(NEXUS):
                await self.expand_now()

    async def build_assimilators(self):
        for nexus in self.units(NEXUS).ready:
            geysers = self.state.vespene_geyser.closer_than(10.0, nexus)
            for geyser in geysers:
                if not self.can_afford(ASSIMILATOR):
                    break
                worker = self.select_build_worker(geyser.position)
                if worker is None:
                    break
                if not self.units(ASSIMILATOR).closer_than(1.0, geyser).exists:
                    await self.do(worker.build(ASSIMILATOR, geyser))

    async def build_army_structures(self):
        pylons = self.units(PYLON).ready
        if pylons.exists:
            pylon = pylons.random
            if not self.units(GATEWAY).exists:
                if self.can_afford(GATEWAY):
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


run_game(
    maps.get("AbyssalReefLE"),
    [
        Bot(Race.Protoss, FirstBot()),
        Computer(Race.Terran, Difficulty.Easy)
    ],
    realtime=True
)
