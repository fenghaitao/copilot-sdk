import asyncio
import shutil

from copilot import CopilotClient, PermissionHandler

BLUE = "\033[34m"
RESET = "\033[0m"


async def main():
    cli_path = shutil.which("copilot")
    if not cli_path:
        raise RuntimeError("Copilot CLI not found in PATH")
    client = CopilotClient({"cli_path": cli_path})
    await client.start()

    try:
        session = await client.create_session(
            {
                "model": "gpt-4.1",
                "on_permission_request": PermissionHandler.approve_all,
            }
        )

        def on_event(event):
            output = None
            if event.type.value == "assistant.reasoning":
                output = f"[reasoning: {event.data.content}]"
            elif event.type.value == "tool.execution_start":
                output = f"[tool: {event.data.tool_name}]"
            if output:
                print(f"{BLUE}{output}{RESET}")

        session.on(on_event)

        models = await client.list_models()
        print("Available models:")
        for m in models:
            print(f"  {m.id}: {m.name}")
        print()

        print("Chat with Copilot (Ctrl+C to exit)\n")

        while True:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            print()

            reply = await session.send_and_wait({"prompt": user_input})
            print(f"\nAssistant: {reply.data.content if reply else None}\n")

    except KeyboardInterrupt:
        print("\nBye!")
    finally:
        try:
            await client.stop()
        except (asyncio.CancelledError, Exception):
            await client.force_stop()


if __name__ == "__main__":
    asyncio.run(main())
