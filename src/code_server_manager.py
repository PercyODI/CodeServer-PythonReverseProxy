import docker
import asyncio


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
            self.client.containers.run("codercom/code-server:latest", "--auth none", detach=True,
                                       name=container_name, network="my_network")
            asyncio.sleep(5)
