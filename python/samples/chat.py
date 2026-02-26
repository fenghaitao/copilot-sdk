import argparse
import asyncio
import os
import shutil

from copilot import CopilotClient, PermissionHandler

BLUE = "\033[34m"
RESET = "\033[0m"

IFLOW_PROVIDER = {
    "type": "openai",
    "base_url": "https://apis.iflow.cn/v1/",
    "api_key": os.environ.get("IFLOW_API_KEY", ""),
    "wire_api": "completions",
}


def parse_args():
    parser = argparse.ArgumentParser(description="Chat with Copilot")
    parser.add_argument("--model", "-m", type=str, default=None, help="Model ID to use")
    parser.add_argument("--list-models", "-l", action="store_true", help="List available models and exit")
    parser.add_argument("--timeout", "-t", type=float, default=300, help="Timeout in seconds per response (default: 300)")
    return parser.parse_args()


async def main():
    args = parse_args()

    cli_path = shutil.which("copilot")
    if not cli_path:
        raise RuntimeError("Copilot CLI not found in PATH")
    client = CopilotClient({"cli_path": cli_path})
    await client.start()

    try:
        models = await client.list_models()

        if args.list_models:
            print("Available models:")
            for m in models:
                print(f"  {m.id}: {m.name}")
            return

        # Determine model and provider
        iflow_ids = {m.id for m in models if m.id == args.model} if args.model else set()
        chosen_model = args.model

        # If model not in Copilot's list, assume it's an iflow model
        copilot_ids = {m.id for m in models}
        if chosen_model and chosen_model not in copilot_ids:
            provider = IFLOW_PROVIDER
        elif not chosen_model:
            # Default to iflow qwen3-coder-plus
            chosen_model = "qwen3-coder-plus"
            provider = IFLOW_PROVIDER
        else:
            provider = None  # use Copilot's default auth

        session_config = {
            "model": chosen_model,
            "on_permission_request": PermissionHandler.approve_all,
        }
        if provider:
            session_config["provider"] = provider

        print(f"Using model: {chosen_model}\n")
        session = await client.create_session(session_config)

        def on_event(event):
            output = None
            if event.type.value == "assistant.reasoning":
                output = f"[reasoning: {event.data.content}]"
            elif event.type.value == "tool.execution_start":
                output = f"[tool: {event.data.tool_name}]"
            if output:
                print(f"{BLUE}{output}{RESET}")

        session.on(on_event)

        print("Chat with Copilot (Ctrl+C to exit)\n")

        while True:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            print()
            reply = await session.send_and_wait({"prompt": user_input}, timeout=args.timeout)
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
