import config

def select_channel(reader):
    channel = input(f"Enter channel number (current: {config.CHANNEL}): ").strip()
    try:
        channel = int(channel)
        reader.set_channel(channel)
        print(f"Switched to channel {channel}")
        return channel
    except ValueError:
        print("Invalid channel number")
        return None