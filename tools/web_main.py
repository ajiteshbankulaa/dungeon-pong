# /// script
# dependencies = ["pygame-ce"]
# ///
import asyncio
import json
import platform
from pathlib import Path
import pygame
from poem.app import Poem, read_axes, W, H

class BrowserPoem(Poem):
    def save(self,completed=False):
        super().save(completed)
        try:
            platform.window.localStorage.setItem("what-returns-v1",self.path.read_text())
        except Exception:
            pass

async def main():
    pygame.mixer.pre_init(44100,-16,2,512)
    pygame.init()
    pygame.display.set_mode((W,H))
    pygame.display.set_caption("What Returns")
    path=Path('web-checkpoint.json')
    try:
        saved=platform.window.localStorage.getItem("what-returns-v1")
        if saved and isinstance(json.loads(str(saved)),dict):path.write_text(str(saved))
    except Exception:
        pass
    game=BrowserPoem(path)
    previous=pygame.time.get_ticks()
    accumulator=0.
    while game.running:
        now=pygame.time.get_ticks()
        accumulator+=min(.1,(now-previous)/1000)
        previous=now
        for event in pygame.event.get():game.event(event)
        h,v=read_axes(pygame.key.get_pressed(),[])
        while accumulator>=1/120:
            game.update(1/120,v if game.mode in ('pong','glass') else h,v>.45,h)
            accumulator-=1/120
        game.draw();pygame.display.flip()
        await asyncio.sleep(0)
    pygame.quit()

asyncio.run(main())
