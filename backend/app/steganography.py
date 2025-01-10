import re

# Convert a string into binary data
def str_to_bin(text):
    return ' '.join(format(ord(char), '08b') for char in text)

# Convert binary data into a string
def bin_to_str(binary):
    chars = binary.split(' ')
    return ''.join(chr(int(char, 2)) for char in chars)

# Wrap a string with a distinct boundary
def wrap(string):
    return "\uFEFF" + string + "\uFEFF"  # Unicode ZERO WIDTH NON-BREAKING SPACE

# Unwrap a string if the distinct boundary exists
def unwrap(string):
    match = re.search(r"\uFEFF(.*?)\uFEFF", string)
    return match.group(1) if match else None

# Convert binary data to zero-width characters
def bin_to_hidden(binary):
    return binary.replace(' ', '\u2060').replace('0', '\u200B').replace('1', '\u200C')

# Convert zero-width characters back to binary data
def hidden_to_bin(hidden):
    return hidden.replace('\u2060', ' ').replace('\u200B', '0').replace('\u200C', '1')

# Hide private message inside public message
def hide_message(public, private):
    private_binary = str_to_bin(private)
    private_hidden = bin_to_hidden(private_binary)
    wrapped_hidden = wrap(private_hidden)
    half = len(public) // 2
    return public[:half] + wrapped_hidden + public[half:]

# Reveal private message from public message
def reveal_message(public_with_hidden):
    unwrapped = unwrap(public_with_hidden)
    if not unwrapped:
        return "No hidden message found."
    binary = hidden_to_bin(unwrapped)
    return bin_to_str(binary)
