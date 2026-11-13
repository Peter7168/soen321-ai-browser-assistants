"""mitmproxy addon: shut down cleanly (so the .flow file is fully written) when the file in $SOEN_STOP_FILE appears."""
import asyncio, os
from mitmproxy import ctx

class StopOnFile:
    def running(self):
        asyncio.get_running_loop().create_task(self.watch())

    async def watch(self):
        stop = os.environ.get("SOEN_STOP_FILE")
        while True:
            await asyncio.sleep(1)
            if stop and os.path.exists(stop):
                os.remove(stop)
                ctx.master.shutdown()
                return

addons = [StopOnFile()]
