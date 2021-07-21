import sc2
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer
from sc2.constants import NEXUS, PROBE, PYLON


class FirstBot(sc2.BotAI):

    def probes_need(self) -> int:
        return self.units(NEXUS).amount * 22

    async def build_workers(self):
        for nexus in self.units(NEXUS).ready.idle:
            if self.units(PROBE).amount < self.probes_need():
                if self.can_afford(PROBE):
                    await self.do(nexus.train(PROBE))

    async def build_pylons(self):
        if self.supply_left < 5:
            if self.can_afford(PYLON):
                await self.build(PYLON, near=self.units(NEXUS).first)

    async def expand(self):
        nexuses = self.units(NEXUS)
        if nexuses.amount < 2 or self.probes_need() - 4 >= self.units(PROBE):
            if self.can_afford(NEXUS):
                await self.expand_now()

    async def on_step(self, iteration):
        print(probes_need())
        await self.distribute_workers()
        await self.build_workers()
        await self.build_pylons()
        await self.expand()


run_game(
    maps.get("AbyssalReefLE"),
    [
        Bot(Race.Protoss, FirstBot()),
        Computer(Race.Terran, Difficulty.Easy)
    ],
    realtime=True
)
