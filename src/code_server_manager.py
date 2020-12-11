import asyncio
from os import environ as env

from aiohttp import ClientSession
import docker


class CodeServerManager:
    client: docker.DockerClient
    container_name: str

    def __init__(self, container_name) -> None:
        self.client = docker.from_env()
        self.container_name = container_name.replace("|", "_")
        super().__init__()

    def get_container_name(self):
        return self.container_name

    async def find_or_create_container(self) -> None:
        # find or create the container
        if self.container_name in [
            x.name for x in self.client.containers.list(all=True)
        ]:
            container = self.client.containers.get(self.container_name)
            if container.status != "running":
                container.start()
        else:
            if "VOLUMEPATH" in env.keys():
                volumes_obj = {
                    f"{env['VOLUMEPATH']}/{self.container_name}": {"bind": "/home", "mode": "rw"}
                }
            else:
                volumes_obj = None
            self.client.containers.run(
                "percyodi/code-server:20201210",
                "--auth none",
                detach=True,
                name=self.container_name,
                network="my_network",
                volumes=volumes_obj,
            )
            await self.wait_for_container()

    async def wait_for_container(self) -> None:
        container_up = False
        while not container_up:
            try:
                async with ClientSession() as session:
                    async with session.get(
                        f"http://{self.container_name}:8080/healthz",
                        allow_redirects=True,
                    ) as res:
                        await res.read()
                        print("Container up.")
                        container_up = True
            except Exception as err:
                print(err)
                print("Container still down.")
                await asyncio.sleep(1)
