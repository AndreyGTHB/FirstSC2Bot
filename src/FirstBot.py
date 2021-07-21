import sc2
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer
from sc2.constants import NEXUS, PROBE, PYLON


class FirstBot(sc2.BotAI):
    async def build_workers(self):
        nexuses = self.units(NEXUS)
        print(nexuses.amount * 22)
        if self.units(PROBE).amount >= nexuses.amount * 22:
            return
        for nexus in nexuses.ready.idle:
            if self.can_afford(PROBE):
                await self.do(nexus.train(PROBE))

    async def build_pylons(self):
        if self.supply_left < 5:
            if self.can_afford(PYLON):
                nexuses = self.units(NEXUS)
                await self.build(PYLON, near=nexuses.first)

    async def on_step(self, iteration):
        await self.distribute_workers()
        await self.build_workers()
        await self.build_pylons()


run_game(
    maps.get("AbyssalReefLE"),
    [
        Bot(Race.Protoss, FirstBot()),
        Computer(Race.Terran, Difficulty.Easy)
    ],
    realtime=True
)
