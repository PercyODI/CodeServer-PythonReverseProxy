import asyncio
from os import confstr_names, environ as env

from aiohttp import ClientSession
import docker


class CodeServerManager:
    client: docker.DockerClient

    def __init__(self) -> None:
        self.client = docker.from_env()
        super().__init__()

    async def find_or_create_container(self, container_name: str) -> None:
        container_name = container_name.replace("|", "_")
        # find or create the container
        if container_name in [x.name for x in self.client.containers.list(all=True)]:
            container = self.client.containers.get(container_name)
            if container.status != "running":
                container.start()
        else:
            if "VOLUMEPATH" in env.keys():
                volumes_obj = {
                    env["VOLUMEPATH"]: {
                        "bind": "/home/coder/project",
                        "mode": "rw"
                    }
                }
            else:
                volumes_obj = None
            self.client.containers.run("codercom/code-server:latest", "--auth none", detach=True,
                                       name=container_name, network="my_network", volumes=volumes_obj)
            await self.wait_for_container(container_name)

    async def wait_for_container(self, container_name: str) -> None:
        container_up = False
        while not container_up:
            try:
                async with ClientSession() as session:
                    async with session.get(
                        f"http://{container_name}:8080/healthz",
                        allow_redirects=True
                    ) as res:
                        await res.read()
                        print("Container up.")
                        container_up = True
            except Exception as err:
                print(err)
                print("Container still down.")
                await asyncio.sleep(1)
