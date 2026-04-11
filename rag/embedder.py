import os
import ollama as ollama_client
from dotenv import load_dotenv

load_dotenv()


class OllamaEmbedder:
    """
    Generates text embeddings using Ollama nomic-embed-text.
    Runs completely locally — no API keys needed.
    """

    def __init__(self, model: str = "nomic-embed-text"):
        self.model = model
        self.ollama = ollama_client.Client(
            host=os.getenv("OLLAMA_HOST", "http://localhost:11434")
        )
        self._verify_model()

    def _verify_model(self):
        """Check model is available, pull if not."""
        try:
            self.ollama.embeddings(model=self.model, prompt="test")
            print(f"[Embedder] {self.model} ready.")
        except Exception:
            print(f"[Embedder] Pulling {self.model}...")
            self.ollama.pull(self.model)
            print(f"[Embedder] {self.model} downloaded.")

    def embed(self, text: str) -> list[float]:
        """Embed a single text string."""
        response = self.ollama.embeddings(model=self.model, prompt=text)
        return response["embedding"]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts — returns list of embedding vectors."""
        embeddings = []
        for i, text in enumerate(texts):
            embedding = self.embed(text)
            embeddings.append(embedding)
            if (i + 1) % 10 == 0:
                print(f"[Embedder] Embedded {i + 1}/{len(texts)} chunks...")
        print(f"[Embedder] ✓ Embedded {len(texts)} texts.")
        return embeddings