import requests

from app.config.settings import settings


class MistralClient:
    """
    Simple client for the Mistral Chat Completions API.
    """

    API_URL = "https://api.mistral.ai/v1/chat/completions"

    def __init__(
        self,
        temperature: float = 0.1,
        max_tokens: int = 2000,
    ):
        self.api_key = settings.MISTRAL_API_KEY
        self.model = settings.MISTRAL_MODEL
        self.temperature = temperature
        self.max_tokens = max_tokens

        if not self.api_key:
            raise ValueError(
                "MISTRAL_API_KEY is not configured."
            )

        if not self.model:
            raise ValueError(
                "MISTRAL_MODEL is not configured."
            )

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """
        Send a system prompt and user prompt to Mistral
        and return the generated text.
        """

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        try:

            response = requests.post(
                self.API_URL,
                headers=headers,
                json=payload,
                timeout=120,
            )

            response.raise_for_status()

        except requests.exceptions.RequestException as exc:

            raise RuntimeError(
                f"Mistral API request failed: {exc}"
            ) from exc

        try:

            data = response.json()

        except ValueError as exc:

            raise RuntimeError(
                "Mistral returned an invalid JSON response."
            ) from exc

        # ---------------------------------------------------------
        # Validate API response
        # ---------------------------------------------------------

        if "choices" not in data:
            raise RuntimeError(
                f"Unexpected Mistral API response: {data}"
            )

        if not data["choices"]:
            raise RuntimeError(
                "Mistral returned no choices."
            )

        message = data["choices"][0].get(
            "message",
            {},
        )

        content = message.get(
            "content"
        )

        if not content:
            raise RuntimeError(
                "Mistral returned an empty message."
            )

        return content


if __name__ == "__main__":

    print("=" * 70)
    print("MISTRAL CLIENT TEST")
    print("=" * 70)

    client = MistralClient(
        temperature=0.1,
        max_tokens=100,
    )

    response = client.generate(
        system_prompt=(
            "You are a helpful assistant. "
            "Respond briefly."
        ),
        user_prompt=(
            "Say hello and confirm that the Mistral API "
            "is working."
        ),
    )

    print("\nResponse:")
    print(response)