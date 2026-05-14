import sys

from maa.agent.agent_server import AgentServer

from .log import log


def main() -> None:
    if len(sys.argv) < 2:
        log.error("Usage: python main.py <socket_id>")
        log.error("socket_id is provided by AgentIdentifier.")
        sys.exit(1)

    socket_id = sys.argv[-1]

    log.debug("AgentServer starting...")
    AgentServer.start_up(socket_id)
    log.debug("AgentServer started")
    AgentServer.join()
    AgentServer.shut_down()
    log.debug("AgentServer shutdown")


if __name__ == "__main__":
    main()
