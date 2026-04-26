import anthropic

client = anthropic.Anthropic(
  # defaults to os.environ.get("ANTHROPIC_API_KEY")
  api_key="sk-ant-api03-NXiNLrx43RT0SyZce3GcZWFZ7JEVbvaL4DsVbtjchVbg4XbmJmJx1M"
          "4phoAunxOnj1tN5joqVNj7aRXFX95LqQ-Tc0ydwAA",
)

message_batch = client.beta.messages.batches.create(
    requests=[
        {
            "custom_id": "first-prompt-in-my-batch",
            "params": {
                "model": "claude-3-5-haiku-20241022",
                "max_tokens": 100,
                "messages": [
                    {
                        "role": "user",
                        "content": "Hey Claude, tell me a short landChain?",
                    }
                ],
            },
        },
        {
            "custom_id": "second-prompt-in-my-batch",
            "params": {
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 100,
                "messages": [
                    {
                        "role": "user",
                        "content": "Hey Claude, tell me a short fun fact integration!",
                    }
                ],
            },
        },
    ]
)
print(message_batch)