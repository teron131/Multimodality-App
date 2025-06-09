import os

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

from .utils import encode_audio, encode_image

load_dotenv()

llm = ChatOpenAI(
    model=os.getenv("GEMINI_MODEL"),
    api_key=os.getenv("GOOGLE_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)


def get_response(
    text_input: str | None = None,
    image_path: str | None = None,
    audio_path: str | None = None,
) -> AIMessage:
    """Get a response from the LLM.

    Args:
        text_input: The text input to the LLM.
        image_path: The path to the image to be sent to the LLM.
        audio_path: The path to the audio to be sent to the LLM.

    Returns:
        The response from the LLM.
    """
    if not text_input and not image_path and not audio_path:
        raise ValueError("At least one of text_input, image_path, or audio_path must be provided")

    content = []
    if text_input:
        content.append({"type": "text", "text": text_input})
    if image_path:
        image_base64 = encode_image(image_path)
        content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}})
    if audio_path:
        audio_base64 = encode_audio(audio_path)
        content.append({"type": "input_audio", "input_audio": {"data": audio_base64, "format": "mp3"}})
    messages = [HumanMessage(content=content)]

    response = llm.invoke(messages)

    return response


if __name__ == "__main__":
    response = get_response(
        text_input="What do you see and hear?",
        image_path="image/150920049.png",
        audio_path="audio/sXoSILzgFug.m4a",
    )
    print(response.content)
